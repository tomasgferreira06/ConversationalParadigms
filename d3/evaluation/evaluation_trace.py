"""Observational tracing of the Coimbra Expert Agent for the D3 evaluation runner.

The agent is NOT modified. Its existing injectable attributes (planner, clients, pipeline, generate,
rag) are replaced by transparent proxies that record what passes through them and delegate every
call unchanged (same arguments, same return value, same exception, same order). Nothing here parses
stdout or debug logs. Only the standard library is imported, so validate-only never loads a model.

RAG-only plans: the agent calls the frozen D2 RAGAgent.respond(question), which does not expose its
chunks. After it returns, the retrieval is reconstructed with the same frozen retriever and the D2
prompt is rebuilt from those chunks (protocol Section 7); this never influences the answer.
"""

from __future__ import annotations

import json
from typing import Any, Callable

NOT_USED = "(não utilizado)"  # prompts.NOT_USED (checked by the tests)
RAG_MARK, WEATHER_MARK, PLACES_MARK = "\n\n[RAG CONTEXT]\n", "\n\n[WEATHER DATA]\n", "\n\n[PLACES DATA]\n"
END_MARK = "\n\nResponde apenas com base nos dados acima."

OBSERVED = "observed_agent_call"
RECONSTRUCTED = "reconstructed_with_same_frozen_retriever"


def jsonable(value: Any) -> Any:
    """A JSON-safe deep copy (raw tool outputs are already JSON; anything else becomes a string)."""

    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def error_info(exc: BaseException) -> dict[str, str]:
    return {"type": type(exc).__name__, "message": str(exc)}


def retrieval_records(results) -> list[dict[str, Any]]:
    """(Document, cosine distance) pairs -> ranked, JSON-safe records."""

    records = []
    for rank, (doc, distance) in enumerate(results, start=1):
        meta = doc.metadata or {}
        path = meta.get("section_path") or []
        records.append({
            "rank": rank,
            "chunk_id": meta.get("chunk_id") or getattr(doc, "id", None),
            "document_id": meta.get("document_id"),
            "section": " > ".join(path) if path else None,
            "cosine_distance": float(distance),
            "text": doc.page_content,
        })
    return records


def prompt_blocks(user_message: str) -> dict[str, str | None]:
    """The RAG / WEATHER / PLACES blocks of the expert's final prompt, None when "(não utilizado)"."""

    try:
        start = user_message.index(RAG_MARK)
        weather = user_message.index(WEATHER_MARK, start)
        places = user_message.index(PLACES_MARK, weather)
        end = user_message.rindex(END_MARK)
    except ValueError:
        return {"rag_context": None, "weather_data": None, "places_data": None}
    blocks = {
        "rag_context": user_message[start + len(RAG_MARK):weather],
        "weather_data": user_message[weather + len(WEATHER_MARK):places],
        "places_data": user_message[places + len(PLACES_MARK):end],
    }
    return {key: None if text == NOT_USED else text for key, text in blocks.items()}


class QuestionTrace:
    """Everything observed while the agent answers one question."""

    def __init__(self):
        self.planner: dict[str, Any] | None = None
        self.plan = None
        self.tools: dict[str, dict[str, Any]] = {}  # server -> executed call
        self.actual_retrieval: dict[str, Any] | None = None
        self.rag_only = False
        self.generation_evidence: dict[str, Any] | None = None


class Tracer:
    """Holds the trace of the current question. `pipeline` is the raw rag_pipeline module, used only
    to reconstruct the RAG-only retrieval and prompt (never handed to the agent)."""

    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.current = QuestionTrace()

    def start(self) -> QuestionTrace:
        self.current = QuestionTrace()
        return self.current

    def finish(self) -> QuestionTrace:
        trace, self.current = self.current, QuestionTrace()
        return trace


class _Delegate:
    def __init__(self, inner, tracer: Tracer):
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_tracer", tracer)

    def __getattr__(self, name):
        return getattr(self._inner, name)


class TracingPlanner(_Delegate):
    def plan(self, question: str):
        trace = self._tracer.current
        try:
            plan = self._inner.plan(question)
        except Exception as exc:
            trace.planner = {"success": False, "use_rag": None, "rag_query": None, "tool_calls": None,
                             "error": error_info(exc)}
            raise
        trace.plan = plan
        trace.planner = {
            "success": True,
            "use_rag": plan.use_rag,
            "rag_query": plan.rag_query,
            "tool_calls": [{"server": c.server, "tool": c.tool, "arguments": jsonable(c.arguments)}
                           for c in plan.tool_calls],
            "error": None,
        }
        return plan


class TracingClient(_Delegate):
    def __init__(self, inner, tracer: Tracer, server: str):
        super().__init__(inner, tracer)
        object.__setattr__(self, "_server", server)

    def call_tool(self, name: str, arguments: dict[str, Any]):
        event = {"tool": name, "arguments": jsonable(arguments), "executed": True,
                 "success": None, "raw_output": None, "error": None}
        self._tracer.current.tools[self._server] = event
        try:
            result = self._inner.call_tool(name, arguments)
        except Exception as exc:
            event.update(success=False, error=error_info(exc))
            raise
        event.update(success=True, raw_output=jsonable(result))  # before any transformation
        return result


class TracingPipeline(_Delegate):
    """Wraps the pipeline the agent uses for RAG combined with tool calls."""

    def retrieve(self, store, query, *args, **kwargs):
        record = {"performed": True, "query": query, "capture_method": OBSERVED, "top3": None, "error": None}
        self._tracer.current.actual_retrieval = record
        try:
            results = self._inner.retrieve(store, query, *args, **kwargs)
        except Exception as exc:
            record["error"] = error_info(exc)
            raise
        record["top3"] = retrieval_records(results)
        return results


class TracingGenerate:
    def __init__(self, inner: Callable, tracer: Tracer):
        self._inner = inner
        self._tracer = tracer

    def __call__(self, messages):
        user = messages[-1].content if messages else ""
        self._tracer.current.generation_evidence = {"capture_method": OBSERVED, **prompt_blocks(user),
                                                    "generator_user_message": user}
        return self._inner(messages)


class TracingRAG(_Delegate):
    """Wraps the D2 RAGAgent; respond() is the unchanged D2 path used for RAG-only plans."""

    def respond(self, question: str):
        trace = self._tracer.current
        trace.rag_only = True
        try:
            return self._inner.respond(question)
        finally:
            self._reconstruct(question, trace)

    def _reconstruct(self, question: str, trace: QuestionTrace) -> None:
        pipeline = self._tracer.pipeline
        record = {"performed": True, "query": question, "capture_method": RECONSTRUCTED, "top3": None, "error": None}
        trace.actual_retrieval = record
        try:
            results = pipeline.retrieve(self._inner.store, question, k=self._inner.config.top_k)
            record["top3"] = retrieval_records(results)
            context = pipeline.build_context(results)
            note = pipeline.conflict_note(results)
            trace.generation_evidence = {
                "capture_method": "reconstructed_d2_prompt",
                "rag_context": f"{context}\n\n{note}" if note else context,
                "weather_data": None,
                "places_data": None,
                "generator_user_message": pipeline.build_messages(question, results)[-1].content,
            }
        except Exception as exc:
            record["error"] = error_info(exc)


def install_tracing(expert, pipeline) -> Tracer:
    """Wrap the agent's injectable attributes; returns the tracer. `pipeline` = raw rag_pipeline module."""

    tracer = Tracer(pipeline)
    expert.planner = TracingPlanner(expert.planner, tracer)
    expert.clients = {name: TracingClient(client, tracer, name) for name, client in expert.clients.items()}
    expert.pipeline = TracingPipeline(expert.pipeline, tracer)
    expert.generate = TracingGenerate(expert.generate, tracer)
    expert.rag = TracingRAG(expert.rag, tracer)
    return tracer


def capability_block(trace: QuestionTrace, server: str) -> dict[str, Any]:
    """Weather/Places block of a raw result: always the same keys, null when not planned."""

    planned = None
    if trace.plan is not None:
        planned = next((c for c in trace.plan.tool_calls if c.server == server), None)
    event = trace.tools.get(server)
    if planned is None and event is None:
        return {"planned": False, "tool": None, "arguments": None, "executed": False,
                "success": None, "raw_output": None, "error": None}
    block = {"planned": planned is not None,
             "tool": planned.tool if planned else event["tool"],
             "arguments": jsonable(planned.arguments) if planned else event["arguments"],
             "executed": event is not None, "success": None, "raw_output": None, "error": None}
    if event is not None:
        block.update(success=event["success"], raw_output=event["raw_output"], error=event["error"])
    return block


def error_stage(trace: QuestionTrace) -> str:
    if trace.planner is not None and not trace.planner["success"]:
        return "planner"
    for server in ("weather", "places"):
        if trace.tools.get(server, {}).get("success") is False:
            return server
    if trace.rag_only:
        return "rag_only_d2_pipeline"
    if trace.generation_evidence is not None:
        return "generation"
    if trace.actual_retrieval is not None:
        return "retrieval"
    return "unknown"

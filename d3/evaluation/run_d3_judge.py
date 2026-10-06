"""D3 V1 LLM-as-Judge runner (Correctness, Faithfulness/Groundedness, Relevance) for the official run.

    uv run python d3/evaluation/run_d3_judge.py                    # validate only (default)
    uv run python d3/evaluation/run_d3_judge.py --validate-only    # same
    uv run python d3/evaluation/run_d3_judge.py --execute --confirm-judge-v1   # the official judge run

Validate-only checks the frozen dataset and protocol, the official raw run, the deterministic scoring and
the judge configuration, counts how many answers would be judged, and exits: no model, client or network
is touched and nothing is written. --execute additionally requires a FROZEN, hashed judge configuration
with a locked provider and model (D3_JUDGE_CONFIG_V1). Answers that do not exist get 0/0/0 without a
judge call (protocol Section 10); every other answer gets exactly one valid judgement (at most one
technical retry). The judge sees only the question, the gold requirements, the evidence the generator
actually received and the final answer: never the oracle retrieval or any deterministic metric.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_d3_evaluation as frozen  # noqa: E402  (stdlib only)
import score_d3_evaluation as det  # noqa: E402  (stdlib only)

CONFIG_JSON = "d3_judge_config_v1.json"
CONFIG_MD = "D3_JUDGE_CONFIG_V1.md"
CONFIG_SHA = "D3_JUDGE_CONFIG_V1.sha256"
RESULTS = "judge_results_v1.jsonl"
JUDGE_MANIFEST = "judge_manifest.json"
REPORT = "D3_LLM_JUDGE_REPORT_V1.md"
JUDGE_SHA = "LLM_JUDGE_V1.sha256"
DIMENSIONS = ("correctness", "faithfulness", "relevance")
SCALE = (0, 1, 2)
LLM_JUDGE, DETERMINISTIC_ZERO = "llm_judge", "protocol_deterministic_zero"
EXIT_OK, EXIT_INVALID, EXIT_ABORTED = 0, 2, 3
ENV_FILE = frozen.REPO_ROOT / ".env"  # read only on --execute; never hashed, logged or persisted
API_KEY_VAR = "OPENAI_API_KEY"
REASONING_EFFORTS = ("minimal", "low", "medium", "high")
TEMPERATURE_NOT_SENT = "not_sent_provider_controlled"
# The frozen D3_JUDGE_CONFIG_V1 judge: a FROZEN configuration must match these values exactly.
OFFICIAL_JUDGE = {"provider": "openai", "model": "gpt-5-mini-2025-08-07",
                  "model_version_or_digest": "gpt-5-mini-2025-08-07", "reasoning_effort": "medium",
                  "max_attempts": 2, "max_output_tokens": 6000, "temperature": None,
                  "temperature_policy": TEMPERATURE_NOT_SENT, "api": "responses", "store": False, "tools": "none",
                  "sdk_max_retries": 0}


def temperature_label(judge: dict[str, Any]) -> str:
    if judge.get("temperature") is None and judge.get("temperature_policy") == TEMPERATURE_NOT_SENT:
        return "not explicitly set / provider-controlled (not sent)"
    return str(judge.get("temperature"))


class JudgeError(RuntimeError):
    """Inputs or configuration are not exactly what the protocol requires; nothing is judged."""


class JudgeOutputError(ValueError):
    """The judge output is not parseable or does not match the strict schema."""


class JudgeAbort(RuntimeError):
    """Every allowed attempt for one answer failed technically; the judge run is aborted."""

    def __init__(self, message: str, attempts: list[dict[str, Any]]):
        super().__init__(message)
        self.attempts = attempts


# ---------------------------------------------------------------------------
# Configuration and input validation (standard library only)
# ---------------------------------------------------------------------------


def _check(condition: Any, message: str) -> None:
    if not condition:
        raise JudgeError(message)


def read_sha_file(path: Path) -> dict[str, str]:
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, _, name = line.strip().partition("  ")
            entries[name.lstrip("*")] = digest
    return entries


def load_judge_config(cfg: frozen.RunnerConfig) -> dict[str, Any]:
    path = cfg.path(CONFIG_JSON)
    _check(path.is_file(), f"judge config missing: {CONFIG_JSON}")
    _check(cfg.path(CONFIG_MD).is_file(), f"judge config document missing: {CONFIG_MD}")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise JudgeError(f"{CONFIG_JSON} is not valid JSON: {exc}") from None
    _check(config.get("config_version") == "D3_JUDGE_CONFIG_V1", "unexpected config_version")
    _check(config.get("status") in ("PREPARED", "FROZEN"), f"invalid config status {config.get('status')!r}")
    judge = config.get("judge") or {}
    # temperature is either 0, or null with the explicit "not sent / provider-controlled" policy; nothing else.
    _check((judge.get("temperature") == 0 and not isinstance(judge.get("temperature"), bool)
            and judge.get("temperature_policy") is None)
           or (judge.get("temperature") is None and judge.get("temperature_policy") == TEMPERATURE_NOT_SENT),
           "judge temperature must be 0, or null with temperature_policy = not_sent_provider_controlled")
    _check(judge.get("max_attempts") == 2, "judge max_attempts must be 2")
    _check(tuple(config.get("dimensions") or ()) == DIMENSIONS, "dimensions must be correctness, faithfulness, relevance")
    _check(tuple(config.get("scale") or ()) == SCALE, "scale must be [0, 1, 2]")
    policy = config.get("input_policy") or {}
    for forbidden in ("include_oracle_retrieval", "include_deterministic_metrics", "include_other_questions"):
        _check(policy.get(forbidden) is False, f"input_policy.{forbidden} must be false")
    no_answer = config.get("no_answer_policy") or {}
    _check(no_answer.get("call_judge") is False and no_answer.get("scores") == {d: 0 for d in DIMENSIONS},
           "no_answer_policy must be 0/0/0 without a judge call")
    _check("aggregation" in config and config["aggregation"].get("composite_score") is None,
           "a composite score is not allowed")
    template = config.get("user_message_template") or ""
    _check(all(f"{{{k}}}" in template for k in ("question", "gold", "evidence", "final_answer")),
           "user_message_template must contain {question}, {gold}, {evidence} and {final_answer}")
    _check(isinstance(config.get("system_prompt"), str) and config["system_prompt"].strip(), "system_prompt missing")
    _check(isinstance(config.get("output_schema"), dict), "output_schema missing")
    _check(isinstance((config.get("source_run") or {}).get("run_id"), str), "source_run.run_id missing")
    if judge.get("provider") == "openai":
        _check(judge.get("api") == "responses", "the OpenAI judge must use the Responses API")
        _check(judge.get("reasoning_effort") in REASONING_EFFORTS, "invalid reasoning_effort")
        _check(isinstance(judge.get("max_output_tokens"), int) and judge["max_output_tokens"] > 0,
               "max_output_tokens must be a positive integer")
        _check(judge.get("store") is False, "store must be false")
        _check(judge.get("tools") == "none", "the judge must not get any tool")
        _check(judge.get("sdk_max_retries") == 0, "SDK retries must be 0 (attempts are controlled by the runner)")
        fmt = judge.get("structured_output") or {}
        _check(fmt.get("type") == "json_schema" and fmt.get("strict") is True and fmt.get("name"),
               "structured_output must be a strict json_schema with a name")

    hashes ={name: frozen.sha256_file(cfg.path(name)) for name in (CONFIG_MD, CONFIG_JSON)}
    sha_path = cfg.path(CONFIG_SHA)
    hashed = False
    if config["status"] == "FROZEN":
        _check(judge.get("provider") and judge.get("model"), "a FROZEN config needs a provider and a model")
        for key, value in OFFICIAL_JUDGE.items():
            _check(key in judge and judge[key] == value and type(judge[key]) is type(value),
                   f"FROZEN judge config: judge.{key} must be {value!r}")
        _check(sha_path.is_file(), f"a FROZEN config needs {CONFIG_SHA}")
    if sha_path.is_file():
        recorded = read_sha_file(sha_path)
        _check(set(recorded) == {CONFIG_MD, CONFIG_JSON}, f"{CONFIG_SHA} must list exactly {CONFIG_MD} and {CONFIG_JSON}")
        _check(recorded == hashes, f"judge config files do not match {CONFIG_SHA}")
        hashed = True
    return {"config": config, "hashes": hashes, "hashed": hashed}


def is_no_answer(record: dict[str, Any]) -> bool:
    answer = record.get("final_answer")
    return not isinstance(answer, str) or not answer.strip()


def validate_inputs(cfg: frozen.RunnerConfig, judge_config: dict[str, Any]) -> dict[str, Any]:
    """Dataset, protocol, official run, deterministic scoring and judge config consistency."""

    config = judge_config["config"]
    source = config["source_run"]
    run_dir = cfg.runs_dir / source["run_id"]
    try:
        validated = det.validate_run(run_dir, cfg)  # dataset + protocol hashes, RUN.sha256, manifest, 35 records
    except det.ScoringError as exc:
        raise JudgeError(f"source run: {exc}") from None
    manifest = validated["manifest"]
    _check(manifest.get("valid_experimental_run") is True, "source run is not a valid experimental run")
    _check(manifest.get("run_id") == source["run_id"], "source run_id differs from the run manifest")
    _check(validated["raw_sha"][det.RAW] == source.get("raw_results_sha256"),
           "raw_results.jsonl differs from the hash recorded in the judge config")
    _check(validated["raw_sha"][det.MANIFEST] == source.get("run_manifest_sha256"),
           "run_manifest.json differs from the hash recorded in the judge config")

    sha_path = run_dir / det.SCORES_SHA
    _check(sha_path.is_file(), f"deterministic scoring hash file missing: {det.SCORES_SHA}")
    recorded = read_sha_file(sha_path)
    _check(set(recorded) == {det.SCORES_JSON, det.REPORT_MD}, f"{det.SCORES_SHA} must list the scores and the report")
    det_hashes = {}
    for name in (det.SCORES_JSON, det.REPORT_MD):
        _check((run_dir / name).is_file(), f"{name} missing")
        det_hashes[name] = frozen.sha256_file(run_dir / name)
        _check(det_hashes[name] == recorded[name], f"{name} does not match {det.SCORES_SHA}")
    _check(det_hashes[det.SCORES_JSON] == source.get("deterministic_scores_sha256"),
           "deterministic_scores_v1.json differs from the hash recorded in the judge config")
    _check(det_hashes[det.REPORT_MD] == source.get("deterministic_report_sha256"),
           "deterministic scoring report differs from the hash recorded in the judge config")
    scores = json.loads((run_dir / det.SCORES_JSON).read_text(encoding="utf-8"))
    _check(scores.get("run_id") == manifest["run_id"], "deterministic scores belong to another run")
    _check((scores.get("inputs") or {}).get("raw_results_sha256") == validated["raw_sha"][det.RAW],
           "deterministic scores were computed from different raw results")

    model = (config.get("judge") or {}).get("model")
    evaluated = {((manifest.get("system") or {}).get(k) or {}).get("model") for k in ("planner", "generator")} - {None}
    _check(model is None or model not in evaluated,
           f"the judge model must differ from the evaluated model(s) {sorted(evaluated)}")

    records = validated["records"]
    return {"run_dir": run_dir, "items": validated["items"], "records": records, "manifest": manifest,
            "frozen": validated["frozen"], "raw_sha": validated["raw_sha"], "deterministic_hashes": det_hashes,
            "deterministic_scores": scores,
            "deterministic_zero_ids": [r["id"] for r in records if is_no_answer(r)],
            "judge_ids": [r["id"] for r in records if not is_no_answer(r)]}


# ---------------------------------------------------------------------------
# Judge input (pure functions)
# ---------------------------------------------------------------------------


def build_judge_payload(item: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """Only the allowed inputs: question, gold requirements, actual generation evidence, final answer.

    Never: oracle retrieval, actual-retrieval records, planner output, expected tools, category, id,
    deterministic metrics or anything about other questions.
    """

    rag = item["rag"]
    gold: dict[str, Any] = {}
    if rag.get("required"):
        gold["essential_facts"] = [{"id": f["id"], "fact": f["fact"]} for f in rag.get("essential_facts", [])]
        gold["evidence_excerpts"] = [{"supports": e["supports"], "text_excerpt": e["text_excerpt"]}
                                     for e in rag.get("evidence", [])]
    gold["answer_requirements"] = item.get("answer_requirements", {})
    if item["weather"].get("required"):
        gold["weather_requirement"] = {"location": item["weather"].get("location_requirement"),
                                       "temporal": item["weather"].get("temporal_requirement")}
    if item["places"].get("required"):
        gold["places_requirement"] = {k: item["places"][f"{k}_requirement"] for k in ("query", "origin", "destination")
                                      if item["places"].get(f"{k}_requirement")}
    evidence = record.get("generation_evidence") or {}
    return {
        "question": item["question"],
        "gold": gold,
        "actual_generation_evidence": {
            "rag_context": evidence.get("rag_context"),
            "weather_data": evidence.get("weather_data"),
            "places_data": evidence.get("places_data"),
            "raw_tool_outputs": {s: (record.get(s) or {}).get("raw_output") for s in ("weather", "places")},
        },
        "final_answer": record.get("final_answer"),
    }


def render_user_message(config: dict[str, Any], payload: dict[str, Any]) -> str:
    def block(value):
        return json.dumps(value, ensure_ascii=False, indent=2)

    return config["user_message_template"].format(
        question=payload["question"], gold=block(payload["gold"]),
        evidence=block(payload["actual_generation_evidence"]), final_answer=payload["final_answer"])


def parse_judge_output(content: Any, max_chars: int) -> dict[str, dict[str, Any]]:
    """Strict schema: exactly the three dimensions, each {score: int in 0..2, reason: non-empty str}."""

    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError as exc:
            raise JudgeOutputError(f"not valid JSON: {exc}") from None
    if not isinstance(content, dict):
        raise JudgeOutputError("the judge output must be a JSON object")
    if set(content) != set(DIMENSIONS):
        raise JudgeOutputError(f"keys must be exactly {list(DIMENSIONS)}, got {sorted(content)}")
    parsed = {}
    for dim in DIMENSIONS:
        entry = content[dim]
        if not isinstance(entry, dict) or set(entry) != {"score", "reason"}:
            raise JudgeOutputError(f"{dim} must be an object with exactly 'score' and 'reason'")
        score, reason = entry["score"], entry["reason"]
        if isinstance(score, bool) or not isinstance(score, int) or score not in SCALE:
            raise JudgeOutputError(f"{dim}.score must be the integer 0, 1 or 2, got {score!r}")
        if not isinstance(reason, str) or not reason.strip():
            raise JudgeOutputError(f"{dim}.reason must be a non-empty string")
        if len(reason) > max_chars:
            raise JudgeOutputError(f"{dim}.reason is longer than {max_chars} characters")
        parsed[dim] = {"score": score, "reason": reason.strip()}
    return parsed


# ---------------------------------------------------------------------------
# Judge client (one small adapter; nothing is imported until --execute)
# ---------------------------------------------------------------------------


@dataclass
class JudgeResponse:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class JudgeClient(Protocol):
    def judge(self, system_prompt: str, user_message: str, output_schema: dict, temperature: float) -> JudgeResponse: ...

    def describe(self) -> dict[str, Any]: ...


class OllamaJudgeClient:
    """Adapter for a local Ollama judge model with JSON-schema output. Available only; not a model choice."""

    def __init__(self, model: str):
        import ollama

        self.model = model
        self._client = ollama.Client()

    def judge(self, system_prompt, user_message, output_schema, temperature):
        response = self._client.chat(model=self.model, format=output_schema, options={"temperature": temperature},
                                     messages=[{"role": "system", "content": system_prompt},
                                               {"role": "user", "content": user_message}])
        meta = {key: getattr(response, key, None) for key in ("model", "created_at", "done_reason",
                                                               "prompt_eval_count", "eval_count", "total_duration")}
        return JudgeResponse(response.message.content, meta)

    def describe(self):
        try:
            import ollama

            digests = {m.model: getattr(m, "digest", None) for m in ollama.list().models}
        except Exception:
            digests = {}
        return {"provider": "ollama", "model": self.model, "reported_digest": digests.get(self.model)}


class JudgeTransportError(RuntimeError):
    """A judge API call failed; the message is sanitised (never contains the API key)."""


_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_\-*.]{4,}")


def redact(text: str, secret: str | None) -> str:
    if secret:
        text = text.replace(secret, "[REDACTED]")
    return _KEY_PATTERN.sub("[REDACTED]", text)


class OpenAIJudgeClient:
    """OpenAI Responses API judge: strict JSON-schema output, store=false, no tools, no background/conversation.

    `sdk` is an `openai.OpenAI` client (created with max_retries=0, so every attempt is a runner attempt).
    The API key is never stored on this object, logged or returned.
    """

    def __init__(self, judge_settings: dict[str, Any], sdk: Any, secret: str | None = None):
        self.settings = judge_settings
        self._sdk = sdk
        self._secret = secret

    def request(self, system_prompt: str, user_message: str, output_schema: dict, temperature) -> dict[str, Any]:
        s = self.settings
        fmt = s["structured_output"]
        kwargs = {
            "model": s["model"],
            "instructions": system_prompt,
            "input": user_message,
            "text": {"format": {"type": "json_schema", "name": fmt["name"], "schema": output_schema, "strict": True}},
            "reasoning": {"effort": s["reasoning_effort"]},
            "max_output_tokens": s["max_output_tokens"],
            "store": False,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        return kwargs

    def judge(self, system_prompt, user_message, output_schema, temperature):
        kwargs = self.request(system_prompt, user_message, output_schema, temperature)
        try:
            response = self._sdk.responses.create(**kwargs)
        except Exception as exc:
            if type(exc).__name__ == "AuthenticationError" or getattr(exc, "status_code", None) == 401:
                raise JudgeTransportError("OpenAI authentication failed") from None
            status = getattr(exc, "status_code", None)
            message = redact(f"{type(exc).__name__}" + (f" (HTTP {status})" if status else "") + f": {exc}",
                             self._secret)
            raise JudgeTransportError(message) from None
        usage = getattr(response, "usage", None)

        def usage_value(*path):
            value = usage
            for name in path:
                value = getattr(value, name, None)
            return value

        metadata = {
            "response_id": getattr(response, "id", None),
            "response_model": getattr(response, "model", None),
            "status": getattr(response, "status", None),
            "incomplete_details": str(getattr(response, "incomplete_details", None) or "") or None,
            "usage": {"input_tokens": usage_value("input_tokens"), "output_tokens": usage_value("output_tokens"),
                      "total_tokens": usage_value("total_tokens"),
                      "reasoning_tokens": usage_value("output_tokens_details", "reasoning_tokens"),
                      "cached_tokens": usage_value("input_tokens_details", "cached_tokens")},
        }
        content = getattr(response, "output_text", None) or ""
        if metadata["status"] not in (None, "completed"):
            content = f"<incomplete response: status={metadata['status']}>"  # fails the schema -> technical retry
        return JudgeResponse(content, metadata)

    def describe(self):
        try:
            from importlib import metadata as md

            sdk_version = md.version("openai")
        except Exception:
            sdk_version = None
        s = self.settings
        return {"provider": "openai", "api": "responses", "model": s["model"], "openai_sdk_version": sdk_version,
                "reasoning_effort": s["reasoning_effort"], "max_output_tokens": s["max_output_tokens"],
                "store": False, "tools": "none", "sdk_max_retries": s["sdk_max_retries"]}


def make_openai_client(config: dict[str, Any], env_file: Path = ENV_FILE,
                       sdk_factory: Callable[[str, dict], Any] | None = None) -> OpenAIJudgeClient:
    """Load .env (existing environment variables win), check OPENAI_API_KEY, build the client. No request is made."""

    from dotenv import load_dotenv

    load_dotenv(env_file, override=False)
    key = (os.environ.get(API_KEY_VAR) or "").strip()
    if not key:
        raise JudgeError(f"{API_KEY_VAR} is not configured.")
    settings = config["judge"]
    if sdk_factory is None:
        def sdk_factory(api_key, s):
            from openai import OpenAI

            return OpenAI(api_key=api_key, max_retries=s["sdk_max_retries"], timeout=s["request_timeout_seconds"])
    return OpenAIJudgeClient(settings, sdk_factory(key, settings), secret=key)


ADAPTERS: dict[str, Callable[[dict], JudgeClient]] = {
    "openai": make_openai_client,
    "ollama": lambda config: OllamaJudgeClient(config["judge"]["model"]),
}


def make_judge_client(config: dict[str, Any]) -> JudgeClient:
    judge = config["judge"]
    adapter = ADAPTERS.get(judge["provider"])
    if adapter is None:
        raise JudgeError(f"no judge adapter for provider {judge['provider']!r}; add one before executing")
    return adapter(config)


# ---------------------------------------------------------------------------
# Judging one answer and the whole run
# ---------------------------------------------------------------------------


def judge_answer(client: JudgeClient, config: dict[str, Any], user_message: str):
    """One official judgement; a second identical attempt only after a technical or schema failure."""

    attempts = []
    for number in range(1, config["judge"]["max_attempts"] + 1):
        try:
            response = client.judge(config["system_prompt"], user_message, config["output_schema"],
                                    config["judge"]["temperature"])
        except Exception as exc:  # transport / API error
            attempts.append({"attempt": number, "kind": "transport_or_api_error",
                             "error": f"{type(exc).__name__}: {exc}", "raw_content": None})
            continue
        try:
            scores = parse_judge_output(response.content, config.get("reason_max_chars", 800))
        except JudgeOutputError as exc:  # unparseable or outside the schema
            attempts.append({"attempt": number, "kind": "invalid_output", "error": str(exc),
                             "raw_content": response.content})
            continue
        attempts.append({"attempt": number, "kind": "valid", "error": None, "raw_content": response.content})
        return scores, attempts, {"raw_content": response.content, "metadata": response.metadata}
    raise JudgeAbort(f"all {len(attempts)} judge attempts failed", attempts)


def zero_record(item: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    reason = config["no_answer_policy"]["reason"]
    return {"id": item["id"], "category": item["category"], "evaluation_method": DETERMINISTIC_ZERO,
            "judge_called": False, "attempts": 0,
            "scores": {d: {"score": 0, "reason": reason} for d in DIMENSIONS},
            "attempt_log": [], "raw_judge_output": None, "error": None}


def aggregate(results: list[dict[str, Any]], categories=frozen.CATEGORIES) -> dict[str, Any]:
    """Mean (0-2) and 0/1/2 distribution per dimension over all questions, overall and per category."""

    def summarise(rows):
        out = {}
        for dim in DIMENSIONS:
            values = [r["scores"][dim]["score"] for r in rows]
            out[dim] = {"n": len(values), "sum": sum(values), "mean": sum(values) / len(values) if values else None,
                        "distribution": {str(s): values.count(s) for s in SCALE}}
        return out

    return {"overall": summarise(results),
            "by_category": {c: summarise([r for r in results if r["category"] == c]) for c in categories}}


def now_local() -> datetime:
    return datetime.now().astimezone()


def write_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def execute(cfg: frozen.RunnerConfig, judge_config: dict[str, Any], inputs: dict[str, Any],
            client_factory: Callable[[dict], JudgeClient] = make_judge_client,
            clock: Callable[[], datetime] = now_local) -> int:
    config = judge_config["config"]
    started = clock()
    judge_run_id = started.strftime("%Y%m%dT%H%M%S%z")
    out_dir = inputs["run_dir"] / "judge" / judge_run_id
    out_dir.mkdir(parents=True, exist_ok=False)  # never overwrite a judge run
    results_path, manifest_path = out_dir / RESULTS, out_dir / JUDGE_MANIFEST
    manifest = {
        "judge_run_id": judge_run_id, "status": "RUNNING", "started_at": started.isoformat(), "finished_at": None,
        "source_run_id": inputs["manifest"]["run_id"],
        "source_raw_results_sha256": inputs["raw_sha"][det.RAW],
        "source_run_manifest_sha256": inputs["raw_sha"][det.MANIFEST],
        "dataset_sha256": inputs["frozen"]["dataset_hashes"],
        "protocol_sha256": inputs["frozen"]["protocol_sha256"],
        "deterministic_scoring_sha256": inputs["deterministic_hashes"],
        "judge_config_sha256": judge_config["hashes"],
        "provider": config["judge"]["provider"], "model": config["judge"]["model"],
        "model_version_or_digest": config["judge"]["model_version_or_digest"], "client_description": None,
        "temperature": config["judge"]["temperature"],
        "temperature_policy": config["judge"].get("temperature_policy"),
        "reasoning_effort": config["judge"].get("reasoning_effort"),
        "max_attempts": config["judge"]["max_attempts"],
        "request_settings": {k: config["judge"].get(k) for k in ("model_family", "api", "reasoning_effort",
                                                                  "max_output_tokens", "store", "tools",
                                                                  "sdk_max_retries", "structured_output")},
        "expected_total_questions": len(inputs["records"]),
        "deterministic_zero_count": len(inputs["deterministic_zero_ids"]),
        "llm_judge_expected_count": len(inputs["judge_ids"]),
        "llm_judge_completed_count": 0, "records_written": 0, "technical_retries": 0,
        "abort_stage": None, "abort_error": None,
    }
    results_path.touch()
    write_json(manifest_path, manifest)

    def abort(stage: str, error: dict[str, Any]) -> int:
        manifest.update(status="ABORTED", abort_stage=stage, abort_error=error, finished_at=clock().isoformat())
        write_json(manifest_path, manifest)
        print(f"JUDGE RUN ABORTED ({stage}): {error.get('message')}\n{out_dir}", file=sys.stderr)
        return EXIT_ABORTED

    try:
        client = client_factory(config)
        manifest["client_description"] = client.describe()
        write_json(manifest_path, manifest)
    except Exception as exc:
        return abort("startup", {"type": type(exc).__name__, "message": str(exc)})

    results = []
    with results_path.open("a", encoding="utf-8", newline="\n") as out:
        for item, record in zip(inputs["items"], inputs["records"]):
            if is_no_answer(record):
                row = zero_record(item, config)
            else:
                message = render_user_message(config, build_judge_payload(item, record))
                started_q = time.monotonic()
                try:
                    scores, attempts, raw = judge_answer(client, config, message)
                except JudgeAbort as exc:
                    failed = {"id": item["id"], "category": item["category"], "evaluation_method": LLM_JUDGE,
                              "judge_called": True, "attempts": len(exc.attempts), "scores": None,
                              "attempt_log": exc.attempts, "raw_judge_output": None,
                              "error": {"type": "JudgeAbort", "message": str(exc)}}
                    out.write(json.dumps(failed, ensure_ascii=False) + "\n")
                    out.flush()
                    manifest["technical_retries"] += max(0, len(exc.attempts) - 1)
                    return abort("judging", {"id": item["id"], "message": str(exc), "attempts": exc.attempts})
                manifest["technical_retries"] += len(attempts) - 1
                manifest["llm_judge_completed_count"] += 1
                row = {"id": item["id"], "category": item["category"], "evaluation_method": LLM_JUDGE,
                       "judge_called": True, "attempts": len(attempts), "scores": scores, "attempt_log": attempts,
                       "raw_judge_output": raw, "duration_seconds": round(time.monotonic() - started_q, 3),
                       "error": None}
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            os.fsync(out.fileno())
            results.append(row)
            manifest["records_written"] += 1
            write_json(manifest_path, manifest)
            print(f"[{item['id']}] {row['evaluation_method']}", flush=True)

    manifest.update(status="COMPLETED", finished_at=clock().isoformat())
    write_json(manifest_path, manifest)
    report = render_report(manifest, aggregate(results), results, inputs["deterministic_scores"])
    (out_dir / REPORT).write_text(report, encoding="utf-8", newline="\n")
    (out_dir / JUDGE_SHA).write_text("".join(f"{frozen.sha256_file(out_dir / n)}  {n}\n"
                                             for n in (RESULTS, JUDGE_MANIFEST, REPORT)), encoding="utf-8", newline="\n")
    print(f"JUDGE RUN COMPLETED: {out_dir}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Report (only after a COMPLETED judge run)
# ---------------------------------------------------------------------------


def _dist(d):
    return " · ".join(f"{s}:{d['distribution'][str(s)]}" for s in SCALE)


def render_report(manifest, agg, results, det_scores) -> str:
    L = []
    a = L.append
    a("# D3 LLM-as-Judge Report V1")
    a("")
    a("## 1. Judge Run")
    a("")
    a("| Field | Value |")
    a("|---|---|")
    provider_name = {"openai": "OpenAI"}.get(manifest["provider"], manifest["provider"])
    a(f"| Judge | {provider_name} {manifest['model']} |")
    a(f"| Model snapshot | {manifest['model_version_or_digest']} |")
    a(f"| Reasoning effort | {manifest.get('reasoning_effort')} |")
    a(f"| Temperature | {temperature_label(manifest)} |")
    for key in ("max_attempts", "judge_run_id", "source_run_id", "started_at", "finished_at", "status"):
        a(f"| {key} | {manifest[key]} |")
    a("")
    a("## 2. Integrity")
    a("")
    a("| Input | SHA-256 |")
    a("|---|---|")
    a(f"| source raw_results.jsonl | `{manifest['source_raw_results_sha256']}` |")
    a(f"| source run_manifest.json | `{manifest['source_run_manifest_sha256']}` |")
    for name, digest in manifest["dataset_sha256"].items():
        a(f"| dataset {name} | `{digest}` |")
    a(f"| protocol | `{manifest['protocol_sha256']}` |")
    for name, digest in manifest["deterministic_scoring_sha256"].items():
        a(f"| deterministic {name} | `{digest}` |")
    for name, digest in manifest["judge_config_sha256"].items():
        a(f"| judge config {name} | `{digest}` |")
    a("")
    a(f"Questions scored: {len(results)}/{manifest['expected_total_questions']} "
      f"({manifest['llm_judge_completed_count']} LLM judgements, "
      f"{manifest['deterministic_zero_count']} protocol deterministic zeros).")
    a("")
    a("## 3. Official Answer Quality Metrics")
    a("")
    a(f"Mean over all {len(results)} questions on the 0–2 scale (deterministic zeros included). No composite score.")
    a("")
    a("| Metric | Mean / 2 | Distribution |")
    a("|---|---:|---|")
    for dim in DIMENSIONS:
        d = agg["overall"][dim]
        a(f"| {dim.capitalize()} | {d['mean']:.3f} | {_dist(d)} |")
    a("")
    a("## 4. Scores by Category")
    a("")
    a("Breakdown of the same metrics (not new metrics).")
    a("")
    a("| Category | Correctness | Faithfulness | Relevance |")
    a("|---|---|---|---|")
    for cat, d in agg["by_category"].items():
        a(f"| {cat} | " + " | ".join(f"{d[dim]['mean']:.2f} ({_dist(d[dim])})" for dim in DIMENSIONS) + " |")
    a("")
    a("## 5. Per-question Scores")
    a("")
    a("| ID | Category | Method | Correctness | Faithfulness | Relevance |")
    a("|---|---|---|---|---|---|")
    for r in results:
        a(f"| {r['id']} | {r['category']} | {r['evaluation_method']} | " +
          " | ".join(str(r["scores"][dim]["score"]) for dim in DIMENSIONS) + " |")
    a("")
    a("## 6. Protocol Deterministic Zeros")
    a("")
    zeros = [r["id"] for r in results if r["evaluation_method"] == DETERMINISTIC_ZERO]
    a(", ".join(zeros) if zeros else "None.")
    a("")
    a("These questions produced no final answer (execution error); protocol Section 10 assigns 0 to all three "
      "dimensions, without a judge call.")
    a("")
    a("## 7. Judge Technical Retries / Errors")
    a("")
    retried = [r["id"] for r in results if r["attempts"] > 1]
    a(f"Technical retries: {manifest['technical_retries']}." + (f" Retried: {', '.join(retried)}." if retried else ""))
    a("")
    a("## 8. Qualitative Error Examples")
    a("")
    a("Judge reasons for every dimension scored below 2 by the LLM judge (verbatim; scores are not modified).")
    a("")
    rows = [(r["id"], dim, r["scores"][dim]) for r in results if r["evaluation_method"] == LLM_JUDGE
            for dim in DIMENSIONS if r["scores"][dim]["score"] < 2]
    if rows:
        a("| ID | Dimension | Score | Reason |")
        a("|---|---|---|---|")
        for qid, dim, s in rows:
            a(f"| {qid} | {dim} | {s['score']} | {s['reason'].replace('|', '/').replace(chr(10), ' ')} |")
    else:
        a("None.")
    a("")
    a("## 9. Interpretation Boundaries")
    a("")
    for line in [
        "Correctness is judged against the frozen gold (Essential Facts and evidence excerpts) and, for weather/places "
        "values, the raw tool outputs of the same run.",
        "Faithfulness/Groundedness is judged against the evidence the generator actually received (generation evidence "
        "and raw tool outputs), never the oracle retrieval.",
        "Relevance is judged against the question.",
        "The judge was instructed not to use external knowledge; it saw no deterministic metric, no oracle retrieval, "
        "no planner output and no other question.",
        "There is no composite or weighted score; the three dimensions are reported separately.",
        "Each answer has a single official judgement; retries were only technical/schema retries with identical input.",
    ]:
        a(f"- {line}")
    a("")
    a("## 10. Final D3 Evaluation Summary")
    a("")
    o = det_scores["official_metrics"]
    ecm, ta, r = o["exact_capability_match"], o["tool_accuracy"], o["retrieval"]
    a("| Block | Metric | Result |")
    a("|---|---|---|")
    a(f"| Agency | Exact Capability Match | {ecm['correct']}/{ecm['total']} ({100 * ecm['value']:.1f}%) |")
    a(f"| Agency | Tool Accuracy | {ta['correct']}/{ta['total']} ({100 * ta['value']:.1f}%) |")
    a(f"| Retrieval | Hit@3 | {r['hit_at_3']['hits']}/{r['hit_at_3']['total']} ({100 * r['hit_at_3']['value']:.1f}%) |")
    a(f"| Retrieval | Recall@3 (macro) | {r['macro_recall_at_3']['value']:.3f} |")
    a(f"| Retrieval | MRR | {r['mrr']['value']:.3f} |")
    for dim in DIMENSIONS:
        d = agg["overall"][dim]
        a(f"| Answer Quality | {dim.capitalize()} | {d['mean']:.3f} / 2 ({_dist(d)}) |")
    a("")
    a("No global average is computed across blocks or dimensions.")
    a("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None, cfg: frozen.RunnerConfig | None = None,
         client_factory: Callable[[dict], JudgeClient] = make_judge_client,
         clock: Callable[[], datetime] = now_local) -> int:
    cfg = cfg or frozen.RunnerConfig()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="D3 V1 LLM-as-Judge runner.")
    parser.add_argument("--validate-only", action="store_true", help="validate and exit (the default)")
    parser.add_argument("--execute", action="store_true", help="run the official judge")
    parser.add_argument("--confirm-judge-v1", action="store_true", help="required together with --execute")
    args = parser.parse_args(argv)
    if args.validate_only and args.execute:
        print("ERROR: --validate-only and --execute are mutually exclusive; nothing was started", file=sys.stderr)
        return EXIT_INVALID
    if args.execute and not args.confirm_judge_v1:
        print("ERROR: --execute requires --confirm-judge-v1; nothing was started", file=sys.stderr)
        return EXIT_INVALID
    try:
        judge_config = load_judge_config(cfg)
        config = judge_config["config"]
        if args.execute and (config["status"] != "FROZEN" or not config["judge"].get("model")
                             or not judge_config["hashed"]):
            raise JudgeError("the judge configuration is not FROZEN (judge model not locked / config not hashed)")
        inputs = validate_inputs(cfg, judge_config)
    except JudgeError as exc:
        print(f"JUDGE VALIDATION FAILED: {exc}; nothing was started", file=sys.stderr)
        return EXIT_INVALID
    judge = config["judge"]
    zeros = inputs["deterministic_zero_ids"]
    print("D3 V1 JUDGE VALIDATION OK")
    print(f"  source run: {inputs['manifest']['run_id']} (COMPLETED; RUN.sha256 OK; deterministic scoring hash OK)")
    print("  dataset V1 and protocol V1 hashes: OK")
    print(f"  judge config: {config['status']} (provider={judge['provider']}, model={judge['model']}, "
          f"max_attempts={judge['max_attempts']}, hashed={judge_config['hashed']})")
    print(f"  temperature: {temperature_label(judge)} (config value: {json.dumps(judge['temperature'])})")
    print(f"  questions: {len(inputs['records'])} total; {len(zeros)} protocol deterministic-zero "
          f"({', '.join(zeros) or '-'}); {len(inputs['judge_ids'])} requiring LLM judge")
    print(f"  judge request: reasoning_effort={judge.get('reasoning_effort')}, "
          f"max_output_tokens={judge.get('max_output_tokens')}, store={judge.get('store')}, tools={judge.get('tools')}")
    if not args.execute:
        if config["status"] == "FROZEN" and judge_config["hashed"]:
            print("READY TO JUDGE")
        else:
            print(f"NOT READY TO JUDGE: judge config is {config['status']} and not hashed "
                  f"({config.get('status_note', '')})")
        print("  validate-only: no API key read, no judge client, model or network used; nothing written")
        return EXIT_OK
    print("STARTING OFFICIAL D3 V1 JUDGE RUN")
    return execute(cfg, judge_config, inputs, client_factory, clock)


if __name__ == "__main__":
    sys.exit(main())

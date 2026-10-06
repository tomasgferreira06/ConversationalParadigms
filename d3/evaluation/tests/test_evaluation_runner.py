"""D3 evaluation runner and tracing, fully offline.

Synthetic datasets ("Pergunta de teste ...") and fakes only: no Internet, Ollama, embedding model,
Chroma store or MCP process, and no D3_Q01-D3_Q35 question is ever passed to a planner, retriever,
agent or tool. The real CoimbraExpertAgent class is used with fake dependencies, so the tracing is
tested against the real orchestration code.
"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

EVAL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = EVAL_DIR.parents[1]
for _p in (EVAL_DIR, REPO_ROOT / "d3" / "coimbra_expert"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from langchain_core.documents import Document  # noqa: E402

import evaluation_trace as et  # noqa: E402
import expert_agent as ea  # noqa: E402
import prompts  # noqa: E402
import run_d3_evaluation as runner  # noqa: E402
from places_mcp_client import PlacesMCPError  # noqa: E402
from planner import Plan, PlannerError, ToolCall  # noqa: E402
from weather_mcp_client import WeatherMCPError  # noqa: E402

TODAY = date(2026, 10, 6)
CATEGORIES = runner.CATEGORIES
TOOL_FOR = {"weather": ("get_current_weather", "get_weather_forecast"),
            "places": ("search_place", "get_distance_between_places")}
DOC = Document(page_content="Texto sintético do chunk A.", id="doc-a::c0001",
               metadata={"chunk_id": "doc-a::c0001", "document_id": "doc-a", "title": "Doc A",
                         "source_type": "web", "canonical_url": "https://example.invalid/a",
                         "section_path": ["Secção 1"]})
ORACLE_DOC = Document(page_content="Texto sintético do chunk gold.", id="doc-g::c0002",
                      metadata={"chunk_id": "doc-g::c0002", "document_id": "doc-g", "title": "Doc G",
                                "source_type": "web", "canonical_url": "https://example.invalid/g"})
METRIC_KEYS = {"exact_capability_match", "ecm", "tool_accuracy", "hit_at_3", "hit@3", "recall_at_3",
               "recall@3", "mrr", "reciprocal_rank", "correctness", "faithfulness", "relevance", "score",
               "judge_score"}
RECORD_KEYS = {"id", "category", "question", "timing", "gold_snapshot", "planner", "actual_retrieval",
               "oracle_retrieval", "weather", "places", "generation_evidence", "final_answer", "error"}
CAP_KEYS = {"planned", "tool", "arguments", "executed", "success", "raw_output", "error"}


# ---------------------------------------------------------------------------
# Synthetic dataset fixtures
# ---------------------------------------------------------------------------


def make_items():
    items, n = [], 0
    for category in CATEGORIES:
        parts = {p.lower() for p in category.split("+")}
        for k in range(5):
            n += 1
            qid = f"D3_Q{n:02d}"
            caps = {"rag": "rag" in parts, "weather": "weather" in parts, "places": "places" in parts}
            items.append({
                "id": qid, "category": category, "difficulty": "easy",
                "question": f"Pergunta de teste {qid}",
                "gold_capabilities": caps,
                "rag": {"required": caps["rag"],
                        "information_need": f"necessidade sintética {qid}" if caps["rag"] else None,
                        "gold_chunks": ["doc-g::c0002"] if caps["rag"] else []},
                "weather": {"required": caps["weather"],
                            "expected_tool": TOOL_FOR["weather"][k % 2] if caps["weather"] else None},
                "places": {"required": caps["places"],
                           "expected_tool": TOOL_FOR["places"][k % 2] if caps["places"] else None},
            })
    return items


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_fixture(root: Path, items=None, mutate_after_hash=None):
    root.mkdir(parents=True, exist_ok=True)
    (root / runner.DATASET_JSON).write_text(json.dumps({"items": make_items() if items is None else items}),
                                            encoding="utf-8")
    (root / runner.DATASET_MD).write_text("md sintético\n", encoding="utf-8")
    (root / runner.DATASET_AUDIT).write_text("audit sintético\n", encoding="utf-8")
    (root / runner.PROTOCOL).write_text("protocolo sintético\n", encoding="utf-8")
    names = (runner.DATASET_MD, runner.DATASET_JSON, runner.DATASET_AUDIT)
    (root / runner.DATASET_SHA).write_text("".join(f"{sha(root / n)}  {n}\n" for n in names), encoding="utf-8")
    (root / runner.PROTOCOL_SHA).write_text(f"{sha(root / runner.PROTOCOL)}  {runner.PROTOCOL}\n", encoding="utf-8")
    if mutate_after_hash:
        mutate_after_hash(root)
    return runner.RunnerConfig(eval_dir=root, runs_dir=root / "runs", pinned_dataset=None, pinned_protocol=None)


class Clock:
    def __init__(self):
        self.t = datetime(2026, 10, 6, 17, 0, 0, tzinfo=timezone(timedelta(hours=1)))

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


# ---------------------------------------------------------------------------
# Fake system: the real CoimbraExpertAgent with fake dependencies
# ---------------------------------------------------------------------------


def gold_plan(item):
    caps, qid = item["gold_capabilities"], item["id"]
    calls = []
    if caps["weather"]:
        tool = item["weather"]["expected_tool"]
        args = {"location": "Coimbra, Portugal"} if tool == "get_current_weather" \
            else {"location": "Coimbra, Portugal", "days": 2}
        calls.append(ToolCall("weather", tool, args))
    if caps["places"]:
        tool = item["places"]["expected_tool"]
        args = {"query": f"Local {qid}, Coimbra", "country_code": "pt"} if tool == "search_place" \
            else {"origin": f"A {qid}", "destination": f"B {qid}", "country_code": "pt"}
        calls.append(ToolCall("places", tool, args))
    rag_query = f"consulta do planner {qid}" if caps["rag"] and calls else None
    return Plan(caps["rag"], rag_query, tuple(calls))


class FakePlanner:
    def __init__(self, plans, log):
        self.plans, self.log = plans, log

    def plan(self, question):
        self.log.append(("planner", question))
        outcome = self.plans[question]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, server, log):
        self.server, self.log, self.closed = server, log, 0

    def call_tool(self, name, arguments):
        self.log.append((self.server, name, dict(arguments)))
        if any(isinstance(v, str) and "FAIL" in v for v in arguments.values()):
            error = WeatherMCPError if self.server == "weather" else PlacesMCPError
            raise error(f"{self.server} tool {name} returned an error: sintético")
        return {"server": self.server, "tool": name, "echo": dict(arguments), "value": 12.5}

    def close(self):
        self.closed += 1


class FakeRAG:
    def __init__(self, log):
        self.log, self.store = log, object()
        self.config = mock.Mock(top_k=3)

    def respond(self, question):
        self.log.append(("rag.respond", question))
        return "Resposta RAG sintética.\n\nFontes:\n- Doc A"


def fake_pipeline(log, name, doc=DOC):
    pipeline = mock.Mock(wraps=ea.rag_pipeline)

    def retrieve(store, query, k=3):
        log.append((name, query))
        return [(doc, 0.2)]

    pipeline.retrieve = mock.Mock(side_effect=retrieve)
    return pipeline


class Crash(BaseException):
    """Simulates the process dying mid-run (not an ordinary per-question exception)."""


class FakeSystem:
    def __init__(self, plans, crash_on=None, oracle_error=False):
        self.log = []
        self.weather, self.places = FakeClient("weather", self.log), FakeClient("places", self.log)
        self.rag = FakeRAG(self.log)
        self.generate_messages = []

        def generate(messages):
            self.log.append(("generate", messages[-1].content))
            self.generate_messages.append(messages)
            return "Resposta final sintética."

        planner = FakePlanner(plans, self.log)
        self.expert = ea.CoimbraExpertAgent(self.rag, planner, {"weather": self.weather, "places": self.places},
                                            generate=generate, pipeline=fake_pipeline(self.log, "agent.retrieve"),
                                            today=lambda: TODAY)
        self.tracer = et.install_tracing(self.expert, fake_pipeline(self.log, "reconstruct.retrieve"))
        self.oracle_error = oracle_error
        self.closed = 0
        if crash_on:
            original = self.expert.respond

            def respond(question):
                if question == crash_on:
                    raise Crash("processo morreu")
                return original(question)

            self.expert.respond = respond

    def oracle_retrieve(self, query):
        self.log.append(("oracle", query))
        if self.oracle_error:
            raise RuntimeError("oracle sintético falhou")
        return [(ORACLE_DOC, 0.1), (DOC, 0.3)]

    def describe(self):
        return {"fake_system": True}

    def close(self):
        self.closed += 1
        return {"closed": True}


def keys_recursive(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from keys_recursive(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from keys_recursive(inner)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def assert_invalid(self, cfg, fragment):
        with self.assertRaises(runner.ValidationError) as ctx:
            runner.validate(cfg)
        self.assertIn(fragment, str(ctx.exception))

    def test_valid_dataset_passes(self):
        result = runner.validate(write_fixture(self.root))
        self.assertEqual(result["summary"]["questions"], 35)
        self.assertEqual(result["summary"]["capabilities"], {"rag": 20, "weather": 20, "places": 20})
        self.assertTrue(all(n == 5 for n in result["summary"]["by_category"].values()))

    def test_wrong_dataset_hash_aborts(self):
        cfg = write_fixture(self.root, mutate_after_hash=lambda r: (r / runner.DATASET_MD).write_text("alterado"))
        self.assert_invalid(cfg, "hash mismatch")

    def test_dataset_hash_differs_from_pinned_value_aborts(self):
        cfg = write_fixture(self.root)
        pinned = {name: "0" * 64 for name in (runner.DATASET_MD, runner.DATASET_JSON, runner.DATASET_AUDIT)}
        self.assert_invalid(runner.RunnerConfig(cfg.eval_dir, cfg.runs_dir, pinned, None), "pinned")

    def test_wrong_protocol_hash_aborts(self):
        cfg = write_fixture(self.root, mutate_after_hash=lambda r: (r / runner.PROTOCOL).write_text("alterado"))
        self.assert_invalid(cfg, runner.PROTOCOL)

    def test_protocol_hash_differs_from_pinned_value_aborts(self):
        cfg = write_fixture(self.root)
        self.assert_invalid(runner.RunnerConfig(cfg.eval_dir, cfg.runs_dir, None, "0" * 64), "pinned")

    def test_missing_dataset_aborts(self):
        cfg = write_fixture(self.root, mutate_after_hash=lambda r: (r / runner.DATASET_JSON).unlink())
        self.assert_invalid(cfg, "dataset missing")

    def test_invalid_json_aborts(self):
        cfg = write_fixture(self.root, mutate_after_hash=lambda r: (r / runner.DATASET_JSON).write_text("{"))
        self.assert_invalid(cfg, "not valid JSON")

    def test_34_questions_abort(self):
        self.assert_invalid(write_fixture(self.root, items=make_items()[:34]), "expected 35")

    def test_duplicated_id_aborts(self):
        items = make_items()
        items[1]["id"] = items[0]["id"]
        self.assert_invalid(write_fixture(self.root, items=items), "duplicated IDs")

    def test_category_balance_aborts(self):
        items = make_items()
        items[5].update(category="RAG", gold_capabilities={"rag": True, "weather": False, "places": False})
        items[5]["rag"] = {"required": True, "information_need": "x", "gold_chunks": ["c"]}
        items[5]["weather"] = {"required": False, "expected_tool": None}
        self.assert_invalid(write_fixture(self.root, items=items), "category balance")

    def test_capability_inconsistent_with_category_aborts(self):
        items = make_items()
        items[0]["gold_capabilities"]["places"] = True
        self.assert_invalid(write_fixture(self.root, items=items), "do not match category")

    def test_capability_counts_are_checked(self):
        items = make_items()
        items[0]["gold_capabilities"]["weather"] = True  # Weather would be 21
        cfg = write_fixture(self.root, items=items)
        with mock.patch.object(runner, "_check_item"):  # bypass per-item consistency to reach the count check
            self.assert_invalid(cfg, "20/20/20")

    def test_rag_question_without_information_need_aborts(self):
        items = make_items()
        items[0]["rag"]["information_need"] = ""
        self.assert_invalid(write_fixture(self.root, items=items), "information_need")

    def test_real_frozen_dataset_and_protocol_validate(self):
        result = runner.validate(runner.RunnerConfig())  # reads the frozen files only
        self.assertEqual(result["dataset_hashes"], runner.PINNED_DATASET_SHA256)
        self.assertEqual(result["protocol_sha256"], runner.PINNED_PROTOCOL_SHA256)


# ---------------------------------------------------------------------------
# CLI safety
# ---------------------------------------------------------------------------


class CliSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = write_fixture(Path(self.tmp.name))
        self.factory = mock.Mock(side_effect=AssertionError("the system must not be started"))

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *argv, cfg=None):
        with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            return runner.main(list(argv), cfg=cfg or self.cfg, system_factory=self.factory)

    def test_default_is_validate_only(self):
        self.assertEqual(self.run_main(), runner.EXIT_OK)
        self.factory.assert_not_called()
        self.assertFalse(self.cfg.runs_dir.exists())

    def test_validate_only_flag_writes_nothing(self):
        self.assertEqual(self.run_main("--validate-only"), runner.EXIT_OK)
        self.factory.assert_not_called()
        self.assertFalse(self.cfg.runs_dir.exists())

    def test_confirm_without_execute_does_not_start(self):
        self.assertEqual(self.run_main("--confirm-frozen-v1"), runner.EXIT_OK)
        self.factory.assert_not_called()
        self.assertFalse(self.cfg.runs_dir.exists())

    def test_execute_without_confirmation_aborts_before_the_agent(self):
        self.assertEqual(self.run_main("--execute"), runner.EXIT_INVALID)
        self.factory.assert_not_called()
        self.assertFalse(self.cfg.runs_dir.exists())

    def test_execute_with_invalid_dataset_aborts_before_the_agent(self):
        bad = write_fixture(Path(self.tmp.name) / "bad", items=make_items()[:34])
        self.assertEqual(self.run_main("--execute", "--confirm-frozen-v1", cfg=bad), runner.EXIT_INVALID)
        self.factory.assert_not_called()
        self.assertFalse(bad.runs_dir.exists())

    def test_validate_and_execute_together_rejected(self):
        self.assertEqual(self.run_main("--validate-only", "--execute", "--confirm-frozen-v1"), runner.EXIT_INVALID)
        self.factory.assert_not_called()

    def test_real_validate_only_loads_no_model_store_or_mcp(self):
        """Fresh interpreter: validate-only on the frozen files imports none of the heavy modules."""

        heavy = ["rag_pipeline", "expert_agent", "agents", "planner", "evaluation_trace", "chromadb", "torch",
                 "langchain_ollama", "langchain_huggingface", "langchain_chroma", "mcp", "ollama", "httpx"]
        code = ("import sys; sys.path.insert(0, r'%s'); import run_d3_evaluation as r; "
                "rc = r.main(['--validate-only']); "
                "print('RC', rc); print('HEAVY', [m for m in %r if m in sys.modules])" % (EVAL_DIR, heavy))
        runs_before = (EVAL_DIR / "runs").exists()
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8",
                             timeout=120, cwd=REPO_ROOT)
        self.assertIn("RC 0", out.stdout, out.stderr)
        self.assertIn("HEAVY []", out.stdout)
        self.assertEqual((EVAL_DIR / "runs").exists(), runs_before)


# ---------------------------------------------------------------------------
# Tracing is observational only
# ---------------------------------------------------------------------------


def plain_agent(plan_or_error):
    log = []
    plans = {"Pergunta de teste T": plan_or_error}
    weather, places, rag = FakeClient("weather", log), FakeClient("places", log), FakeRAG(log)

    def generate(messages):
        log.append(("generate", [m.content for m in messages]))
        return "Resposta final sintética."

    agent = ea.CoimbraExpertAgent(rag, FakePlanner(plans, log), {"weather": weather, "places": places},
                                  generate=generate, pipeline=fake_pipeline(log, "agent.retrieve"), today=lambda: TODAY)
    return agent, log


W_CURRENT = ToolCall("weather", "get_current_weather", {"location": "Coimbra, Portugal"})
W_FAIL = ToolCall("weather", "get_weather_forecast", {"location": "FAIL, Portugal", "days": 2})
P_SEARCH = ToolCall("places", "search_place", {"query": "Local X, Coimbra", "country_code": "pt"})
P_FAIL = ToolCall("places", "get_distance_between_places", {"origin": "FAIL", "destination": "B", "country_code": "pt"})
SCENARIOS = {
    "rag_only": Plan(True, None, ()),
    "rag_weather": Plan(True, "consulta X", (W_CURRENT,)),
    "weather_places": Plan(False, None, (W_CURRENT, P_SEARCH)),
    "all_three": Plan(True, "consulta Y", (W_CURRENT, P_SEARCH)),
    "weather_error": Plan(False, None, (W_FAIL, P_SEARCH)),
    "places_error": Plan(True, "consulta Z", (W_CURRENT, P_FAIL)),
    "planner_error": PlannerError("plano inválido duas vezes"),
}


class TracingTransparencyTests(unittest.TestCase):
    def outcome(self, agent):
        try:
            return ("ok", agent.respond("Pergunta de teste T"))
        except Exception as exc:
            return ("error", type(exc).__name__, str(exc))

    def test_traced_agent_behaves_exactly_like_the_plain_agent(self):
        for name, plan in SCENARIOS.items():
            with self.subTest(name):
                plain, plain_log = plain_agent(plan)
                traced, traced_log = plain_agent(plan)
                et.install_tracing(traced, fake_pipeline([], "reconstruct.retrieve"))
                self.assertEqual(self.outcome(plain), self.outcome(traced))
                self.assertEqual(plain_log, traced_log)  # same calls, same arguments, same order

    def test_close_is_delegated_to_every_mcp_client(self):
        agent, _ = plain_agent(SCENARIOS["rag_only"])
        weather, places = agent.clients["weather"], agent.clients["places"]
        et.install_tracing(agent, fake_pipeline([], "r"))
        agent.close()
        self.assertEqual((weather.closed, places.closed), (1, 1))

    def test_not_used_marker_matches_the_prompts_module(self):
        self.assertEqual(et.NOT_USED, prompts.NOT_USED)
        msg = prompts.final_messages("Q?", TODAY, "CTX [Fonte 1]", weather_data=None, places_data={"a": 1})[-1].content
        blocks = et.prompt_blocks(msg)
        self.assertEqual(blocks["rag_context"], "CTX [Fonte 1]")
        self.assertIsNone(blocks["weather_data"])
        self.assertEqual(json.loads(blocks["places_data"]), {"a": 1})

    def test_expert_agent_has_no_evaluation_hooks(self):
        import inspect

        self.assertNotIn("trace", inspect.getsource(ea).lower())


# ---------------------------------------------------------------------------
# Raw results of a (fake) run
# ---------------------------------------------------------------------------


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = write_fixture(Path(self.tmp.name))
        self.validation = runner.validate(self.cfg)
        self.items = self.validation["items"]
        self.plans = {item["question"]: gold_plan(item) for item in self.items}

    def tearDown(self):
        self.tmp.cleanup()

    def execute(self, system):
        with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            rc = runner.execute(self.cfg, self.validation, system_factory=lambda: system, clock=Clock())
        run_dir = next(self.cfg.runs_dir.iterdir())
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        raw = (run_dir / "raw_results.jsonl").read_text(encoding="utf-8").splitlines()
        return rc, run_dir, manifest, [json.loads(line) for line in raw]

    @staticmethod
    def by_id(records):
        return {r["id"]: r for r in records}

    def test_completed_run_schema_order_and_hashes(self):
        system = FakeSystem(self.plans)
        rc, run_dir, manifest, records = self.execute(system)
        self.assertEqual(rc, runner.EXIT_OK)
        self.assertEqual(manifest["status"], "COMPLETED")
        self.assertTrue(manifest["valid_experimental_run"])
        self.assertEqual(manifest["question_count_completed"], 35)
        self.assertEqual(manifest["run_id"], "20261006T170001+0100")
        self.assertEqual([r["id"] for r in records], [i["id"] for i in self.items])
        for record in records:
            self.assertEqual(set(record), RECORD_KEYS)
            self.assertEqual(set(record["weather"]), CAP_KEYS)
            self.assertEqual(set(record["places"]), CAP_KEYS)
            self.assertEqual(set(record["timing"]), {"started_at", "finished_at", "duration_seconds"})
            self.assertEqual(set(record["generation_evidence"]),
                             {"capture_method", "rag_context", "weather_data", "places_data", "generator_user_message"})
        lines = (run_dir / "RUN.sha256").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines, [f"{sha(run_dir / 'raw_results.jsonl')}  raw_results.jsonl",
                                 f"{sha(run_dir / 'run_manifest.json')}  run_manifest.json"])
        self.assertEqual(system.closed, 1)
        self.assertEqual(sum(1 for e in system.log if e[0] == "planner"), 35)  # each question exactly once

    def test_gold_snapshot_is_minimal(self):
        records = self.by_id(self.execute(FakeSystem(self.plans))[3])
        snap = records["D3_Q21"]["gold_snapshot"]
        self.assertEqual(set(snap), {"capabilities", "expected_weather_tool", "expected_places_tool"})

    def test_unused_capabilities_are_null(self):
        records = self.by_id(self.execute(FakeSystem(self.plans))[3])
        rag_only = records["D3_Q01"]
        self.assertEqual(rag_only["weather"], {"planned": False, "tool": None, "arguments": None, "executed": False,
                                               "success": None, "raw_output": None, "error": None})
        self.assertFalse(rag_only["places"]["planned"])
        weather_only = records["D3_Q06"]
        self.assertFalse(weather_only["actual_retrieval"]["performed"])
        self.assertIsNone(weather_only["actual_retrieval"]["top3"])
        self.assertFalse(weather_only["oracle_retrieval"]["required_by_gold"])
        self.assertIsNone(weather_only["oracle_retrieval"]["query"])
        self.assertIsNone(weather_only["generation_evidence"]["rag_context"])
        self.assertIsNone(weather_only["generation_evidence"]["places_data"])

    def test_planner_error_is_recorded(self):
        self.plans[self.items[2]["question"]] = PlannerError("plano inválido duas vezes")
        records = self.by_id(self.execute(FakeSystem(self.plans))[3])
        record = records["D3_Q03"]
        self.assertFalse(record["planner"]["success"])
        self.assertEqual(record["planner"]["error"]["type"], "PlannerError")
        self.assertEqual(record["error"]["stage"], "planner")
        self.assertIsNone(record["final_answer"])
        self.assertTrue(records["D3_Q04"]["planner"]["success"])  # the run continued

    def test_weather_error_is_recorded_and_later_call_not_executed(self):
        item = self.items[25]  # WEATHER+PLACES
        self.plans[item["question"]] = Plan(False, None, (W_FAIL, P_SEARCH))
        record = self.by_id(self.execute(FakeSystem(self.plans))[3])[item["id"]]
        self.assertTrue(record["weather"]["executed"])
        self.assertFalse(record["weather"]["success"])
        self.assertEqual(record["weather"]["error"]["type"], "WeatherMCPError")
        self.assertEqual(record["weather"]["arguments"], {"location": "FAIL, Portugal", "days": 2})
        self.assertTrue(record["places"]["planned"])
        self.assertFalse(record["places"]["executed"])
        self.assertEqual(record["error"]["stage"], "weather")

    def test_places_error_is_recorded(self):
        item = self.items[20]  # RAG+PLACES
        self.plans[item["question"]] = Plan(True, "consulta", (P_FAIL,))
        record = self.by_id(self.execute(FakeSystem(self.plans))[3])[item["id"]]
        self.assertFalse(record["places"]["success"])
        self.assertEqual(record["places"]["error"]["type"], "PlacesMCPError")
        self.assertEqual(record["error"]["stage"], "places")
        self.assertIsNone(record["final_answer"])

    def test_raw_tool_output_and_final_answer_are_recorded(self):
        record = self.by_id(self.execute(FakeSystem(self.plans))[3])["D3_Q31"]
        self.assertTrue(record["weather"]["success"])
        self.assertEqual(record["weather"]["raw_output"]["value"], 12.5)
        self.assertEqual(record["places"]["raw_output"]["server"], "places")
        self.assertTrue(record["final_answer"].startswith("Resposta final sintética."))
        self.assertIsNone(record["error"])
        evidence = record["generation_evidence"]
        self.assertEqual(evidence["capture_method"], et.OBSERVED)
        self.assertIn("Texto sintético do chunk A.", evidence["rag_context"])
        self.assertEqual(json.loads(evidence["places_data"])["server"], "places")
        self.assertIn("[USER QUESTION]", evidence["generator_user_message"])

    def test_actual_retrieval_combined_is_observed_with_planner_query(self):
        record = self.by_id(self.execute(FakeSystem(self.plans))[3])["D3_Q16"]
        actual = record["actual_retrieval"]
        self.assertEqual(actual["capture_method"], et.OBSERVED)
        self.assertEqual(actual["query"], "consulta do planner D3_Q16")
        self.assertEqual((actual["top3"][0]["rank"], actual["top3"][0]["chunk_id"]), (1, "doc-a::c0001"))

    def test_actual_retrieval_rag_only_is_reconstructed_with_original_question(self):
        record = self.by_id(self.execute(FakeSystem(self.plans))[3])["D3_Q02"]
        actual = record["actual_retrieval"]
        self.assertEqual(actual["capture_method"], et.RECONSTRUCTED)
        self.assertEqual(actual["query"], "Pergunta de teste D3_Q02")
        self.assertEqual(record["final_answer"], "Resposta RAG sintética.\n\nFontes:\n- Doc A")
        self.assertEqual(record["generation_evidence"]["capture_method"], "reconstructed_d2_prompt")
        self.assertIn("Texto sintético do chunk A.", record["generation_evidence"]["generator_user_message"])

    def test_oracle_retrieval_uses_the_gold_information_need(self):
        system = FakeSystem(self.plans)
        records = self.by_id(self.execute(system)[3])
        oracle_queries = [e[1] for e in system.log if e[0] == "oracle"]
        rag_items = [i for i in self.items if i["gold_capabilities"]["rag"]]
        self.assertEqual(oracle_queries, [i["rag"]["information_need"] for i in rag_items])
        record = records["D3_Q01"]["oracle_retrieval"]
        self.assertEqual(record["query"], "necessidade sintética D3_Q01")
        self.assertEqual([r["chunk_id"] for r in record["top3"]], ["doc-g::c0002", "doc-a::c0001"])

    def test_oracle_retrieval_never_reaches_the_agent_or_generation(self):
        system = FakeSystem(self.plans)
        records = self.execute(system)[3]
        needs = [i["rag"]["information_need"] for i in self.items if i["gold_capabilities"]["rag"]]
        agent_events = [json.dumps(e, ensure_ascii=False, default=str) for e in system.log if e[0] != "oracle"]
        for need in needs:
            self.assertFalse(any(need in event for event in agent_events), need)
        for messages in system.generate_messages:
            self.assertNotIn("Texto sintético do chunk gold.", messages[-1].content)
        for record in records:  # the oracle chunk never appears in what the agent used or answered
            used = json.dumps([record["actual_retrieval"], record["generation_evidence"], record["final_answer"]],
                              ensure_ascii=False)
            self.assertNotIn("doc-g::c0002", used)
        # every oracle call comes after the agent's last event for that question
        for index, event in enumerate(system.log):
            if event[0] == "oracle":
                qid = event[1].rsplit(" ", 1)[1]
                later = [e for e in system.log[index + 1:] if qid in json.dumps(e, ensure_ascii=False, default=str)]
                self.assertEqual(later, [])

    def test_oracle_failure_is_recorded_without_stopping(self):
        rc, _, manifest, records = self.execute(FakeSystem(self.plans, oracle_error=True))
        self.assertEqual(rc, runner.EXIT_OK)
        self.assertEqual(self.by_id(records)["D3_Q01"]["oracle_retrieval"]["error"]["type"], "RuntimeError")
        self.assertEqual(manifest["question_count_completed"], 35)

    def test_runner_computes_no_metrics(self):
        _, _, manifest, records = self.execute(FakeSystem(self.plans))
        keys = {k.lower() for k in keys_recursive(manifest)} | {k.lower() for r in records for k in keys_recursive(r)}
        self.assertEqual(keys & METRIC_KEYS, set())

    def test_crash_mid_run_is_aborted_and_partial_run_preserved(self):
        system = FakeSystem(self.plans, crash_on=self.items[4]["question"])
        rc, run_dir, manifest, records = self.execute(system)
        self.assertEqual(rc, runner.EXIT_ABORTED)
        self.assertEqual((manifest["status"], manifest["abort_stage"]), ("ABORTED", "during_run"))
        self.assertEqual(manifest["question_count_completed"], 4)
        self.assertEqual([r["id"] for r in records], ["D3_Q01", "D3_Q02", "D3_Q03", "D3_Q04"])
        self.assertFalse((run_dir / "RUN.sha256").exists())
        self.assertEqual(system.closed, 1)

    def test_startup_failure_is_invalid_and_aborted(self):
        def factory():
            raise RuntimeError("Ollama is not reachable")

        with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            rc = runner.execute(self.cfg, self.validation, system_factory=factory, clock=Clock())
        run_dir = next(self.cfg.runs_dir.iterdir())
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, runner.EXIT_ABORTED)
        self.assertEqual((manifest["status"], manifest["abort_stage"]), ("ABORTED", "startup"))
        self.assertFalse(manifest["valid_experimental_run"])
        self.assertEqual((run_dir / "raw_results.jsonl").read_text(), "")

    def test_existing_run_directory_is_never_overwritten(self):
        self.execute(FakeSystem(self.plans))
        with self.assertRaises(FileExistsError), mock.patch("sys.stdout"):
            runner.execute(self.cfg, self.validation, system_factory=lambda: FakeSystem(self.plans), clock=Clock())


if __name__ == "__main__":
    unittest.main()

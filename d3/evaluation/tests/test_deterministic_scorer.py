"""D3 deterministic scorer, fully offline: synthetic dataset, protocol and raw run fixtures only.

No planner, retriever, MCP, model or network is used, and no D3_Q01-D3_Q35 question is sent to any
system. Only synthetic "Pergunta de teste ..." items are scored here.
"""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

EVAL_DIR = Path(__file__).resolve().parents[1]
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import run_d3_evaluation as frozen  # noqa: E402
import score_d3_evaluation as scorer  # noqa: E402

TOOLS = {"weather": ("get_current_weather", "get_weather_forecast"),
         "places": ("search_place", "get_distance_between_places")}
JUDGE_KEYS = {"correctness", "faithfulness", "groundedness", "relevance", "judge", "judge_score", "judge_scores"}
RUN_ID = "20261006T170000+0100"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_items():
    items, n = [], 0
    for category in frozen.CATEGORIES:
        parts = {p.lower() for p in category.split("+")}
        for k in range(5):
            n += 1
            qid = f"D3_Q{n:02d}"
            caps = {c: c in parts for c in ("rag", "weather", "places")}
            gold = [f"doc-{qid}::c0001"] + ([f"doc-{qid}::c0002"] if k == 0 else [])
            items.append({
                "id": qid, "category": category, "question": f"Pergunta de teste {qid}",
                "gold_capabilities": caps,
                "rag": {"required": caps["rag"], "information_need": f"necessidade {qid}" if caps["rag"] else None,
                        "gold_chunks": gold if caps["rag"] else []},
                "weather": {"required": caps["weather"],
                            "expected_tool": TOOLS["weather"][k % 2] if caps["weather"] else None},
                "places": {"required": caps["places"],
                           "expected_tool": TOOLS["places"][k % 2] if caps["places"] else None},
            })
    return items


def perfect_record(item):
    caps = item["gold_capabilities"]
    calls = [{"server": s, "tool": item[s]["expected_tool"], "arguments": {"x": item["id"]}}
             for s in ("weather", "places") if caps[s]]
    oracle_top3 = None
    if caps["rag"]:
        chunks = list(item["rag"]["gold_chunks"]) + ["other::c0009", "other::c0008"]
        oracle_top3 = [{"rank": r, "chunk_id": c, "cosine_distance": 0.1 * r} for r, c in enumerate(chunks[:3], start=1)]

    def block(server):
        if not caps[server]:
            return {"planned": False, "tool": None, "arguments": None, "executed": False,
                    "success": None, "raw_output": None, "error": None}
        return {"planned": True, "tool": item[server]["expected_tool"], "arguments": {"x": item["id"]},
                "executed": True, "success": True, "raw_output": {"ok": True}, "error": None}

    return {
        "id": item["id"], "category": item["category"], "question": item["question"],
        "timing": {"started_at": "t0", "finished_at": "t1", "duration_seconds": 1.0},
        "gold_snapshot": {"capabilities": dict(caps), "expected_weather_tool": item["weather"]["expected_tool"],
                          "expected_places_tool": item["places"]["expected_tool"]},
        "planner": {"success": True, "use_rag": caps["rag"], "rag_query": None, "tool_calls": calls, "error": None},
        "actual_retrieval": {"performed": False, "query": None, "capture_method": None, "top3": None, "error": None},
        "oracle_retrieval": {"required_by_gold": caps["rag"], "query": item["rag"]["information_need"],
                             "top3": oracle_top3, "error": None},
        "weather": block("weather"), "places": block("places"),
        "generation_evidence": {"capture_method": None, "rag_context": None, "weather_data": None,
                                "places_data": None, "generator_user_message": None},
        "final_answer": "Resposta sintética.", "error": None,
    }


class Fixture:
    """Synthetic frozen inputs + one synthetic COMPLETED run in a temporary directory."""

    def __init__(self, root: Path):
        self.root = root
        self.items = make_items()
        self.records = [perfect_record(i) for i in self.items]
        self.manifest_overrides = {}
        self.write_frozen()

    def write_frozen(self, items=None):
        r = self.root
        (r / frozen.DATASET_JSON).write_text(json.dumps({"items": items or self.items}), encoding="utf-8")
        (r / frozen.DATASET_MD).write_text("md\n", encoding="utf-8")
        (r / frozen.DATASET_AUDIT).write_text("audit\n", encoding="utf-8")
        (r / frozen.PROTOCOL).write_text("protocolo\n", encoding="utf-8")
        names = (frozen.DATASET_MD, frozen.DATASET_JSON, frozen.DATASET_AUDIT)
        (r / frozen.DATASET_SHA).write_text("".join(f"{sha(r / n)}  {n}\n" for n in names), encoding="utf-8")
        (r / frozen.PROTOCOL_SHA).write_text(f"{sha(r / frozen.PROTOCOL)}  {frozen.PROTOCOL}\n", encoding="utf-8")

    @property
    def cfg(self):
        return frozen.RunnerConfig(eval_dir=self.root, runs_dir=self.root / "runs",
                                   pinned_dataset=None, pinned_protocol=None)

    def write_run(self, raw_lines=None):
        run_dir = self.root / "runs" / RUN_ID
        run_dir.mkdir(parents=True, exist_ok=True)
        lines = raw_lines if raw_lines is not None else [json.dumps(r, ensure_ascii=False) for r in self.records]
        (run_dir / "raw_results.jsonl").write_text("".join(line + "\n" for line in lines), encoding="utf-8")
        names = (frozen.DATASET_MD, frozen.DATASET_JSON, frozen.DATASET_AUDIT)
        manifest = {"run_id": RUN_ID, "status": "COMPLETED", "valid_experimental_run": True,
                    "started_at": "2026-10-06T17:00:00+01:00", "finished_at": "2026-10-06T17:05:00+01:00",
                    "git": {"commit": "abc", "dirty": False}, "system": {"run_date": "2026-10-06"},
                    "dataset": {"sha256": {n: sha(self.root / n) for n in names}},
                    "protocol": {"sha256": sha(self.root / frozen.PROTOCOL)},
                    "question_count_expected": 35, "question_count_completed": 35}
        manifest.update(self.manifest_overrides)
        (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (run_dir / "RUN.sha256").write_text(
            f"{sha(run_dir / 'raw_results.jsonl')}  raw_results.jsonl\n"
            f"{sha(run_dir / 'run_manifest.json')}  run_manifest.json\n", encoding="utf-8")
        return run_dir

    def score(self):
        return scorer.score(scorer.validate_run(self.write_run(), self.cfg), "runs/fixture")

    def record(self, qid):
        return next(r for r in self.records if r["id"] == qid)


def per_q(scores, qid):
    return next(q for q in scores["per_question"] if q["id"] == qid)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()


# ---------------------------------------------------------------------------
# Exact Capability Match
# ---------------------------------------------------------------------------


class EcmTests(Base):
    def test_exact_match(self):
        s = self.fx.score()
        self.assertEqual(s["official_metrics"]["exact_capability_match"]["correct"], 35)
        self.assertEqual(s["official_metrics"]["exact_capability_match"]["total"], 35)
        self.assertEqual(per_q(s, "D3_Q16")["agency"]["exact_capability_match"], 1)

    def test_missing_capability(self):
        self.fx.record("D3_Q16")["planner"]["tool_calls"] = []  # RAG+WEATHER planned as RAG only
        s = self.fx.score()
        self.assertEqual(per_q(s, "D3_Q16")["agency"]["exact_capability_match"], 0)
        self.assertEqual(s["official_metrics"]["exact_capability_match"]["correct"], 34)
        self.assertEqual(s["error_analysis"]["agency_errors"][0]["observations"],
                         ["Weather capability absent although gold=true"])

    def test_extra_capability(self):
        self.fx.record("D3_Q06")["planner"]["use_rag"] = True  # WEATHER planned as RAG+WEATHER
        s = self.fx.score()
        self.assertEqual(per_q(s, "D3_Q06")["agency"]["exact_capability_match"], 0)
        self.assertEqual(s["error_analysis"]["agency_errors"][0]["observations"],
                         ["RAG capability added although gold=false"])

    def test_planner_failure_predicts_all_false(self):
        self.fx.record("D3_Q31")["planner"] = {"success": False, "use_rag": None, "rag_query": None,
                                               "tool_calls": None, "error": {"type": "PlannerError", "message": "x"}}
        q = per_q(self.fx.score(), "D3_Q31")
        self.assertEqual(q["agency"]["predicted_capabilities"], {"rag": False, "weather": False, "places": False})
        self.assertEqual(q["agency"]["exact_capability_match"], 0)
        self.assertEqual((q["tool_accuracy"]["weather"]["correct"], q["tool_accuracy"]["places"]["correct"]), (0, 0))

    def test_category_breakdown(self):
        self.fx.record("D3_Q01")["planner"].update(use_rag=False, tool_calls=[{"server": "places", "tool": "search_place"}])
        b = self.fx.score()["category_breakdown"]["exact_capability_match"]
        self.assertEqual((b["RAG"]["correct"], b["RAG"]["total"]), (4, 5))
        self.assertEqual(b["PLACES"]["correct"], 5)


# ---------------------------------------------------------------------------
# Tool Accuracy
# ---------------------------------------------------------------------------


class ToolAccuracyTests(Base):
    def test_weather_correct(self):
        q = per_q(self.fx.score(), "D3_Q07")
        self.assertEqual(q["tool_accuracy"]["weather"],
                         {"expected_tool": "get_weather_forecast", "selected_tool": "get_weather_forecast", "correct": 1})

    def test_weather_missing_is_incorrect(self):
        self.fx.record("D3_Q06")["planner"].update(use_rag=True, tool_calls=[])
        s = self.fx.score()
        self.assertIsNone(per_q(s, "D3_Q06")["tool_accuracy"]["weather"]["selected_tool"])
        self.assertEqual(s["official_metrics"]["tool_accuracy"]["breakdown"]["weather"]["correct"], 19)
        self.assertEqual(s["error_analysis"]["tool_selection_errors"][0]["observation"], "no weather call in the plan")

    def test_wrong_weather_tool_is_incorrect_but_ecm_unchanged(self):
        self.fx.record("D3_Q06")["planner"]["tool_calls"][0]["tool"] = "get_weather_forecast"
        s = self.fx.score()
        self.assertEqual(per_q(s, "D3_Q06")["tool_accuracy"]["weather"]["correct"], 0)
        self.assertEqual(s["official_metrics"]["tool_accuracy"]["correct"], 39)
        self.assertEqual(s["official_metrics"]["exact_capability_match"]["correct"], 35)

    def test_places_correct(self):
        self.assertEqual(per_q(self.fx.score(), "D3_Q12")["tool_accuracy"]["places"]["correct"], 1)

    def test_places_missing_is_incorrect(self):
        self.fx.record("D3_Q12")["planner"]["tool_calls"] = [{"server": "weather", "tool": "get_current_weather"}]
        s = self.fx.score()
        self.assertEqual(per_q(s, "D3_Q12")["tool_accuracy"]["places"]["correct"], 0)
        self.assertEqual(s["official_metrics"]["tool_accuracy"]["breakdown"]["places"]["correct"], 19)

    def test_extra_non_gold_tool_does_not_change_ta(self):
        self.fx.record("D3_Q01")["planner"]["tool_calls"] = [{"server": "weather", "tool": "get_current_weather"}]
        s = self.fx.score()
        ta = s["official_metrics"]["tool_accuracy"]
        self.assertEqual((ta["correct"], ta["total"]), (40, 40))
        self.assertIsNone(per_q(s, "D3_Q01")["tool_accuracy"]["weather"])
        self.assertEqual(s["official_metrics"]["exact_capability_match"]["correct"], 34)  # penalised by ECM only

    def test_tool_execution_failure_does_not_change_ta(self):
        rec = self.fx.record("D3_Q26")
        rec["weather"].update(success=False, raw_output=None, error={"type": "WeatherMCPError", "message": "x"})
        rec["error"] = {"stage": "weather", "type": "ExpertAgentError", "message": "x"}
        rec["final_answer"] = None
        s = self.fx.score()
        self.assertEqual(s["official_metrics"]["tool_accuracy"]["correct"], 40)
        d = s["descriptive_run_summary"]
        self.assertEqual((d["no_final_answer"], d["errors_by_stage"]), (1, {"weather": 1}))
        self.assertEqual(d["tool_execution"]["weather"]["failed_ids"], ["D3_Q26"])

    def test_breakdown_totals(self):
        ta = self.fx.score()["official_metrics"]["tool_accuracy"]
        self.assertEqual((ta["breakdown"]["weather"]["total"], ta["breakdown"]["places"]["total"]), (20, 20))


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def oracle(*chunk_ids, error=None):
    return {"required_by_gold": True, "query": "q", "error": error,
            "top3": None if error else [{"rank": r, "chunk_id": c, "cosine_distance": 0.2}
                                        for r, c in enumerate(chunk_ids, start=1)]}


class RetrievalTests(unittest.TestCase):
    def test_hit_and_mrr_rank1(self):
        r = scorer.retrieval_scores(["g"], oracle("g", "a", "b"))
        self.assertEqual((r["hit_at_3"], r["reciprocal_rank"], r["first_gold_rank"]), (1, 1.0, 1))

    def test_mrr_rank2(self):
        self.assertEqual(scorer.retrieval_scores(["g"], oracle("a", "g", "b"))["reciprocal_rank"], 0.5)

    def test_hit_and_mrr_rank3(self):
        r = scorer.retrieval_scores(["g"], oracle("a", "b", "g"))
        self.assertEqual(r["hit_at_3"], 1)
        self.assertEqual(r["reciprocal_rank"], 1 / 3)

    def test_miss(self):
        r = scorer.retrieval_scores(["g"], oracle("a", "b", "c"))
        self.assertEqual((r["hit_at_3"], r["recall_at_3"], r["reciprocal_rank"], r["first_gold_rank"]),
                         (0, 0.0, 0.0, None))

    def test_recall_with_multiple_gold_chunks(self):
        r = scorer.retrieval_scores(["g1", "g2", "g3"], oracle("g2", "a", "g3"))
        self.assertEqual(r["recall_at_3"], 2 / 3)
        self.assertEqual(r["reciprocal_rank"], 1.0)

    def test_duplicate_retrieved_chunk_counts_once(self):
        self.assertEqual(scorer.retrieval_scores(["g1", "g2"], oracle("g1", "g1", "a"))["recall_at_3"], 0.5)

    def test_oracle_error_scores_zero(self):
        r = scorer.retrieval_scores(["g"], oracle(error={"type": "X", "message": "y"}))
        self.assertEqual((r["hit_at_3"], r["recall_at_3"], r["reciprocal_rank"], r["oracle_failed"]),
                         (0, 0.0, 0.0, True))

    def test_missing_top3_scores_zero(self):
        r = scorer.retrieval_scores(["g"], {"required_by_gold": True, "query": "q", "top3": None, "error": None})
        self.assertEqual((r["hit_at_3"], r["oracle_failed"]), (0, True))

    def test_rank_field_defines_order(self):
        o = oracle("a", "g")
        o["top3"].reverse()
        self.assertEqual(scorer.retrieval_scores(["g"], o)["first_gold_rank"], 2)


class RetrievalAggregationTests(Base):
    def test_macro_recall_and_mrr_over_20(self):
        self.fx.record("D3_Q01")["oracle_retrieval"]["top3"] = [  # 2 gold chunks, one retrieved at rank 2
            {"rank": 1, "chunk_id": "x::1", "cosine_distance": 0.1},
            {"rank": 2, "chunk_id": "doc-D3_Q01::c0001", "cosine_distance": 0.2}]
        self.fx.record("D3_Q02")["oracle_retrieval"].update(top3=None, error={"type": "E", "message": "m"})
        s = self.fx.score()
        rt = s["official_metrics"]["retrieval"]
        self.assertEqual(rt["questions"], 20)
        self.assertEqual((rt["hit_at_3"]["hits"], rt["hit_at_3"]["total"]), (19, 20))
        self.assertAlmostEqual(rt["macro_recall_at_3"]["value"], (18 + 0.5 + 0) / 20)
        self.assertAlmostEqual(rt["mrr"]["value"], (18 + 0.5 + 0) / 20)
        self.assertEqual([r["id"] for r in s["error_analysis"]["retrieval_imperfect"]], ["D3_Q01", "D3_Q02"])

    def test_actual_retrieval_is_not_used(self):
        self.fx.record("D3_Q03")["actual_retrieval"] = {
            "performed": True, "query": "x", "capture_method": "c", "error": None,
            "top3": [{"rank": 1, "chunk_id": "z", "cosine_distance": 0.0}]}
        self.assertEqual(self.fx.score()["official_metrics"]["retrieval"]["hit_at_3"]["hits"], 20)

    def test_non_rag_questions_excluded(self):
        self.assertEqual(per_q(self.fx.score(), "D3_Q06")["retrieval"], {"included": False})


# ---------------------------------------------------------------------------
# Validation aborts
# ---------------------------------------------------------------------------


class ValidationTests(Base):
    def assert_abort(self, fragment, run_dir=None):
        with self.assertRaises(scorer.ScoringError) as ctx:
            scorer.validate_run(run_dir or self.fx.write_run(), self.fx.cfg)
        self.assertIn(fragment, str(ctx.exception))

    def patched_items(self, items):
        """Bypass the frozen-dataset validation to reach the scorer's own count checks."""

        self.fx.manifest_overrides = {"dataset": {"sha256": {}}, "protocol": {"sha256": "p"}}
        for rec, item in zip(self.fx.records, items):
            rec["gold_snapshot"]["capabilities"] = item["gold_capabilities"]
            rec["oracle_retrieval"]["required_by_gold"] = item["gold_capabilities"]["rag"]
        return mock.patch.object(frozen, "validate",
                                 return_value={"items": items, "dataset_hashes": {}, "protocol_sha256": "p"})

    def test_valid_run_passes(self):
        self.assertEqual(len(scorer.validate_run(self.fx.write_run(), self.fx.cfg)["records"]), 35)

    def test_exactly_20_rag_questions_required(self):
        items = make_items()
        items[0]["gold_capabilities"]["rag"] = False
        with self.patched_items(items):
            self.assert_abort("expected 20 RAG questions")

    def test_exactly_40_mcp_needs_required(self):
        items = make_items()
        items[5]["gold_capabilities"]["weather"] = False
        with self.patched_items(items):
            self.assert_abort("expected 40 MCP tool needs")

    def test_exactly_35_dataset_items_required(self):
        self.fx.write_frozen(items=make_items()[:34])
        self.assert_abort("expected 35")

    def test_raw_id_mismatch_aborts(self):
        self.fx.records[3]["id"] = "D3_Q99"
        self.assert_abort("missing questions")

    def test_raw_order_mismatch_aborts(self):
        self.fx.records[3], self.fx.records[4] = self.fx.records[4], self.fx.records[3]
        self.assert_abort("in order")

    def test_raw_question_mismatch_aborts(self):
        self.fx.records[3]["question"] = "outra pergunta"
        self.assert_abort("raw question differs")

    def test_raw_category_mismatch_aborts(self):
        self.fx.records[3]["category"] = "PLACES"
        self.assert_abort("raw category differs")

    def test_gold_snapshot_mismatch_aborts(self):
        self.fx.records[6]["gold_snapshot"]["expected_weather_tool"] = "get_current_weather"  # gold: forecast
        self.assert_abort("gold_snapshot")

    def test_duplicate_raw_id_aborts(self):
        self.fx.records[4] = copy.deepcopy(self.fx.records[3])
        self.assert_abort("duplicated raw IDs")

    def test_missing_question_aborts(self):
        lines = [json.dumps(r) for r in self.fx.records[:34]]
        self.assert_abort("exactly 35 lines", self.fx.write_run(raw_lines=lines))

    def test_invalid_json_line_aborts(self):
        lines = [json.dumps(r) for r in self.fx.records]
        lines[10] = "{not json"
        self.assert_abort("not valid JSON", self.fx.write_run(raw_lines=lines))

    def test_run_sha_mismatch_aborts(self):
        run_dir = self.fx.write_run()
        with (run_dir / "raw_results.jsonl").open("a", encoding="utf-8") as stream:
            stream.write("\n")
        self.assert_abort("does not match RUN.sha256", run_dir)

    def test_dataset_hash_mismatch_aborts(self):
        run_dir = self.fx.write_run()
        (self.fx.root / frozen.DATASET_AUDIT).write_text("alterado", encoding="utf-8")
        self.assert_abort("hash mismatch", run_dir)

    def test_protocol_hash_mismatch_aborts(self):
        run_dir = self.fx.write_run()
        (self.fx.root / frozen.PROTOCOL).write_text("alterado", encoding="utf-8")
        self.assert_abort(frozen.PROTOCOL, run_dir)

    def test_manifest_hash_differs_from_current_files_aborts(self):
        self.fx.manifest_overrides = {"protocol": {"sha256": "0" * 64}}
        self.assert_abort("protocol SHA-256 recorded in the manifest")

    def test_aborted_run_cannot_be_scored(self):
        self.fx.manifest_overrides = {"status": "ABORTED"}
        self.assert_abort("not COMPLETED")

    def test_invalid_run_cannot_be_scored(self):
        self.fx.manifest_overrides = {"valid_experimental_run": False}
        self.assert_abort("valid_experimental_run")

    def test_incomplete_count_cannot_be_scored(self):
        self.fx.manifest_overrides = {"question_count_completed": 34}
        self.assert_abort("question_count_completed")

    def test_malformed_planner_aborts(self):
        self.fx.records[0]["planner"]["success"] = None
        self.assert_abort("planner.success")


# ---------------------------------------------------------------------------
# Outputs, determinism and isolation
# ---------------------------------------------------------------------------


def keys_recursive(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from keys_recursive(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from keys_recursive(inner)


class OutputTests(Base):
    def run_main(self, *argv):
        with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            return scorer.main(list(argv), cfg=self.fx.cfg)

    def test_scoring_writes_derived_files_and_never_modifies_raw(self):
        run_dir = self.fx.write_run()
        before = {n: sha(run_dir / n) for n in ("raw_results.jsonl", "run_manifest.json", "RUN.sha256")}
        self.assertEqual(self.run_main("--run-dir", str(run_dir)), 0)
        self.assertEqual({n: sha(run_dir / n) for n in before}, before)
        lines = (run_dir / scorer.SCORES_SHA).read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines, [f"{sha(run_dir / scorer.SCORES_JSON)}  {scorer.SCORES_JSON}",
                                 f"{sha(run_dir / scorer.REPORT_MD)}  {scorer.REPORT_MD}"])

    def test_validate_only_writes_nothing(self):
        run_dir = self.fx.write_run()
        self.assertEqual(self.run_main("--run-dir", str(run_dir), "--validate-only"), 0)
        self.assertFalse(any((run_dir / n).exists() for n in scorer.DERIVED))

    def test_run_dir_is_required(self):
        run_dir = self.fx.write_run()
        self.assertEqual(self.run_main(), 2)
        self.assertFalse(any((run_dir / n).exists() for n in scorer.DERIVED))

    def test_existing_derived_files_are_not_overwritten_by_default(self):
        run_dir = self.fx.write_run()
        self.assertEqual(self.run_main("--run-dir", str(run_dir)), 0)
        first = sha(run_dir / scorer.SCORES_JSON)
        self.assertEqual(self.run_main("--run-dir", str(run_dir)), 2)
        self.assertEqual(sha(run_dir / scorer.SCORES_JSON), first)

    def test_repeated_scoring_is_byte_stable(self):
        run_dir = self.fx.write_run()
        self.run_main("--run-dir", str(run_dir))
        first = {n: sha(run_dir / n) for n in scorer.DERIVED}
        self.assertEqual(self.run_main("--run-dir", str(run_dir), "--overwrite-derived"), 0)
        self.assertEqual({n: sha(run_dir / n) for n in scorer.DERIVED}, first)

    def test_no_judge_fields_and_only_frozen_metrics(self):
        s = self.fx.score()
        self.assertEqual({k.lower() for k in keys_recursive(s)} & JUDGE_KEYS, set())
        self.assertEqual(set(s["official_metrics"]), {"exact_capability_match", "tool_accuracy", "retrieval"})
        self.assertEqual(set(s["official_metrics"]["retrieval"]) - {"questions", "query_source"},
                         {"hit_at_3", "macro_recall_at_3", "mrr"})

    def test_report_structure(self):
        report = scorer.render_report(self.fx.score())
        self.assertIn("NOT AN OFFICIAL METRIC", report)
        for n in range(1, 12):
            self.assertIn(f"\n## {n}. ", report)

    def test_scorer_imports_no_model_mcp_or_network_module(self):
        heavy = ["rag_pipeline", "expert_agent", "agents", "planner", "evaluation_trace", "chromadb", "torch",
                 "langchain_core", "langchain_ollama", "langchain_huggingface", "langchain_chroma", "mcp", "ollama",
                 "httpx", "requests", "urllib.request", "http.client", "sentence_transformers"]
        run_dir = self.fx.write_run()
        code = ("import sys, pathlib; sys.path.insert(0, r'%s'); import score_d3_evaluation as s, run_d3_evaluation as f; "
                "cfg = f.RunnerConfig(eval_dir=pathlib.Path(r'%s'), runs_dir=pathlib.Path(r'%s'), pinned_dataset=None, "
                "pinned_protocol=None); rc = s.main(['--run-dir', r'%s'], cfg=cfg); "
                "print('RC', rc); print('HEAVY', [m for m in %r if m in sys.modules])"
                % (EVAL_DIR, self.fx.root, self.fx.root / "runs", run_dir, heavy))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8",
                             timeout=120)
        self.assertIn("RC 0", out.stdout, out.stderr)
        self.assertIn("HEAVY []", out.stdout)


if __name__ == "__main__":
    unittest.main()

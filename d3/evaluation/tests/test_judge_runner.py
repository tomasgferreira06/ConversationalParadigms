"""D3 LLM-as-Judge runner, fully offline.

A FakeJudgeClient stands in for any judge model; datasets, runs, deterministic scores and judge configs
are synthetic fixtures ("Pergunta de teste ..."). No LLM, network, MCP, retrieval or model is used.
"""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

EVAL_DIR = Path(__file__).resolve().parents[1]
for _p in (EVAL_DIR, EVAL_DIR / "tests"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import run_d3_evaluation as frozen  # noqa: E402
import run_d3_judge as judge  # noqa: E402
import score_d3_evaluation as det  # noqa: E402
from test_deterministic_scorer import Fixture as ScorerFixture  # noqa: E402

REAL_CONFIG = json.loads((EVAL_DIR / judge.CONFIG_JSON).read_text(encoding="utf-8"))
NO_ANSWER_IDS = ("D3_Q07", "D3_Q22")
FORBIDDEN_PAYLOAD_KEYS = {"oracle_retrieval", "exact_capability_match", "tool_accuracy", "hit_at_3", "recall_at_3",
                          "mrr", "reciprocal_rank", "planner", "actual_retrieval", "category", "gold_snapshot",
                          "expected_tool", "cosine_distance", "official_metrics", "information_need"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keys_recursive(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from keys_recursive(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from keys_recursive(inner)


def valid_output(c=2, f=2, r=2):
    return json.dumps({"correctness": {"score": c, "reason": "Matches F1 in the gold."},
                       "faithfulness": {"score": f, "reason": "Supported by the RAG context."},
                       "relevance": {"score": r, "reason": "Answers the question directly."}})


class FakeJudgeClient:
    """Scripted judge: each call pops the next response (str content or an exception)."""

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def judge(self, system_prompt, user_message, output_schema, temperature):
        self.calls.append({"system": system_prompt, "user": user_message, "schema": output_schema,
                           "temperature": temperature})
        response = self.responses.pop(0) if self.responses else valid_output()
        if isinstance(response, BaseException):
            raise response
        return judge.JudgeResponse(response, {"eval_count": 42})

    def describe(self):
        return {"provider": "fake", "model": "fake-judge-model"}


class Clock:
    def __init__(self):
        self.t = datetime(2026, 10, 7, 10, 0, 0, tzinfo=timezone(timedelta(hours=1)))

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


class JudgeFixture(ScorerFixture):
    """Synthetic frozen dataset + COMPLETED run + deterministic scoring + judge configuration."""

    def __init__(self, root: Path, status="FROZEN"):
        super().__init__(root)
        for item, record in zip(self.items, self.records):
            caps = item["gold_capabilities"]
            if caps["rag"]:
                item["rag"]["essential_facts"] = [{"id": "F1", "fact": f"Facto gold {item['id']}",
                                                   "evidence_type": "direct", "requires_inference": False}]
                item["rag"]["evidence"] = [{"document": "doc", "section": "s", "chunk_id": "c", "supports": ["F1"],
                                            "text_excerpt": f"Excerto gold {item['id']}"}]
            item["answer_requirements"] = {"stable_facts": [f"Facto gold {item['id']}"] if caps["rag"] else [],
                                           "weather_requirements": ["report weather"] if caps["weather"] else [],
                                           "places_requirements": ["report place"] if caps["places"] else []}
            item["weather"]["location_requirement"] = "Coimbra, Portugal" if caps["weather"] else None
            item["weather"]["temporal_requirement"] = "current" if caps["weather"] else None
            item["places"]["query_requirement"] = {"canonical_name": "Local"} if caps["places"] else None
            record["generation_evidence"] = {
                "capture_method": "observed_agent_call",
                "rag_context": f"CONTEXTO REAL {item['id']}" if caps["rag"] else None,
                "weather_data": '{"temperature_c": 18.5}' if caps["weather"] else None,
                "places_data": '{"display_name": "Local real"}' if caps["places"] else None,
                "generator_user_message": "..."}
            for server in ("weather", "places"):
                if caps[server]:
                    record[server]["raw_output"] = {"raw": f"OUTPUT REAL {server} {item['id']}"}
            if (record["oracle_retrieval"] or {}).get("top3"):
                record["oracle_retrieval"]["top3"][0]["text"] = f"TEXTO ORACLE {item['id']}"
            record["final_answer"] = f"Resposta final {item['id']}"
            if item["id"] in NO_ANSWER_IDS:
                record["final_answer"] = None
                record["error"] = {"stage": "places", "type": "ExpertAgentError", "message": "x"}
        self.write_frozen()
        self.status = status
        self.rebuild_run()

    def rebuild_run(self, raw_lines=None):
        self.run_dir = self.write_run(raw_lines=raw_lines)
        for name in det.DERIVED:
            if (self.run_dir / name).exists():
                (self.run_dir / name).unlink()
        try:
            det.validate_run(self.run_dir, self.cfg)
        except det.ScoringError:
            pass  # invalid source runs are tested as such; no deterministic scoring for them
        else:
            with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
                assert det.main(["--run-dir", str(self.run_dir)], cfg=self.cfg) == 0
        self.write_config()

    def write_config(self, mutate=None):
        config = copy.deepcopy(REAL_CONFIG)
        config["status"] = self.status  # FROZEN fixtures keep the official judge settings of the real config

        def digest(name):
            return sha(self.run_dir / name) if (self.run_dir / name).exists() else None

        config["source_run"] = {"run_id": self.run_dir.name,
                                "raw_results_sha256": digest(det.RAW), "run_manifest_sha256": digest(det.MANIFEST),
                                "deterministic_scores_sha256": digest(det.SCORES_JSON),
                                "deterministic_report_sha256": digest(det.REPORT_MD)}
        if mutate:
            mutate(config)
        (self.root / judge.CONFIG_JSON).write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        (self.root / judge.CONFIG_MD).write_text(f"# Judge config fixture\n\nStatus: {self.status}\n", encoding="utf-8")
        sha_path = self.root / judge.CONFIG_SHA
        if sha_path.exists():
            sha_path.unlink()
        if self.status == "FROZEN":
            sha_path.write_text(f"{sha(self.root / judge.CONFIG_MD)}  {judge.CONFIG_MD}\n"
                                f"{sha(self.root / judge.CONFIG_JSON)}  {judge.CONFIG_JSON}\n", encoding="utf-8")
        return config

    def item(self, qid):
        return next(i for i in self.items if i["id"] == qid)


class Base(unittest.TestCase):
    status = "FROZEN"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = JudgeFixture(Path(self.tmp.name), status=self.status)

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *argv, client=None):
        self.client = client or FakeJudgeClient()
        self.factory = mock.Mock(return_value=self.client)
        with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            return judge.main(list(argv), cfg=self.fx.cfg, client_factory=self.factory, clock=Clock())

    def judge_dir(self):
        root = self.fx.run_dir / "judge"
        dirs = sorted(root.iterdir()) if root.exists() else []
        self.assertEqual(len(dirs), 1)
        return dirs[0]

    def results(self):
        return [json.loads(line) for line in (self.judge_dir() / judge.RESULTS).read_text(encoding="utf-8").splitlines()]

    def judge_manifest(self):
        return json.loads((self.judge_dir() / judge.JUDGE_MANIFEST).read_text(encoding="utf-8"))

    def validate(self):
        return judge.validate_inputs(self.fx.cfg, judge.load_judge_config(self.fx.cfg))

    def assert_execute_rejected(self):
        self.assertEqual(self.run_main("--execute", "--confirm-judge-v1"), judge.EXIT_INVALID)
        self.factory.assert_not_called()
        self.assertFalse((self.fx.run_dir / "judge").exists())


# ---------------------------------------------------------------------------
# Safety gates and input validation
# ---------------------------------------------------------------------------


class PreparedConfigTests(Base):
    status = "PREPARED"

    def test_validate_only_passes_and_never_calls_the_judge(self):
        self.assertEqual(self.run_main("--validate-only"), judge.EXIT_OK)
        self.factory.assert_not_called()
        self.assertEqual(self.client.calls, [])
        self.assertFalse((self.fx.run_dir / "judge").exists())

    def test_default_is_validate_only(self):
        self.assertEqual(self.run_main(), judge.EXIT_OK)
        self.factory.assert_not_called()
        self.assertFalse((self.fx.run_dir / "judge").exists())

    def test_no_locked_model_execute_aborts_before_any_client(self):
        self.assert_execute_rejected()

    def test_real_config_is_the_frozen_official_judge(self):
        loaded = judge.load_judge_config(frozen.RunnerConfig())  # reads the real config only (hash checked)
        judge_block = loaded["config"]["judge"]
        self.assertEqual(loaded["config"]["status"], "FROZEN")
        self.assertTrue(loaded["hashed"])
        self.assertEqual((judge_block["provider"], judge_block["model"], judge_block["model_family"],
                          judge_block["model_version_or_digest"], judge_block["reasoning_effort"],
                          judge_block["max_attempts"], judge_block["max_output_tokens"], judge_block["store"],
                          judge_block["api"], judge_block["tools"]),
                         ("openai", "gpt-5-mini-2025-08-07", "GPT-5 mini", "gpt-5-mini-2025-08-07", "medium", 2, 6000,
                          False, "responses", "none"))
        self.assertIsNone(judge_block["temperature"])
        self.assertEqual(judge_block["temperature_policy"], "not_sent_provider_controlled")


class GateTests(Base):
    def test_execute_without_confirmation_aborts(self):
        self.assertEqual(self.run_main("--execute"), judge.EXIT_INVALID)
        self.factory.assert_not_called()
        self.assertFalse((self.fx.run_dir / "judge").exists())

    def test_frozen_config_without_hash_cannot_execute(self):
        (self.fx.root / judge.CONFIG_SHA).unlink()
        self.assert_execute_rejected()

    def test_config_hash_mismatch_aborts(self):
        (self.fx.root / judge.CONFIG_MD).write_text("alterado", encoding="utf-8")
        self.assert_execute_rejected()

    def test_invalid_dataset_hash_aborts(self):
        (self.fx.root / frozen.DATASET_AUDIT).write_text("alterado", encoding="utf-8")
        self.assert_execute_rejected()

    def test_invalid_protocol_hash_aborts(self):
        (self.fx.root / frozen.PROTOCOL).write_text("alterado", encoding="utf-8")
        self.assert_execute_rejected()

    def test_invalid_run_sha_aborts(self):
        (self.fx.run_dir / det.RUN_SHA).write_text(f"{'0' * 64}  raw_results.jsonl\n{'0' * 64}  run_manifest.json\n",
                                                   encoding="utf-8")
        self.assert_execute_rejected()

    def test_invalid_deterministic_scoring_hash_aborts(self):
        with (self.fx.run_dir / det.REPORT_MD).open("a", encoding="utf-8") as stream:
            stream.write("x")
        self.assert_execute_rejected()

    def test_deterministic_scores_hash_differs_from_config_aborts(self):
        self.fx.write_config(mutate=lambda c: c["source_run"].update(deterministic_scores_sha256="0" * 64))
        self.assert_execute_rejected()

    def test_aborted_source_run_cannot_be_judged(self):
        self.fx.manifest_overrides = {"status": "ABORTED"}
        self.fx.rebuild_run()
        with self.assertRaises(judge.JudgeError) as ctx:
            self.validate()
        self.assertIn("not COMPLETED", str(ctx.exception))

    def test_raw_count_not_35_aborts(self):
        lines = (self.fx.run_dir / det.RAW).read_text(encoding="utf-8").splitlines()[:34]
        self.fx.rebuild_run(raw_lines=lines)
        with self.assertRaises(judge.JudgeError) as ctx:
            self.validate()
        self.assertIn("35", str(ctx.exception))

    def test_question_mismatch_aborts(self):
        self.fx.records[3]["question"] = "outra pergunta"
        self.fx.rebuild_run()
        with self.assertRaises(judge.JudgeError) as ctx:
            self.validate()
        self.assertIn("raw question differs", str(ctx.exception))

    def test_judge_model_equal_to_evaluated_model_rejected(self):
        self.fx.manifest_overrides = {"system": {"run_date": "2026-10-06", "planner": {"model": "gpt-5-mini-2025-08-07"},
                                                 "generator": {"model": "llama3.2:3b"}}}
        self.fx.rebuild_run()
        with self.assertRaises(judge.JudgeError) as ctx:
            self.validate()
        self.assertIn("must differ", str(ctx.exception))

    def test_config_with_oracle_or_metrics_input_rejected(self):
        for flag in ("include_oracle_retrieval", "include_deterministic_metrics"):
            self.fx.write_config(mutate=lambda c, f=flag: c["input_policy"].update({f: True}))
            with self.assertRaises(judge.JudgeError):
                judge.load_judge_config(self.fx.cfg)

    def test_composite_score_rejected_in_config(self):
        self.fx.write_config(mutate=lambda c: c["aggregation"].update(composite_score="mean"))
        with self.assertRaises(judge.JudgeError):
            judge.load_judge_config(self.fx.cfg)

    def test_counts_are_derived_from_the_raw_results(self):
        inputs = self.validate()
        self.assertEqual(inputs["deterministic_zero_ids"], list(NO_ANSWER_IDS))
        self.assertEqual(len(inputs["judge_ids"]), 33)


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------


class PayloadTests(Base):
    def payload(self, qid):
        item = self.fx.item(qid)
        record = next(r for r in self.fx.records if r["id"] == qid)
        return judge.build_judge_payload(item, record), item, record

    def test_oracle_retrieval_and_other_forbidden_inputs_excluded(self):
        for qid in ("D3_Q01", "D3_Q31", "D3_Q26"):
            payload, _, record = self.payload(qid)
            self.assertEqual({k.lower() for k in keys_recursive(payload)} & FORBIDDEN_PAYLOAD_KEYS, set())
            text = json.dumps(payload, ensure_ascii=False)
            self.assertNotIn("TEXTO ORACLE", text)
            if record["oracle_retrieval"]["query"]:
                self.assertNotIn(record["oracle_retrieval"]["query"], text)

    def test_deterministic_metrics_never_enter_the_message(self):
        payload, _, _ = self.payload("D3_Q31")
        message = judge.render_user_message(REAL_CONFIG, payload)
        for marker in ("exact_capability_match", "tool_accuracy", "hit_at_3", "recall_at_3", "mrr", "Hit@3",
                       "official_metrics"):
            self.assertNotIn(marker, message)

    def test_actual_evidence_included(self):
        payload, _, _ = self.payload("D3_Q31")  # RAG+WEATHER+PLACES
        ev = payload["actual_generation_evidence"]
        self.assertEqual(ev["rag_context"], "CONTEXTO REAL D3_Q31")
        self.assertEqual(ev["weather_data"], '{"temperature_c": 18.5}')
        self.assertEqual(ev["places_data"], '{"display_name": "Local real"}')
        self.assertEqual(ev["raw_tool_outputs"]["weather"], {"raw": "OUTPUT REAL weather D3_Q31"})
        self.assertEqual(ev["raw_tool_outputs"]["places"], {"raw": "OUTPUT REAL places D3_Q31"})

    def test_gold_facts_evidence_and_requirements_included(self):
        payload, item, _ = self.payload("D3_Q16")
        self.assertEqual(payload["gold"]["essential_facts"], [{"id": "F1", "fact": "Facto gold D3_Q16"}])
        self.assertEqual(payload["gold"]["evidence_excerpts"],
                         [{"supports": ["F1"], "text_excerpt": "Excerto gold D3_Q16"}])
        self.assertEqual(payload["gold"]["answer_requirements"], item["answer_requirements"])
        self.assertEqual(payload["gold"]["weather_requirement"], {"location": "Coimbra, Portugal", "temporal": "current"})

    def test_question_and_final_answer_included(self):
        payload, item, _ = self.payload("D3_Q05")
        message = judge.render_user_message(REAL_CONFIG, payload)
        self.assertIn(item["question"], message)
        self.assertIn("Resposta final D3_Q05", message)
        for section in ("[A] QUESTION", "[B] GOLD ANSWER REQUIREMENTS", "[C] ACTUAL GENERATION EVIDENCE",
                        "[D] FINAL ANSWER"):
            self.assertIn(section, message)

    def test_non_rag_item_has_no_gold_facts(self):
        payload, _, _ = self.payload("D3_Q06")
        self.assertNotIn("essential_facts", payload["gold"])


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------


class ParseTests(unittest.TestCase):
    def bad(self, mutate):
        data = json.loads(valid_output())
        mutate(data)
        with self.assertRaises(judge.JudgeOutputError):
            judge.parse_judge_output(json.dumps(data), 800)

    def test_valid_scores_only_0_1_2(self):
        for s in (0, 1, 2):
            self.assertEqual(judge.parse_judge_output(valid_output(s, s, s), 800)["relevance"]["score"], s)

    def test_score_3_rejected(self):
        self.bad(lambda d: d["correctness"].update(score=3))

    def test_float_score_rejected(self):
        self.bad(lambda d: d["faithfulness"].update(score=1.0))

    def test_bool_and_null_scores_rejected(self):
        self.bad(lambda d: d["relevance"].update(score=True))
        self.bad(lambda d: d["relevance"].update(score=None))

    def test_missing_dimension_rejected(self):
        self.bad(lambda d: d.pop("relevance"))

    def test_missing_or_empty_reason_rejected(self):
        self.bad(lambda d: d["correctness"].pop("reason"))
        self.bad(lambda d: d["correctness"].update(reason="  "))

    def test_overall_score_rejected(self):
        self.bad(lambda d: d.update(overall_score=2))

    def test_unparseable_rejected(self):
        with self.assertRaises(judge.JudgeOutputError):
            judge.parse_judge_output("not json", 800)


# ---------------------------------------------------------------------------
# Execution with a fake judge
# ---------------------------------------------------------------------------


class ExecutionTests(Base):
    def test_completed_run_35_lines_with_deterministic_zeros(self):
        self.assertEqual(self.run_main("--execute", "--confirm-judge-v1"), judge.EXIT_OK)
        results = self.results()
        self.assertEqual([r["id"] for r in results], [i["id"] for i in self.fx.items])
        zeros = [r for r in results if r["evaluation_method"] == judge.DETERMINISTIC_ZERO]
        self.assertEqual([r["id"] for r in zeros], list(NO_ANSWER_IDS))
        for r in zeros:
            self.assertEqual({d: r["scores"][d]["score"] for d in judge.DIMENSIONS},
                             {"correctness": 0, "faithfulness": 0, "relevance": 0})
            self.assertEqual((r["judge_called"], r["attempts"], r["raw_judge_output"]), (False, 0, None))
            self.assertIn("protocol Section 10", r["scores"]["correctness"]["reason"])
        manifest = self.judge_manifest()
        self.assertEqual(manifest["status"], "COMPLETED")
        self.assertEqual((manifest["deterministic_zero_count"], manifest["llm_judge_expected_count"],
                          manifest["llm_judge_completed_count"]), (2, 33, 33))

    def test_one_call_per_usable_answer_and_none_for_no_answer(self):
        self.run_main("--execute", "--confirm-judge-v1")
        self.assertEqual(len(self.client.calls), 33)
        for qid in NO_ANSWER_IDS:
            self.assertFalse(any(self.fx.item(qid)["question"] in c["user"] for c in self.client.calls))
        for call in self.client.calls:
            self.assertIsNone(call["temperature"])  # frozen policy: not sent (provider-controlled)
            self.assertEqual(call["system"], REAL_CONFIG["system_prompt"])
            self.assertEqual(call["schema"], REAL_CONFIG["output_schema"])
            self.assertNotIn("TEXTO ORACLE", call["user"])

    def test_scores_only_in_scale_and_raw_output_kept(self):
        self.run_main("--execute", "--confirm-judge-v1", client=FakeJudgeClient([valid_output(1, 2, 0)]))
        first = self.results()[0]
        self.assertEqual([first["scores"][d]["score"] for d in judge.DIMENSIONS], [1, 2, 0])
        self.assertEqual(first["raw_judge_output"]["metadata"], {"eval_count": 42})
        for r in self.results():
            for d in judge.DIMENSIONS:
                self.assertIn(r["scores"][d]["score"], (0, 1, 2))

    def test_retry_on_schema_failure_with_identical_input(self):
        client = FakeJudgeClient(["not json", valid_output()])
        self.assertEqual(self.run_main("--execute", "--confirm-judge-v1", client=client), judge.EXIT_OK)
        self.assertEqual(client.calls[0], client.calls[1])
        first = self.results()[0]
        self.assertEqual(first["attempts"], 2)
        self.assertEqual([a["kind"] for a in first["attempt_log"]], ["invalid_output", "valid"])
        self.assertEqual(self.judge_manifest()["technical_retries"], 1)

    def test_retry_on_transport_error(self):
        client = FakeJudgeClient([ConnectionError("timeout"), valid_output()])
        self.assertEqual(self.run_main("--execute", "--confirm-judge-v1", client=client), judge.EXIT_OK)
        self.assertEqual(self.results()[0]["attempt_log"][0]["kind"], "transport_or_api_error")

    def test_surprising_score_is_not_retried(self):
        client = FakeJudgeClient([valid_output(0, 0, 0)])
        self.run_main("--execute", "--confirm-judge-v1", client=client)
        first = self.results()[0]
        self.assertEqual((first["attempts"], [first["scores"][d]["score"] for d in judge.DIMENSIONS]), (1, [0, 0, 0]))
        self.assertEqual(len(client.calls), 33)

    def test_second_failure_aborts_and_preserves_partial_results(self):
        client = FakeJudgeClient([valid_output(), valid_output(), "bad", '{"correctness": 3}'])
        self.assertEqual(self.run_main("--execute", "--confirm-judge-v1", client=client), judge.EXIT_ABORTED)
        self.assertEqual(len(client.calls), 4)  # max 2 attempts for the failing answer
        manifest = self.judge_manifest()
        self.assertEqual((manifest["status"], manifest["abort_stage"]), ("ABORTED", "judging"))
        results = self.results()
        self.assertEqual([r["id"] for r in results], ["D3_Q01", "D3_Q02", "D3_Q03"])
        self.assertIsNone(results[-1]["scores"])
        self.assertEqual(results[-1]["attempts"], 2)
        for name in (judge.REPORT, judge.JUDGE_SHA):
            self.assertFalse((self.judge_dir() / name).exists())

    def test_client_startup_failure_aborts(self):
        with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            rc = judge.main(["--execute", "--confirm-judge-v1"], cfg=self.fx.cfg,
                            client_factory=mock.Mock(side_effect=RuntimeError("no backend")), clock=Clock())
        self.assertEqual(rc, judge.EXIT_ABORTED)
        self.assertEqual(self.judge_manifest()["abort_stage"], "startup")

    def test_completed_run_hash_manifest(self):
        self.run_main("--execute", "--confirm-judge-v1")
        out = self.judge_dir()
        lines = (out / judge.JUDGE_SHA).read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines, [f"{sha(out / n)}  {n}" for n in (judge.RESULTS, judge.JUDGE_MANIFEST, judge.REPORT)])

    def test_source_files_unchanged(self):
        names = (det.RAW, det.MANIFEST, det.RUN_SHA, det.SCORES_JSON, det.REPORT_MD, det.SCORES_SHA)
        before = {n: sha(self.fx.run_dir / n) for n in names}
        frozen_files = (frozen.DATASET_JSON, frozen.PROTOCOL, judge.CONFIG_JSON, judge.CONFIG_MD)
        frozen_before = {n: sha(self.fx.root / n) for n in frozen_files}
        self.run_main("--execute", "--confirm-judge-v1")
        self.assertEqual({n: sha(self.fx.run_dir / n) for n in names}, before)
        self.assertEqual({n: sha(self.fx.root / n) for n in frozen_files}, frozen_before)

    def test_existing_judge_run_is_never_overwritten(self):
        self.run_main("--execute", "--confirm-judge-v1")
        with self.assertRaises(FileExistsError), mock.patch("sys.stdout"):
            judge.execute(self.fx.cfg, judge.load_judge_config(self.fx.cfg), self.validate(),
                          lambda c: FakeJudgeClient(), Clock())


# ---------------------------------------------------------------------------
# Aggregation and report
# ---------------------------------------------------------------------------


class AggregationTests(Base):
    def completed_results(self):
        client = FakeJudgeClient([valid_output(1, 2, 2), valid_output(2, 1, 0)])
        self.run_main("--execute", "--confirm-judge-v1", client=client)
        return self.results()

    def test_mean_over_35_with_zeros_and_distributions_sum_to_35(self):
        agg = judge.aggregate(self.completed_results())
        c = agg["overall"]["correctness"]
        self.assertEqual(c["n"], 35)
        self.assertEqual(c["sum"], 1 + 2 + 31 * 2)  # 33 judged (two scripted, the rest 2) + 2 zeros
        self.assertAlmostEqual(c["mean"], c["sum"] / 35)
        self.assertEqual(c["distribution"], {"0": 2, "1": 1, "2": 32})
        for d in judge.DIMENSIONS:
            self.assertEqual(sum(agg["overall"][d]["distribution"].values()), 35)

    def test_per_category_counts_are_5(self):
        agg = judge.aggregate(self.completed_results())
        for cat in frozen.CATEGORIES:
            for d in judge.DIMENSIONS:
                self.assertEqual(agg["by_category"][cat][d]["n"], 5)

    def test_no_composite_score(self):
        agg = judge.aggregate(self.completed_results())
        self.assertEqual({k.lower() for k in keys_recursive(agg)} &
                         {"overall_score", "composite", "composite_score", "weighted", "global_mean"}, set())
        report = (self.judge_dir() / judge.REPORT).read_text(encoding="utf-8")
        self.assertIn("No global average", report)
        for n in range(1, 11):
            self.assertIn(f"\n## {n}. ", report)

    def test_repeated_aggregation_and_report_are_deterministic(self):
        results = self.completed_results()
        self.assertEqual(json.dumps(judge.aggregate(results), sort_keys=True),
                         json.dumps(judge.aggregate(copy.deepcopy(results)), sort_keys=True))
        manifest = self.judge_manifest()
        det_scores = json.loads((self.fx.run_dir / det.SCORES_JSON).read_text(encoding="utf-8"))
        self.assertEqual(judge.render_report(manifest, judge.aggregate(results), results, det_scores),
                         (self.judge_dir() / judge.REPORT).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# OpenAI adapter and .env handling (fake SDK; no request is ever sent)
# ---------------------------------------------------------------------------

SECRET = "sk-test-SECRET-0123456789abcdef"
REPO_ROOT = EVAL_DIR.parents[1]


class FakeUsage:
    input_tokens, output_tokens, total_tokens = 1200, 340, 1540

    class output_tokens_details:  # noqa: N801
        reasoning_tokens = 256

    class input_tokens_details:  # noqa: N801
        cached_tokens = 0


class FakeOpenAIResponse:
    def __init__(self, text, status="completed", rid="resp_123"):
        self.output_text, self.status, self.id = text, status, rid
        self.model, self.usage, self.incomplete_details = "gpt-5-mini-2025-08-07", FakeUsage(), None


class FakeSDK:
    """Stands in for openai.OpenAI: records responses.create kwargs; scripted outputs or exceptions."""

    def __init__(self, outputs=None):
        self.outputs, self.calls = list(outputs or []), []
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        out = self.outputs.pop(0) if self.outputs else FakeOpenAIResponse(valid_output())
        if isinstance(out, BaseException):
            raise out
        return out


class AuthenticationError(Exception):
    status_code = 401


class APIConnectionError(Exception):
    pass


def openai_config(mutate=None):
    config = copy.deepcopy(REAL_CONFIG)
    if mutate:
        mutate(config)
    return config


class OpenAIAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env_file = Path(self.tmp.name) / ".env"
        self.env = mock.patch.dict("os.environ", {}, clear=False)
        self.env.start()
        import os
        os.environ.pop(judge.API_KEY_VAR, None)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def client(self, sdk=None, config=None):
        self.env_file.write_text(f"{judge.API_KEY_VAR}={SECRET}\n", encoding="utf-8")
        self.sdk = sdk or FakeSDK()
        self.factory_args = []

        def sdk_factory(key, settings):
            self.factory_args.append((key, settings))
            return self.sdk

        return judge.make_openai_client(config or openai_config(), env_file=self.env_file, sdk_factory=sdk_factory)

    def test_key_loaded_from_dotenv(self):
        self.client()
        self.assertEqual(self.factory_args[0][0], SECRET)

    def test_existing_environment_variable_takes_precedence(self):
        import os
        os.environ[judge.API_KEY_VAR] = "sk-from-environment-0000"
        self.client()
        self.assertEqual(self.factory_args[0][0], "sk-from-environment-0000")

    def test_missing_or_empty_key_aborts_before_any_sdk(self):
        factory = mock.Mock()
        with self.assertRaises(judge.JudgeError) as ctx:
            judge.make_openai_client(openai_config(), env_file=self.env_file, sdk_factory=factory)  # no .env
        self.assertEqual(str(ctx.exception), "OPENAI_API_KEY is not configured.")
        self.env_file.write_text(f"{judge.API_KEY_VAR}=\n", encoding="utf-8")
        with self.assertRaises(judge.JudgeError):
            judge.make_openai_client(openai_config(), env_file=self.env_file, sdk_factory=factory)
        factory.assert_not_called()

    def test_request_settings(self):
        config = openai_config()
        client = self.client(config=config)
        client.judge(config["system_prompt"], "USER MESSAGE", config["output_schema"], None)
        kwargs = self.sdk.calls[0]
        self.assertEqual(kwargs["model"], "gpt-5-mini-2025-08-07")
        self.assertEqual(kwargs["instructions"], config["system_prompt"])
        self.assertEqual(kwargs["input"], "USER MESSAGE")
        self.assertEqual(kwargs["reasoning"], {"effort": "medium"})
        self.assertIs(kwargs["store"], False)
        self.assertEqual(kwargs["max_output_tokens"], config["judge"]["max_output_tokens"])
        self.assertEqual(kwargs["text"], {"format": {"type": "json_schema", "name": "d3_judge_scores",
                                                     "schema": config["output_schema"], "strict": True}})
        for absent in ("tools", "tool_choice", "background", "conversation", "previous_response_id", "temperature"):
            self.assertNotIn(absent, kwargs)

    def test_official_config_never_sends_sampling_parameters(self):
        config = openai_config()
        self.assertIsNone(config["judge"]["temperature"])
        client = self.client(config=config)
        judge.judge_answer(client, config, "u")  # the runner path: temperature comes from the frozen config
        kwargs = self.sdk.calls[0]
        for absent in ("temperature", "top_p", "logprobs", "top_logprobs"):
            self.assertNotIn(absent, kwargs)
        self.assertEqual((kwargs["model"], kwargs["reasoning"], kwargs["max_output_tokens"], kwargs["store"]),
                         ("gpt-5-mini-2025-08-07", {"effort": "medium"}, 6000, False))
        self.assertTrue(kwargs["text"]["format"]["strict"])
        self.assertNotIn("tools", kwargs)

    def test_exact_schema_matches_the_specification(self):
        dim = {"type": "object", "properties": {"score": {"type": "integer", "enum": [0, 1, 2]},
                                                "reason": {"type": "string"}},
               "required": ["score", "reason"], "additionalProperties": False}
        self.assertEqual(REAL_CONFIG["output_schema"],
                         {"type": "object", "properties": {"correctness": dim, "faithfulness": dim, "relevance": dim},
                          "required": ["correctness", "faithfulness", "relevance"], "additionalProperties": False})

    def test_sdk_created_without_automatic_retries(self):
        self.client()
        self.assertEqual(self.factory_args[0][1]["sdk_max_retries"], 0)

    def test_metadata_captured(self):
        config = openai_config()
        response = self.client(config=config).judge("s", "u", config["output_schema"], None)
        self.assertEqual(response.metadata["response_id"], "resp_123")
        self.assertEqual(response.metadata["response_model"], "gpt-5-mini-2025-08-07")
        self.assertEqual(response.metadata["usage"], {"input_tokens": 1200, "output_tokens": 340, "total_tokens": 1540,
                                                      "reasoning_tokens": 256, "cached_tokens": 0})

    def test_incomplete_response_is_a_schema_failure(self):
        config = openai_config()
        client = self.client(FakeSDK([FakeOpenAIResponse(valid_output(), status="incomplete"),
                                      FakeOpenAIResponse(valid_output(1, 1, 1))]), config)
        scores, attempts, _ = judge.judge_answer(client, config, "u")
        self.assertEqual([a["kind"] for a in attempts], ["invalid_output", "valid"])
        self.assertEqual(scores["correctness"]["score"], 1)

    def test_api_error_retried_and_redacted(self):
        config = openai_config()
        client = self.client(FakeSDK([APIConnectionError(f"failed with key {SECRET}"),
                                      FakeOpenAIResponse(valid_output())]), config)
        _, attempts, raw = judge.judge_answer(client, config, "u")
        self.assertEqual(attempts[0]["kind"], "transport_or_api_error")
        self.assertNotIn(SECRET, json.dumps(attempts))
        self.assertIn("[REDACTED]", attempts[0]["error"])
        self.assertEqual(raw["metadata"]["response_id"], "resp_123")

    def test_authentication_error_is_generic(self):
        config = openai_config()
        client = self.client(FakeSDK([AuthenticationError(f"Incorrect API key provided: {SECRET}")] * 2), config)
        with self.assertRaises(judge.JudgeAbort) as ctx:
            judge.judge_answer(client, config, "u")
        self.assertEqual([a["error"] for a in ctx.exception.attempts],
                         ["JudgeTransportError: OpenAI authentication failed"] * 2)
        self.assertNotIn(SECRET, json.dumps(ctx.exception.attempts))

    def test_first_valid_output_is_official(self):
        config = openai_config()
        client = self.client(FakeSDK([FakeOpenAIResponse(valid_output(0, 1, 2)), FakeOpenAIResponse(valid_output())]),
                             config)
        scores, attempts, _ = judge.judge_answer(client, config, "u")
        self.assertEqual([scores[d]["score"] for d in judge.DIMENSIONS], [0, 1, 2])
        self.assertEqual((len(attempts), len(self.sdk.calls)), (1, 1))

    def test_client_description_has_no_secret(self):
        description = self.client().describe()
        self.assertNotIn(SECRET, json.dumps(description))
        self.assertEqual(description["model"], "gpt-5-mini-2025-08-07")

    def test_env_file_is_git_ignored_and_example_has_no_value(self):
        out = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=REPO_ROOT)
        self.assertEqual(out.returncode, 0)
        out = subprocess.run(["git", "check-ignore", "-q", ".env.example"], cwd=REPO_ROOT)
        self.assertNotEqual(out.returncode, 0)
        self.assertEqual((REPO_ROOT / ".env.example").read_text(encoding="utf-8").strip(), "OPENAI_API_KEY=")


class OpenAIExecutionTests(Base):
    """Full fake judge run through the OpenAI adapter: the key never reaches any output."""

    def setUp(self):
        super().setUp()
        self.fx.write_config(mutate=lambda c: c["judge"].update(provider="openai", model="gpt-5-mini-2025-08-07"))
        self.env_file = Path(self.tmp.name) / ".env"
        self.env_file.write_text(f"{judge.API_KEY_VAR}={SECRET}\n", encoding="utf-8")
        self.env = mock.patch.dict("os.environ", {}, clear=False)
        self.env.start()
        import os
        os.environ.pop(judge.API_KEY_VAR, None)

    def tearDown(self):
        self.env.stop()
        super().tearDown()

    def execute(self, sdk, env_file=None):
        import io
        out, err = io.StringIO(), io.StringIO()
        factory = lambda c: judge.make_openai_client(c, env_file=env_file or self.env_file,  # noqa: E731
                                                     sdk_factory=lambda key, s: sdk)
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            rc = judge.main(["--execute", "--confirm-judge-v1"], cfg=self.fx.cfg, client_factory=factory, clock=Clock())
        return rc, out.getvalue() + err.getvalue()

    def test_key_never_persisted_or_printed(self):
        sdk = FakeSDK()
        rc, console = self.execute(sdk)
        self.assertEqual(rc, judge.EXIT_OK)
        self.assertEqual(len(sdk.calls), 33)  # synthetic fixture: 35 - 2 deterministic zeros
        self.assertNotIn(SECRET, console)
        for path in self.judge_dir().iterdir():
            self.assertNotIn(SECRET, path.read_text(encoding="utf-8"), path.name)
        manifest = self.judge_manifest()
        self.assertEqual(manifest["request_settings"]["reasoning_effort"], "medium")
        self.assertIs(manifest["request_settings"]["store"], False)
        self.assertEqual(self.results()[0]["raw_judge_output"]["metadata"]["response_id"], "resp_123")

    def test_auth_failure_aborts_without_leaking_the_key(self):
        sdk = FakeSDK([AuthenticationError(f"Incorrect API key provided: {SECRET}")] * 2)
        rc, console = self.execute(sdk)
        self.assertEqual(rc, judge.EXIT_ABORTED)
        self.assertNotIn(SECRET, console)
        for path in self.judge_dir().iterdir():
            self.assertNotIn(SECRET, path.read_text(encoding="utf-8"))
        self.assertIn("OpenAI authentication failed", (self.judge_dir() / judge.JUDGE_MANIFEST).read_text(encoding="utf-8"))

    def test_missing_key_aborts_startup_without_calls(self):
        sdk = FakeSDK()
        rc, console = self.execute(sdk, env_file=Path(self.tmp.name) / "missing.env")
        self.assertEqual(rc, judge.EXIT_ABORTED)
        self.assertEqual(sdk.calls, [])
        manifest = self.judge_manifest()
        self.assertEqual((manifest["abort_stage"], manifest["abort_error"]["message"]),
                         ("startup", "OPENAI_API_KEY is not configured."))

    def test_validate_only_needs_no_key_and_creates_no_client(self):
        factory = mock.Mock()
        with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            rc = judge.main(["--validate-only"], cfg=self.fx.cfg, client_factory=factory, clock=Clock())
        self.assertEqual(rc, judge.EXIT_OK)
        factory.assert_not_called()

    def test_judge_model_llama_rejected(self):
        self.fx.manifest_overrides = {"system": {"run_date": "2026-10-06", "planner": {"model": "llama3.2:3b"},
                                                 "generator": {"model": "llama3.2:3b"}}}
        self.fx.rebuild_run()
        self.fx.write_config(mutate=lambda c: c["judge"].update(provider="openai", model="llama3.2:3b"))
        with self.assertRaises(judge.JudgeError):
            self.validate()

    def test_openai_config_settings_are_enforced(self):
        for mutate in (lambda c: c["judge"].update(store=True), lambda c: c["judge"].update(tools="web_search"),
                       lambda c: c["judge"].update(sdk_max_retries=2), lambda c: c["judge"].update(api="chat"),
                       lambda c: c["judge"]["structured_output"].update(strict=False)):
            self.fx.write_config(mutate=lambda c, m=mutate: (c["judge"].update(provider="openai"), m(c)))
            with self.assertRaises(judge.JudgeError):
                judge.load_judge_config(self.fx.cfg)


class FrozenSamplingPolicyTests(Base):
    """temperature = null / not sent, reasoning_effort = medium, and the frozen official values are enforced."""

    def test_frozen_fixture_with_null_temperature_is_accepted(self):
        loaded = judge.load_judge_config(self.fx.cfg)
        self.assertEqual((loaded["config"]["status"], loaded["hashed"]), ("FROZEN", True))
        self.assertIsNone(loaded["config"]["judge"]["temperature"])

    def test_manifest_and_report_record_the_policy(self):
        self.assertEqual(self.run_main("--execute", "--confirm-judge-v1"), judge.EXIT_OK)
        manifest = self.judge_manifest()
        self.assertIsNone(manifest["temperature"])
        self.assertEqual(manifest["temperature_policy"], "not_sent_provider_controlled")
        self.assertEqual(manifest["reasoning_effort"], "medium")
        self.assertEqual((manifest["provider"], manifest["model"]), ("openai", "gpt-5-mini-2025-08-07"))
        self.assertTrue(all(c["temperature"] is None for c in self.client.calls))
        report = (self.judge_dir() / judge.REPORT).read_text(encoding="utf-8")
        self.assertIn("| Judge | OpenAI gpt-5-mini-2025-08-07 |", report)
        self.assertIn("| Reasoning effort | medium |", report)
        self.assertIn("| Temperature | not explicitly set / provider-controlled (not sent) |", report)
        self.assertNotIn("| Temperature | 0", report)
        self.assertNotIn("| temperature |", report)

    def test_tampered_frozen_values_rejected(self):
        tampering = [
            ("temperature 0", lambda c: c["judge"].update(temperature=0, temperature_policy=None)),
            ("temperature 0.5", lambda c: c["judge"].update(temperature=0.5)),
            ("null without policy", lambda c: c["judge"].pop("temperature_policy")),
            ("other policy", lambda c: c["judge"].update(temperature_policy="whatever")),
            ("effort high", lambda c: c["judge"].update(reasoning_effort="high")),
            ("model alias", lambda c: c["judge"].update(model="gpt-5-mini")),
            ("other model", lambda c: c["judge"].update(model="gpt-5")),
            ("provider", lambda c: c["judge"].update(provider="ollama")),
            ("max tokens", lambda c: c["judge"].update(max_output_tokens=4000)),
            ("attempts", lambda c: c["judge"].update(max_attempts=3)),
            ("store", lambda c: c["judge"].update(store=True)),
        ]
        for name, mutate in tampering:
            with self.subTest(name):
                self.fx.write_config(mutate=mutate)  # re-hashed: rejected by the frozen-value check itself
                with self.assertRaises(judge.JudgeError):
                    judge.load_judge_config(self.fx.cfg)

    def test_edit_after_hashing_rejected(self):
        path = self.fx.root / judge.CONFIG_JSON
        config = json.loads(path.read_text(encoding="utf-8"))
        config["judge"]["reasoning_effort"] = "low"
        path.write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaises(judge.JudgeError) as ctx:
            judge.load_judge_config(self.fx.cfg)
        self.assertIn("reasoning_effort", str(ctx.exception))

    def test_no_answer_still_uncalled_and_counts_derived(self):
        self.run_main("--execute", "--confirm-judge-v1")
        manifest = self.judge_manifest()
        self.assertEqual((manifest["deterministic_zero_count"], manifest["llm_judge_expected_count"]), (2, 33))
        self.assertEqual(len(self.client.calls), 33)


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------


class IsolationTests(unittest.TestCase):
    def test_validate_only_imports_no_model_network_or_provider_module(self):
        """Fresh interpreter, real frozen files and the real PREPARED config: validate-only only."""

        heavy = ["ollama", "openai", "dotenv", "anthropic", "httpx", "requests", "urllib.request", "http.client", "mcp",
                 "torch", "chromadb", "langchain_core", "langchain_ollama", "rag_pipeline", "expert_agent", "planner",
                 "evaluation_trace"]
        code = ("import sys; sys.path.insert(0, r'%s'); import run_d3_judge as j; rc = j.main(['--validate-only']); "
                "print('RC', rc); print('HEAVY', [m for m in %r if m in sys.modules])" % (EVAL_DIR, heavy))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8",
                             timeout=120)
        self.assertIn("RC 0", out.stdout, out.stderr)
        self.assertIn("HEAVY []", out.stdout)
        self.assertIn("31 requiring LLM judge", out.stdout)
        self.assertIn("4 protocol deterministic-zero", out.stdout)
        self.assertIn("READY TO JUDGE", out.stdout)
        self.assertNotIn("NOT READY", out.stdout)


if __name__ == "__main__":
    unittest.main()

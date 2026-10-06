"""D3 V1 deterministic scorer: frozen dataset + frozen protocol + one official raw run -> official non-LLM metrics.

    uv run python d3/evaluation/score_d3_evaluation.py --run-dir d3/evaluation/runs/<run_id> --validate-only
    uv run python d3/evaluation/score_d3_evaluation.py --run-dir d3/evaluation/runs/<run_id>

Implements exactly the metrics of D3_EVALUATION_PROTOCOL_V1.md Sections 5-6: Exact Capability Match,
Tool Accuracy, Hit@3, macro Recall@3 and MRR (oracle retrieval). Everything is derived from the frozen
dataset and raw_results.jsonl; nothing is re-executed. Standard library only: no agent, planner,
retriever, embedding model, vector store, MCP client, LLM or network. The raw run files are only read;
the outputs are new derived files in the run directory, byte-stable for the same inputs.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_d3_evaluation as frozen  # noqa: E402  (stdlib-only validation of the frozen dataset/protocol)

SCORING_VERSION = "D3_DETERMINISTIC_SCORING_V1"
SCORES_JSON = "deterministic_scores_v1.json"
REPORT_MD = "D3_DETERMINISTIC_SCORING_REPORT_V1.md"
SCORES_SHA = "DETERMINISTIC_SCORING_V1.sha256"
DERIVED = (SCORES_JSON, REPORT_MD, SCORES_SHA)
RAW, MANIFEST, RUN_SHA = "raw_results.jsonl", "run_manifest.json", "RUN.sha256"
SERVERS = ("weather", "places")
CAPS = ("rag", "weather", "places")


class ScoringError(RuntimeError):
    """The inputs are not exactly what the protocol requires; nothing is scored."""


# ---------------------------------------------------------------------------
# Metric definitions (protocol Sections 5 and 6)
# ---------------------------------------------------------------------------


def predicted_capabilities(planner: dict[str, Any]) -> dict[str, bool]:
    """P.rag = use_rag; P.weather/places = a tool call on that server; planner failure -> all false."""

    if not planner["success"]:
        return {"rag": False, "weather": False, "places": False}
    servers = {call["server"] for call in planner["tool_calls"]}
    return {"rag": bool(planner["use_rag"]), "weather": "weather" in servers, "places": "places" in servers}


def selected_tool(planner: dict[str, Any], server: str) -> str | None:
    if not planner["success"]:
        return None
    return next((call["tool"] for call in planner["tool_calls"] if call["server"] == server), None)


def retrieval_scores(gold_chunks: list[str], oracle: dict[str, Any]) -> dict[str, Any]:
    """Hit@3_i, Recall@3_i (distinct gold chunks) and RR_i; an oracle failure scores 0 on all three."""

    gold = set(gold_chunks)
    failed = oracle.get("error") is not None or not isinstance(oracle.get("top3"), list)
    retrieved = [] if failed else [entry["chunk_id"] for entry in sorted(oracle["top3"], key=lambda e: e["rank"])]
    found = gold & set(retrieved)
    first_rank = next((rank for rank, chunk in enumerate(retrieved, start=1) if chunk in gold), None)
    return {
        "oracle_failed": failed,
        "retrieved_chunk_ids": retrieved,
        "gold_retrieved": sorted(found),
        "first_gold_rank": first_rank,
        "hit_at_3": 1 if found else 0,
        "recall_at_3": len(found) / len(gold),
        "reciprocal_rank": 1.0 / first_rank if first_rank else 0.0,
    }


def ratio(correct: int | float, total: int) -> dict[str, Any]:
    return {"correct": correct, "total": total, "value": correct / total, "percentage": 100.0 * correct / total}


# ---------------------------------------------------------------------------
# Validation of the run (nothing is scored unless every check passes)
# ---------------------------------------------------------------------------


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise ScoringError(message)


def read_run_sha(run_dir: Path) -> dict[str, str]:
    path = run_dir / RUN_SHA
    _check(path.is_file(), f"{RUN_SHA} missing")
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, _, name = line.strip().partition("  ")
            entries[name.lstrip("*")] = digest
    return entries


def _check_record_shape(record: dict[str, Any]) -> None:
    qid = record.get("id")
    for key in ("planner", "oracle_retrieval", "weather", "places", "error", "final_answer", "gold_snapshot"):
        _check(key in record, f"{qid}: raw record without {key!r}")
    planner = record["planner"]
    _check(isinstance(planner, dict) and isinstance(planner.get("success"), bool),
           f"{qid}: planner.success must be true or false")
    if planner["success"]:
        _check(isinstance(planner.get("use_rag"), bool), f"{qid}: planner.use_rag must be a boolean")
        calls = planner.get("tool_calls")
        _check(isinstance(calls, list) and all(isinstance(c, dict) and c.get("server") in SERVERS
                                               and isinstance(c.get("tool"), str) for c in calls),
               f"{qid}: malformed planner.tool_calls")
    oracle = record["oracle_retrieval"]
    _check(isinstance(oracle, dict), f"{qid}: oracle_retrieval must be an object")
    if isinstance(oracle.get("top3"), list):
        _check(len(oracle["top3"]) <= 3, f"{qid}: oracle top3 has more than 3 entries")
        _check(all(isinstance(e, dict) and isinstance(e.get("rank"), int) and isinstance(e.get("chunk_id"), str)
                   for e in oracle["top3"]), f"{qid}: malformed oracle top3 entry")


def validate_run(run_dir: Path, cfg: frozen.RunnerConfig) -> dict[str, Any]:
    """Protocol + dataset freeze, RUN.sha256, manifest and the 35 raw records against the dataset."""

    try:
        frozen_inputs = frozen.validate(cfg)  # dataset schema/balance/hashes and protocol hash (pinned too)
    except frozen.ValidationError as exc:
        raise ScoringError(f"frozen inputs: {exc}") from None
    items = frozen_inputs["items"]

    _check(run_dir.is_dir(), f"run directory not found: {run_dir}")
    run_sha = read_run_sha(run_dir)
    _check(set(run_sha) == {RAW, MANIFEST}, f"{RUN_SHA} must list exactly {RAW} and {MANIFEST}")
    raw_sha = {}
    for name in (RAW, MANIFEST):
        _check((run_dir / name).is_file(), f"{name} missing")
        raw_sha[name] = frozen.sha256_file(run_dir / name)
        _check(raw_sha[name] == run_sha[name], f"{name} does not match {RUN_SHA}")

    try:
        manifest = json.loads((run_dir / MANIFEST).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScoringError(f"{MANIFEST} is not valid JSON: {exc}") from None
    _check(isinstance(manifest, dict), f"{MANIFEST} is not a JSON object")
    _check(manifest.get("status") == "COMPLETED", f"run status is {manifest.get('status')!r}, not COMPLETED")
    _check(manifest.get("valid_experimental_run") is not False, "run is marked valid_experimental_run = false")
    _check(manifest.get("question_count_expected") == 35, "manifest question_count_expected != 35")
    _check(manifest.get("question_count_completed") == 35, "manifest question_count_completed != 35")
    _check((manifest.get("dataset") or {}).get("sha256") == frozen_inputs["dataset_hashes"],
           "dataset SHA-256 recorded in the manifest differs from the current frozen dataset")
    _check((manifest.get("protocol") or {}).get("sha256") == frozen_inputs["protocol_sha256"],
           "protocol SHA-256 recorded in the manifest differs from the current frozen protocol")

    lines = (run_dir / RAW).read_text(encoding="utf-8").split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    _check(len(lines) == 35, f"{RAW} must have exactly 35 lines, has {len(lines)}")
    records = []
    for number, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ScoringError(f"{RAW} line {number} is not valid JSON: {exc}") from None
        _check(isinstance(record, dict), f"{RAW} line {number} is not a JSON object")
        records.append(record)
    ids = [r.get("id") for r in records]
    duplicates = sorted({i for i in ids if ids.count(i) > 1}, key=str)
    _check(not duplicates, f"duplicated raw IDs: {duplicates}")
    missing = [i for i in frozen.EXPECTED_IDS if i not in ids]
    _check(not missing, f"missing questions in the raw results: {missing}")
    _check(ids == list(frozen.EXPECTED_IDS), "raw IDs are not exactly D3_Q01..D3_Q35 in order")

    for item, record in zip(items, records):
        qid = item["id"]
        _check(record.get("question") == item["question"], f"{qid}: raw question differs from the frozen dataset")
        _check(record.get("category") == item["category"], f"{qid}: raw category differs from the frozen dataset")
        expected_snapshot = {"capabilities": item["gold_capabilities"],
                             "expected_weather_tool": item["weather"]["expected_tool"],
                             "expected_places_tool": item["places"]["expected_tool"]}
        _check(record.get("gold_snapshot") == expected_snapshot, f"{qid}: gold_snapshot inconsistent with the dataset")
        _check_record_shape(record)
        _check(record["oracle_retrieval"].get("required_by_gold") is item["gold_capabilities"]["rag"],
               f"{qid}: oracle_retrieval.required_by_gold inconsistent with the dataset")

    rag_items = [i for i in items if i["gold_capabilities"]["rag"]]
    _check(len(rag_items) == 20, f"expected 20 RAG questions, found {len(rag_items)}")
    needs = sum(i["gold_capabilities"][s] for i in items for s in SERVERS)
    _check(needs == 40, f"expected 40 MCP tool needs, found {needs}")
    return {"items": items, "records": records, "manifest": manifest, "frozen": frozen_inputs,
            "raw_sha": raw_sha, "run_sha_file": frozen.sha256_file(run_dir / RUN_SHA)}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _cap_name(cap: str) -> str:
    return "RAG" if cap == "rag" else cap.capitalize()


def mechanical_agency_notes(gold: dict[str, bool], predicted: dict[str, bool], planner_ok: bool) -> list[str]:
    if not planner_ok:
        return ["planner failed: no plan (all capabilities predicted false)"]
    notes = []
    for cap in CAPS:
        if gold[cap] and not predicted[cap]:
            notes.append(f"{_cap_name(cap)} capability absent although gold=true")
        if predicted[cap] and not gold[cap]:
            notes.append(f"{_cap_name(cap)} capability added although gold=false")
    return notes


def score(validated: dict[str, Any], run_dir_label: str) -> dict[str, Any]:
    items, records, manifest = validated["items"], validated["records"], validated["manifest"]
    per_question = []
    ecm_by_cat = {c: [0, 0] for c in frozen.CATEGORIES}
    ecm_correct, tool_correct = 0, {"weather": [0, 0], "places": [0, 0]}
    hits = recalls = rrs = 0.0
    rag_count = 0
    agency_errors, tool_errors, retrieval_rows = [], [], []

    for item, record in zip(items, records):
        planner = record["planner"]
        gold = dict(item["gold_capabilities"])
        predicted = predicted_capabilities(planner)
        ecm = 1 if predicted == gold else 0
        ecm_correct += ecm
        ecm_by_cat[item["category"]][0] += ecm
        ecm_by_cat[item["category"]][1] += 1
        calls = planner["tool_calls"] if planner["success"] else None
        if not ecm:
            agency_errors.append({"id": item["id"], "category": item["category"], "gold_capabilities": gold,
                                  "predicted_capabilities": predicted, "planner_success": planner["success"],
                                  "planner_tool_calls": calls,
                                  "observations": mechanical_agency_notes(gold, predicted, planner["success"])})

        tools = {}
        for server in SERVERS:
            if not gold[server]:
                tools[server] = None  # no gold need: not part of Tool Accuracy
                continue
            expected = item[server]["expected_tool"]
            chosen = selected_tool(planner, server)
            correct = 1 if chosen == expected else 0
            tool_correct[server][0] += correct
            tool_correct[server][1] += 1
            tools[server] = {"expected_tool": expected, "selected_tool": chosen, "correct": correct}
            if not correct:
                observation = ("planner failed: no plan" if not planner["success"] else
                               f"no {server} call in the plan" if chosen is None else
                               f"{chosen} selected instead of {expected}")
                tool_errors.append({"id": item["id"], "category": item["category"], "server": server,
                                    "expected_tool": expected, "selected_tool": chosen, "observation": observation})

        if gold["rag"]:
            rag_count += 1
            oracle = record["oracle_retrieval"]
            r = retrieval_scores(item["rag"]["gold_chunks"], oracle)
            hits += r["hit_at_3"]
            recalls += r["recall_at_3"]
            rrs += r["reciprocal_rank"]
            top3 = [] if r["oracle_failed"] else [
                {"rank": e["rank"], "chunk_id": e["chunk_id"], "cosine_distance": e.get("cosine_distance")}
                for e in sorted(oracle["top3"], key=lambda e: e["rank"])]
            retrieval = {"included": True, "query": oracle.get("query"),
                         "gold_chunks": list(item["rag"]["gold_chunks"]), "oracle_top3": top3,
                         "oracle_error": oracle.get("error"), **r}
            retrieval_rows.append({"id": item["id"], **retrieval})
        else:
            retrieval = {"included": False}

        per_question.append({
            "id": item["id"], "category": item["category"],
            "agency": {"gold_capabilities": gold, "predicted_capabilities": predicted,
                       "planner_success": planner["success"], "planner_tool_calls": calls,
                       "exact_capability_match": ecm},
            "tool_accuracy": tools,
            "retrieval": retrieval,
        })

    weather_n, places_n = tool_correct["weather"], tool_correct["places"]
    total_tools = weather_n[1] + places_n[1]
    official = {
        "exact_capability_match": ratio(ecm_correct, len(items)),
        "tool_accuracy": {**ratio(weather_n[0] + places_n[0], total_tools),
                          "breakdown": {"weather": ratio(*weather_n), "places": ratio(*places_n)},
                          "breakdown_note": "informative breakdown of Tool Accuracy, not separate primary metrics"},
        "retrieval": {
            "questions": rag_count,
            "query_source": "dataset rag.information_need (oracle retrieval captured in the run)",
            "hit_at_3": {"hits": int(hits), "total": rag_count, "value": hits / rag_count,
                         "percentage": 100.0 * hits / rag_count},
            "macro_recall_at_3": {"total": rag_count, "value": recalls / rag_count,
                                  "percentage": 100.0 * recalls / rag_count},
            "mrr": {"total": rag_count, "value": rrs / rag_count},
        },
    }
    return {
        "scoring_version": SCORING_VERSION,
        "run_id": manifest["run_id"],
        "run_dir": run_dir_label,
        "run": {"status": manifest["status"], "valid_experimental_run": manifest.get("valid_experimental_run"),
                "started_at": manifest.get("started_at"), "finished_at": manifest.get("finished_at"),
                "git": manifest.get("git"), "run_date": (manifest.get("system") or {}).get("run_date")},
        "inputs": {
            "dataset_sha256": validated["frozen"]["dataset_hashes"],
            "protocol_sha256": validated["frozen"]["protocol_sha256"],
            "raw_results_sha256": validated["raw_sha"][RAW],
            "run_manifest_sha256": validated["raw_sha"][MANIFEST],
            "run_sha256_file_sha256": validated["run_sha_file"],
        },
        "integrity": {"status": "PASS", "questions": len(records), "rag_questions": rag_count,
                      "expected_mcp_tool_needs": total_tools},
        "official_metrics": official,
        "category_breakdown": {"exact_capability_match": {c: ratio(*ecm_by_cat[c]) for c in frozen.CATEGORIES},
                               "note": "breakdown of ECM, not a separate primary metric"},
        "per_question": per_question,
        "error_analysis": {"agency_errors": agency_errors, "tool_selection_errors": tool_errors,
                           "retrieval_imperfect": [row for row in retrieval_rows
                                                   if row["hit_at_3"] == 0 or row["recall_at_3"] < 1
                                                   or row["reciprocal_rank"] < 1]},
        "descriptive_run_summary": descriptive_summary(records),
    }


def descriptive_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Execution outcomes: descriptive counts only, NOT official metrics; they never change ECM/TA."""

    stages = collections.Counter(r["error"]["stage"] for r in records if r["error"])
    tools = {}
    for server in SERVERS:
        blocks = [r[server] for r in records]
        tools[server] = {"planned": sum(1 for b in blocks if b.get("planned")),
                         "executed": sum(1 for b in blocks if b.get("executed")),
                         "succeeded": sum(1 for b in blocks if b.get("success") is True),
                         "failed": sum(1 for b in blocks if b.get("success") is False),
                         "failed_ids": [r["id"] for r in records if r[server].get("success") is False]}
    return {
        "note": "descriptive counts, NOT official metrics",
        "final_answer_produced": sum(1 for r in records if r["final_answer"] is not None),
        "no_final_answer": sum(1 for r in records if r["final_answer"] is None),
        "no_final_answer_ids": [r["id"] for r in records if r["final_answer"] is None],
        "errors_by_stage": dict(sorted(stages.items())),
        "error_ids_by_stage": {s: [r["id"] for r in records if r["error"] and r["error"]["stage"] == s]
                               for s in sorted(stages)},
        "planner_failures": sum(1 for r in records if r["planner"]["success"] is False),
        "tool_execution": tools,
        "oracle_retrieval_errors": [r["id"] for r in records if r["oracle_retrieval"].get("error")],
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _caps(c: dict[str, bool]) -> str:
    on = [_cap_name(k) for k in CAPS if c[k]]
    return " + ".join(on) if on else "(none)"


def _calls(calls) -> str:
    if calls is None:
        return "(no plan)"
    if not calls:
        return "[]"
    return "; ".join(f"{c['server']}.{c['tool']}({json.dumps(c.get('arguments'), ensure_ascii=False, sort_keys=True)})"
                     for c in calls)


def render_report(s: dict[str, Any]) -> str:
    o, run, d = s["official_metrics"], s["run"], s["descriptive_run_summary"]
    ecm, ta, rt = o["exact_capability_match"], o["tool_accuracy"], o["retrieval"]
    L = []
    a = L.append
    a("# D3 Deterministic Scoring Report V1")
    a("")
    a(f"Scoring version: `{s['scoring_version']}`. Scored with `d3/evaluation/score_d3_evaluation.py` (standard library "
      "only) from the frozen dataset, the frozen protocol and the official raw run. Nothing was re-executed; no agent, "
      "planner, retriever, embedding model, MCP server, LLM or network was used. No LLM-as-Judge score is included.")
    a("")
    a("## 1. Run Scored")
    a("")
    a("| Field | Value |")
    a("|---|---|")
    a(f"| run_id | `{s['run_id']}` |")
    a(f"| run directory | `{s['run_dir']}` |")
    a(f"| git commit | `{(run['git'] or {}).get('commit')}` |")
    a(f"| git dirty | {(run['git'] or {}).get('dirty')} |")
    a(f"| run status | {run['status']} (valid_experimental_run = {run['valid_experimental_run']}) |")
    a(f"| started_at | {run['started_at']} |")
    a(f"| finished_at | {run['finished_at']} |")
    a(f"| run date (for relative dates) | {run['run_date']} |")
    a("")
    a("## 2. Integrity Validation")
    a("")
    a("| Check | Result |")
    a("|---|---|")
    for name, digest in s["inputs"]["dataset_sha256"].items():
        a(f"| dataset `{name}` = freeze manifest = runner pin = run manifest | PASS (`{digest}`) |")
    a(f"| protocol `D3_EVALUATION_PROTOCOL_V1.md` = freeze manifest = runner pin = run manifest | PASS (`{s['inputs']['protocol_sha256']}`) |")
    a(f"| `raw_results.jsonl` = RUN.sha256 | PASS (`{s['inputs']['raw_results_sha256']}`) |")
    a(f"| `run_manifest.json` = RUN.sha256 | PASS (`{s['inputs']['run_manifest_sha256']}`) |")
    a("| status COMPLETED, valid_experimental_run, 35 expected / 35 completed | PASS |")
    a(f"| raw records | PASS ({s['integrity']['questions']}/35 valid JSON lines; IDs D3_Q01→D3_Q35 in order; no duplicate or missing ID) |")
    a("| question text, category and gold snapshot = frozen dataset | PASS (35/35) |")
    a(f"| RAG questions / expected MCP tool needs | PASS ({s['integrity']['rag_questions']} / {s['integrity']['expected_mcp_tool_needs']}) |")
    a("")
    a("Overall: **PASS**. The scorer aborts before computing anything if any check fails.")
    a("")
    a("## 3. Official Metrics")
    a("")
    a("| Block | Metric | Result |")
    a("|---|---|---|")
    a(f"| Agency | Exact Capability Match | {ecm['correct']}/{ecm['total']} ({_pct(ecm['value'])}) |")
    a(f"| Agency | Tool Accuracy | {ta['correct']}/{ta['total']} ({_pct(ta['value'])}) |")
    a(f"| Retrieval | Hit@3 | {rt['hit_at_3']['hits']}/{rt['hit_at_3']['total']} ({_pct(rt['hit_at_3']['value'])}) |")
    a(f"| Retrieval | Recall@3 (macro) | {rt['macro_recall_at_3']['value']:.3f} ({_pct(rt['macro_recall_at_3']['value'])}) |")
    a(f"| Retrieval | MRR | {rt['mrr']['value']:.3f} |")
    a("")
    a("Retrieval metrics use the oracle retrieval captured in the run (query = gold `rag.information_need`, top-3 of the "
      "frozen retriever) against the gold chunks, over the 20 RAG questions. Unrounded values are in "
      "`deterministic_scores_v1.json`.")
    a("")
    a("## 4. Exact Capability Match by Category")
    a("")
    a("Breakdown of ECM (not a separate primary metric).")
    a("")
    a("| Category | ECM |")
    a("|---|---|")
    for cat, v in s["category_breakdown"]["exact_capability_match"].items():
        a(f"| {cat} | {v['correct']}/{v['total']} ({_pct(v['value'])}) |")
    a("")
    a("## 5. Tool Accuracy Breakdown")
    a("")
    a("Informative breakdown of Tool Accuracy (not separate primary metrics).")
    a("")
    a("| Server | Correct expected-tool selections |")
    a("|---|---|")
    for server in SERVERS:
        b = ta["breakdown"][server]
        a(f"| {server.capitalize()} | {b['correct']}/{b['total']} ({_pct(b['value'])}) |")
    a(f"| **Total** | **{ta['correct']}/{ta['total']} ({_pct(ta['value'])})** |")
    a("")
    a("## 6. Retrieval Per Question")
    a("")
    a("| ID | Gold chunks | Gold retrieved | First gold rank | Hit@3 | Recall@3 | RR | Oracle top-3 (chunk_id, cosine distance) |")
    a("|---|---|---|---|---|---|---|---|")
    for q in s["per_question"]:
        r = q["retrieval"]
        if not r["included"]:
            continue
        top = "<br>".join(f"{e['rank']}. `{e['chunk_id']}` ({e['cosine_distance']:.3f})"
                          if isinstance(e["cosine_distance"], (int, float)) else f"{e['rank']}. `{e['chunk_id']}`"
                          for e in r["oracle_top3"]) or "(oracle failed)"
        a(f"| {q['id']} | {len(set(r['gold_chunks']))} | {len(r['gold_retrieved'])} | {r['first_gold_rank'] or '—'} | "
          f"{r['hit_at_3']} | {r['recall_at_3']:.3f} | {r['reciprocal_rank']:.3f} | {top} |")
    a("")
    a("Cosine distances are shown for diagnosis only; they are not a D3 metric.")
    a("")
    imperfect = s["error_analysis"]["retrieval_imperfect"]
    a("Retrieval cases with Hit@3 = 0, Recall@3 < 1 or RR < 1:")
    a("")
    if imperfect:
        a("| ID | Gold chunks | Oracle top-3 | Hit@3 | Recall@3 | RR |")
        a("|---|---|---|---|---|---|")
        for row in imperfect:
            a(f"| {row['id']} | {', '.join('`' + c + '`' for c in row['gold_chunks'])} | "
              f"{', '.join('`' + c + '`' for c in row['retrieved_chunk_ids']) or '(oracle failed)'} | "
              f"{row['hit_at_3']} | {row['recall_at_3']:.3f} | {row['reciprocal_rank']:.3f} |")
    else:
        a("None.")
    a("")
    a("## 7. Agency Errors")
    a("")
    a("Questions with ECM = 0. Observations are mechanical comparisons of the plan with the gold, not causal explanations.")
    a("")
    errors = s["error_analysis"]["agency_errors"]
    if errors:
        a("| ID | Category | Gold | Predicted | Planner tool calls | Observation |")
        a("|---|---|---|---|---|---|")
        for e in errors:
            a(f"| {e['id']} | {e['category']} | {_caps(e['gold_capabilities'])} | {_caps(e['predicted_capabilities'])} | "
              f"{_calls(e['planner_tool_calls'])} | {'; '.join(e['observations'])} |")
    else:
        a("None.")
    a("")
    a("## 8. Tool Selection Errors")
    a("")
    a("Expected-tool selections that were missing or different (Tool Accuracy = 0 for that need).")
    a("")
    terrors = s["error_analysis"]["tool_selection_errors"]
    if terrors:
        a("| ID | Category | Server | Expected tool | Selected tool | Observation |")
        a("|---|---|---|---|---|---|")
        for e in terrors:
            a(f"| {e['id']} | {e['category']} | {e['server']} | {e['expected_tool']} | {e['selected_tool'] or '—'} | "
              f"{e['observation']} |")
    else:
        a("None.")
    a("")
    a("## 9. Descriptive Execution Outcomes")
    a("")
    a("**NOT AN OFFICIAL METRIC.** Descriptive counts of what happened during the run. They do not change ECM or Tool "
      "Accuracy: a correctly selected tool that failed to execute still counts as a correct selection.")
    a("")
    a("| Outcome | Count |")
    a("|---|---|")
    a(f"| Final answers produced | {d['final_answer_produced']} |")
    no_ids = f" ({', '.join(d['no_final_answer_ids'])})" if d["no_final_answer_ids"] else ""
    a(f"| Questions with no final answer | {d['no_final_answer']}{no_ids} |")
    a(f"| Planner failures | {d['planner_failures']} |")
    for server in SERVERS:
        t = d["tool_execution"][server]
        failed = f" ({', '.join(t['failed_ids'])})" if t["failed_ids"] else ""
        a(f"| {server.capitalize()} calls planned / executed / succeeded / failed | "
          f"{t['planned']} / {t['executed']} / {t['succeeded']} / {t['failed']}{failed} |")
    a(f"| Oracle retrieval errors | {len(d['oracle_retrieval_errors'])} |")
    a("")
    a("Errors by stage:")
    a("")
    if d["errors_by_stage"]:
        a("| Stage | Count | IDs |")
        a("|---|---|---|")
        for stage, n in d["errors_by_stage"].items():
            a(f"| {stage} | {n} | {', '.join(d['error_ids_by_stage'][stage])} |")
    else:
        a("None.")
    a("")
    a("## 10. Interpretation Boundaries")
    a("")
    for line in [
        "**Exact Capability Match** measures capability selection by the planner (RAG / Weather / Places), all-or-nothing per question.",
        "**Tool Accuracy** measures only the selected tool name for each of the 40 gold needs. Tool arguments are not scored "
        "(they are listed in Section 7 for qualitative analysis), and an extra call on a non-gold server is penalised only by ECM.",
        "**Hit@3 / Recall@3 / MRR** measure the frozen retriever given the gold information need (oracle retrieval), not the "
        "planner's `rag_query`; `actual_retrieval` is not used by these metrics.",
        "A **tool execution failure** does not change Tool Accuracy; execution outcomes are descriptive only (Section 9).",
        "**LLM-as-Judge** (Correctness, Faithfulness/Groundedness, Relevance) has not been run; no answer-quality claim follows from this report.",
        "One run is one observation (live Weather/Places data, LLM planner); the numbers describe this run.",
    ]:
        a(f"- {line}")
    a("")
    a("## 11. Next Step")
    a("")
    a("Freeze the judge configuration (a model different from and more capable than llama3.2:3b, fixed version and "
      "temperature, the prompt and the rubric of protocol Section 10) and run the LLM-as-Judge for Correctness, "
      "Faithfulness/Groundedness and Relevance on this run's raw results.")
    a("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_outputs(run_dir: Path, scores: dict[str, Any], overwrite: bool) -> dict[str, str]:
    existing = [name for name in DERIVED if (run_dir / name).exists()]
    if existing and not overwrite:
        raise ScoringError(f"derived scoring files already exist: {existing} (use --overwrite-derived explicitly)")
    for name in existing:  # only derived files, never raw results
        (run_dir / name).unlink()
    (run_dir / SCORES_JSON).write_text(dumps(scores), encoding="utf-8", newline="\n")
    (run_dir / REPORT_MD).write_text(render_report(scores), encoding="utf-8", newline="\n")
    hashes = {name: frozen.sha256_file(run_dir / name) for name in (SCORES_JSON, REPORT_MD)}
    (run_dir / SCORES_SHA).write_text("".join(f"{h}  {n}\n" for n, h in hashes.items()), encoding="utf-8", newline="\n")
    return hashes


def run_label(run_dir: Path) -> str:
    try:
        return run_dir.resolve().relative_to(frozen.REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return run_dir.name


def main(argv: list[str] | None = None, cfg: frozen.RunnerConfig | None = None) -> int:
    cfg = cfg or frozen.RunnerConfig()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="D3 V1 deterministic scorer (no models, no network).")
    parser.add_argument("--run-dir", type=Path, help="the official run directory to score (required)")
    parser.add_argument("--validate-only", action="store_true", help="check integrity and exit without writing")
    parser.add_argument("--overwrite-derived", action="store_true", help="replace existing derived scoring files")
    args = parser.parse_args(argv)
    if args.run_dir is None:
        completed = []
        if cfg.runs_dir.is_dir():
            for d in sorted(cfg.runs_dir.iterdir()):
                try:
                    if json.loads((d / MANIFEST).read_text(encoding="utf-8")).get("status") == "COMPLETED":
                        completed.append(d.name)
                except (OSError, ValueError):
                    pass
        print(f"ERROR: --run-dir is required (COMPLETED runs found: {completed or 'none'}); nothing scored",
              file=sys.stderr)
        return 2
    try:
        validated = validate_run(args.run_dir, cfg)
        if args.validate_only:
            print(f"RUN {validated['manifest']['run_id']}: INTEGRITY PASS; READY TO SCORE (nothing written)")
            return 0
        scores = score(validated, run_label(args.run_dir))
        hashes = write_outputs(args.run_dir, scores, args.overwrite_derived)
    except ScoringError as exc:
        print(f"SCORING ABORTED: {exc}", file=sys.stderr)
        return 2
    o = scores["official_metrics"]
    print(f"RUN {scores['run_id']} SCORED")
    print(f"  ECM {o['exact_capability_match']['correct']}/35  TA {o['tool_accuracy']['correct']}/40  "
          f"Hit@3 {o['retrieval']['hit_at_3']['hits']}/20  Recall@3 {o['retrieval']['macro_recall_at_3']['value']:.6f}  "
          f"MRR {o['retrieval']['mrr']['value']:.6f}")
    for name, digest in hashes.items():
        print(f"  {digest}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

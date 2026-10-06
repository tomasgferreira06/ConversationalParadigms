"""D3 V1 official evaluation runner: collects RAW results of the Coimbra Expert Agent (no scoring).

    uv run python d3/evaluation/run_d3_evaluation.py                  # validate only (default)
    uv run python d3/evaluation/run_d3_evaluation.py --validate-only  # same
    uv run python d3/evaluation/run_d3_evaluation.py --execute --confirm-frozen-v1   # the official run

Validate-only loads the frozen dataset, checks its schema, balance and hashes and the protocol hash,
prints a summary and exits: no model, embedding, vector store, MCP server or network is touched, and
nothing is written. The official run (both flags required) follows D3_EVALUATION_PROTOCOL_V1.md:
one sequential pass over D3_Q01..D3_Q35 with the Coimbra Expert loaded once, an isolated oracle
retrieval per RAG question after its end-to-end answer, and raw results written to
d3/evaluation/runs/<run_id>/. This script computes NO metric and runs NO judge.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from importlib import metadata
from pathlib import Path
from typing import Any, Callable

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parents[1]

DATASET_JSON = "d3_evaluation_set_v1.json"
DATASET_MD = "D3_EVALUATION_SET_V1.md"
DATASET_AUDIT = "D3_EVALUATION_SET_AUDIT_V1.md"
DATASET_SHA = "D3_EVALUATION_SET_V1.sha256"
PROTOCOL = "D3_EVALUATION_PROTOCOL_V1.md"
PROTOCOL_SHA = "D3_EVALUATION_PROTOCOL_V1.sha256"

# Frozen values (dataset audit Section 14 and the protocol freeze); a mismatch aborts the run.
PINNED_DATASET_SHA256 = {
    DATASET_MD: "d15356000ee620fe6341396d7699653638a34685411f8ab0df37f5e7710f1f01",
    DATASET_JSON: "3cef162c592e3e18c18103a970b926f949dc9e1115f971bfea3c5595674e0528",
    DATASET_AUDIT: "7171c366cd15c8e0b7bc13c5baa20c31ab94b28d062a84d9486cfc3cf805afaa",
}
PINNED_PROTOCOL_SHA256 = "1dd9974ee18e000326b58e30902d8bf3810155d23961ea0c62677f464e6a1e59"

CATEGORIES = ("RAG", "WEATHER", "PLACES", "RAG+WEATHER", "RAG+PLACES", "WEATHER+PLACES", "RAG+WEATHER+PLACES")
EXPECTED_IDS = tuple(f"D3_Q{n:02d}" for n in range(1, 36))
TOOLS = {"weather": ("get_current_weather", "get_weather_forecast"),
         "places": ("search_place", "get_distance_between_places")}
PACKAGES = ("langchain-core", "langchain-ollama", "langchain-chroma", "langchain-huggingface", "chromadb",
            "sentence-transformers", "transformers", "torch", "mcp", "ollama", "httpx", "nltk")

EXIT_OK, EXIT_INVALID, EXIT_ABORTED = 0, 2, 3


class ValidationError(RuntimeError):
    """The frozen inputs are not exactly what the protocol requires; nothing is executed."""


@dataclass(frozen=True)
class RunnerConfig:
    eval_dir: Path = EVAL_DIR
    runs_dir: Path = EVAL_DIR / "runs"
    pinned_dataset: dict[str, str] | None = field(default_factory=lambda: dict(PINNED_DATASET_SHA256))
    pinned_protocol: str | None = PINNED_PROTOCOL_SHA256

    def path(self, name: str) -> Path:
        return self.eval_dir / name


# ---------------------------------------------------------------------------
# Validation (standard library only)
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_sha_manifest(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValidationError(f"freeze manifest missing: {path.name}")
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, _, name = line.strip().partition("  ")
            entries[name.lstrip("*")] = digest
    return entries


def verify_hashes(cfg: RunnerConfig, manifest_name: str, names: tuple[str, ...],
                  pinned: dict[str, str] | None) -> dict[str, str]:
    manifest = read_sha_manifest(cfg.path(manifest_name))
    if set(manifest) != set(names):
        raise ValidationError(f"{manifest_name} must list exactly {list(names)}, lists {sorted(manifest)}")
    actual = {}
    for name in names:
        path = cfg.path(name)
        if not path.is_file():
            raise ValidationError(f"frozen file missing: {name}")
        actual[name] = sha256_file(path)
        if actual[name] != manifest[name]:
            raise ValidationError(f"hash mismatch for {name}: {actual[name]} != {manifest_name}")
        if pinned is not None and pinned.get(name) != actual[name]:
            raise ValidationError(f"hash of {name} differs from the value pinned in the runner")
    return actual


def _check_item(item: dict[str, Any]) -> None:
    qid = item.get("id")
    for key in ("id", "category", "question", "gold_capabilities", "rag", "weather", "places"):
        if key not in item:
            raise ValidationError(f"{qid}: missing field {key!r}")
    if item["category"] not in CATEGORIES:
        raise ValidationError(f"{qid}: unknown category {item['category']!r}")
    if not isinstance(item["question"], str) or not item["question"].strip():
        raise ValidationError(f"{qid}: empty question")
    caps = item["gold_capabilities"]
    if not isinstance(caps, dict) or set(caps) != {"rag", "weather", "places"} or \
            not all(isinstance(v, bool) for v in caps.values()):
        raise ValidationError(f"{qid}: gold_capabilities must be three booleans")
    parts = set(item["category"].split("+"))
    if {k for k, v in caps.items() if v} != {p.lower() for p in parts}:
        raise ValidationError(f"{qid}: gold_capabilities do not match category {item['category']}")
    rag = item["rag"]
    if rag.get("required") is not caps["rag"]:
        raise ValidationError(f"{qid}: rag.required inconsistent with gold_capabilities")
    if caps["rag"]:
        if not isinstance(rag.get("information_need"), str) or not rag["information_need"].strip():
            raise ValidationError(f"{qid}: RAG question without information_need")
        if not rag.get("gold_chunks"):
            raise ValidationError(f"{qid}: RAG question without gold_chunks")
    for server in ("weather", "places"):
        block = item[server]
        if block.get("required") is not caps[server]:
            raise ValidationError(f"{qid}: {server}.required inconsistent with gold_capabilities")
        tool = block.get("expected_tool")
        if caps[server] and tool not in TOOLS[server]:
            raise ValidationError(f"{qid}: invalid expected {server} tool {tool!r}")
        if not caps[server] and tool is not None:
            raise ValidationError(f"{qid}: expected {server} tool set although not required")


def validate(cfg: RunnerConfig) -> dict[str, Any]:
    """All pre-execution checks of protocol Section 13. Returns the dataset and a summary."""

    dataset_path = cfg.path(DATASET_JSON)
    if not dataset_path.is_file():
        raise ValidationError(f"dataset missing: {dataset_path}")
    try:
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"dataset is not valid JSON: {exc}") from None
    items = dataset.get("items") if isinstance(dataset, dict) else None
    if not isinstance(items, list):
        raise ValidationError("dataset has no 'items' list")
    ids = [item.get("id") if isinstance(item, dict) else None for item in items]
    duplicates = sorted({i for i in ids if ids.count(i) > 1}, key=str)
    if duplicates:
        raise ValidationError(f"duplicated IDs: {duplicates}")
    if len(items) != 35:
        raise ValidationError(f"expected 35 questions, found {len(items)}")
    if ids != list(EXPECTED_IDS):
        raise ValidationError("IDs must be exactly D3_Q01..D3_Q35, each once and in order")
    for item in items:
        _check_item(item)
    by_category = collections.Counter(item["category"] for item in items)
    if any(by_category[c] != 5 for c in CATEGORIES):
        raise ValidationError(f"category balance must be 5 each, got {dict(by_category)}")
    caps = {k: sum(item["gold_capabilities"][k] for item in items) for k in ("rag", "weather", "places")}
    if caps != {"rag": 20, "weather": 20, "places": 20}:
        raise ValidationError(f"capability counts must be 20/20/20, got {caps}")
    dataset_hashes = verify_hashes(cfg, DATASET_SHA, (DATASET_MD, DATASET_JSON, DATASET_AUDIT), cfg.pinned_dataset)
    protocol_hashes = verify_hashes(cfg, PROTOCOL_SHA, (PROTOCOL,),
                                    None if cfg.pinned_protocol is None else {PROTOCOL: cfg.pinned_protocol})
    tools = collections.Counter(item[s]["expected_tool"] for item in items for s in ("weather", "places")
                                if item[s]["expected_tool"])
    return {
        "dataset": dataset,
        "items": items,
        "dataset_hashes": dataset_hashes,
        "protocol_sha256": protocol_hashes[PROTOCOL],
        "summary": {"questions": len(items), "by_category": {c: by_category[c] for c in CATEGORIES},
                    "capabilities": caps, "expected_tools": dict(tools),
                    "rag_questions_for_oracle_retrieval": caps["rag"]},
    }


# ---------------------------------------------------------------------------
# One question (data collection only)
# ---------------------------------------------------------------------------


def now_local() -> datetime:
    return datetime.now().astimezone()


def gold_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    return {"capabilities": dict(item["gold_capabilities"]),
            "expected_weather_tool": item["weather"]["expected_tool"],
            "expected_places_tool": item["places"]["expected_tool"]}


def run_question(system, item: dict[str, Any], clock: Callable[[], datetime] = now_local) -> dict[str, Any]:
    """End-to-end answer first, then (RAG questions only) the isolated oracle retrieval."""

    import evaluation_trace as et

    system.tracer.start()
    started, t0 = clock(), time.monotonic()
    final_answer, failure = None, None
    try:
        final_answer = system.expert.respond(item["question"])
    except Exception as exc:  # a per-question failure is a result, never retried
        failure = exc
    trace = system.tracer.finish()  # the end-to-end trace is closed before the oracle retrieval

    rag_gold = item["gold_capabilities"]["rag"]
    oracle = {"required_by_gold": rag_gold, "query": item["rag"]["information_need"] if rag_gold else None,
              "top3": None, "error": None}
    if rag_gold:
        try:
            oracle["top3"] = et.retrieval_records(system.oracle_retrieve(oracle["query"]))
        except Exception as exc:
            oracle["error"] = et.error_info(exc)
    finished = clock()

    planner = trace.planner or {"success": None, "use_rag": None, "rag_query": None, "tool_calls": None,
                                "error": None}
    actual = trace.actual_retrieval or {"performed": False, "query": None, "capture_method": None,
                                        "top3": None, "error": None}
    evidence = trace.generation_evidence or {"capture_method": None, "rag_context": None, "weather_data": None,
                                             "places_data": None, "generator_user_message": None}
    error = None
    if failure is not None:
        error = {"stage": et.error_stage(trace), **et.error_info(failure)}
    return {
        "id": item["id"],
        "category": item["category"],
        "question": item["question"],
        "timing": {"started_at": started.isoformat(), "finished_at": finished.isoformat(),
                   "duration_seconds": round(time.monotonic() - t0, 3)},
        "gold_snapshot": gold_snapshot(item),
        "planner": planner,
        "actual_retrieval": actual,
        "oracle_retrieval": oracle,
        "weather": et.capability_block(trace, "weather"),
        "places": et.capability_block(trace, "places"),
        "generation_evidence": evidence,
        "final_answer": final_answer,
        "error": error,
    }


# ---------------------------------------------------------------------------
# The real system (loaded only by --execute, after validation)
# ---------------------------------------------------------------------------


def tree_digest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    digest = hashlib.sha256()
    for file_path in files:
        relative = file_path.name if path.is_file() else file_path.relative_to(path).as_posix()
        digest.update(f"{relative}\0{sha256_file(file_path)}\n".encode("utf-8"))
    return {"sha256": digest.hexdigest(), "files": len(files), "bytes": sum(p.stat().st_size for p in files)}


class RealSystem:
    """FROZEN_V2 RAGAgent on a runtime copy of the frozen store + the Coimbra Expert (one MCP session each)."""

    def __init__(self):
        for path in (REPO_ROOT / "integration", EVAL_DIR):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        import dataclasses

        import agents  # noqa: E402  (sets up the D2 / D3 import paths)
        import evaluation_trace

        self.rag_pipeline = agents.rag_pipeline
        self.planner_module = sys.modules["planner"]
        base = self.rag_pipeline.BASELINE
        if base is not self.rag_pipeline.FROZEN_V2:
            raise RuntimeError("the active RAG configuration is not FROZEN_V2")
        self.original_store = base.store_dir
        self.store_before = tree_digest(self.original_store)
        self._tmp = tempfile.TemporaryDirectory(prefix="d3_eval_store_", ignore_cleanup_errors=True)
        self.runtime_store = Path(self._tmp.name) / "chroma_frozen_v2_runtime_copy"
        shutil.copytree(self.original_store, self.runtime_store)  # the original store is never opened
        self.config = dataclasses.replace(base, store_dir=self.runtime_store)
        self.expert = None
        try:
            self.rag = agents.RAGAgent.load(self.config)  # checks Ollama, loads embeddings, opens the copy
            self.collection_count = self.rag.store._collection.count()
            self.expert = agents.expert_agent.load_expert(self.rag)  # starts both MCP servers once
        except BaseException:
            self._tmp.cleanup()
            raise
        self.tracer = evaluation_trace.install_tracing(self.expert, self.rag_pipeline)

    def oracle_retrieve(self, query: str):
        # Raw retriever on the raw store: never routed through the agent or its tracing proxies.
        return self.rag_pipeline.retrieve(self.rag.store, query, k=self.config.top_k)

    def describe(self) -> dict[str, Any]:
        cfg = self.config
        mcp = {}
        for name, folder, service in (("weather_mcp", "weather_mcp", "weather_service.py"),
                                      ("places_mcp", "places_mcp", "places_service.py")):
            root = REPO_ROOT / "d3" / folder
            mcp[name] = {"server_path": str(root / "server.py"), "server_sha256": sha256_file(root / "server.py"),
                         "service_sha256": sha256_file(root / service), "version": None}
        return {
            "run_date": now_local().date().isoformat(),
            "planner": {"model": self.planner_module.PLANNER_MODEL,
                        "temperature": self.planner_module.PLANNER_TEMPERATURE},
            "generator": {"model": cfg.llm_model, "temperature": cfg.llm_temperature},
            "retrieval": {"embedding_model": cfg.embedding_model, "query_prompt_name": cfg.query_prompt_name,
                          "top_k": cfg.top_k, "collection_name": cfg.collection_name,
                          "distance_space": cfg.distance_space, "indexed_roles": sorted(cfg.indexed_roles)},
            "vector_store": {"original_path": str(self.original_store), "runtime_copy_path": str(self.runtime_store),
                             "original_digest_before": self.store_before, "collection_count": self.collection_count},
            "mcp": mcp,
            "ollama_model_digests": ollama_digests((self.planner_module.PLANNER_MODEL, cfg.llm_model)),
        }

    def close(self) -> dict[str, Any]:
        try:
            if self.expert is not None:
                self.expert.close()
        finally:
            self.rag = self.expert = None
            self._tmp.cleanup()
        return {"vector_store_original_digest_after": tree_digest(self.original_store)}


def ollama_digests(models) -> dict[str, str | None] | None:
    try:
        import ollama

        listed = {m.model: getattr(m, "digest", None) for m in ollama.list().models}
    except Exception:
        return None
    return {model: listed.get(model) for model in models}


# ---------------------------------------------------------------------------
# Run bookkeeping
# ---------------------------------------------------------------------------


def git_state() -> dict[str, Any]:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True,
                                  check=True, timeout=30).stdout.strip()
        except Exception:
            return None

    status = git("status", "--porcelain")
    return {"commit": git("rev-parse", "HEAD"), "dirty": None if status is None else bool(status)}


def package_versions() -> dict[str, str | None]:
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def write_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def execute(cfg: RunnerConfig, validation: dict[str, Any], system_factory: Callable[[], Any] = RealSystem,
            clock: Callable[[], datetime] = now_local) -> int:
    started = clock()
    run_id = started.strftime("%Y%m%dT%H%M%S%z")
    run_dir = cfg.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)  # never overwrite a run
    manifest_path, raw_path = run_dir / "run_manifest.json", run_dir / "raw_results.jsonl"
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "status": "RUNNING",
        "valid_experimental_run": None,
        "started_at": started.isoformat(),
        "finished_at": None,
        "abort_stage": None,
        "abort_error": None,
        "protocol": {"path": str(cfg.path(PROTOCOL)), "sha256": validation["protocol_sha256"]},
        "dataset": {"path": str(cfg.path(DATASET_JSON)), "sha256": validation["dataset_hashes"]},
        "git": git_state(),
        "python": {"version": sys.version, "implementation": platform.python_implementation(),
                   "platform": platform.platform()},
        "packages": package_versions(),
        "system": None,
        "question_count_expected": len(validation["items"]),
        "question_count_completed": 0,
        "close_error": None,
    }
    raw_path.touch()
    write_json(manifest_path, manifest)

    def abort(stage: str, exc: BaseException) -> int:
        manifest.update(status="ABORTED", abort_stage=stage, finished_at=clock().isoformat(),
                        abort_error={"type": type(exc).__name__, "message": str(exc)},
                        valid_experimental_run=False)
        write_json(manifest_path, manifest)
        print(f"RUN ABORTED ({stage}): {type(exc).__name__}: {exc}\n{run_dir}", file=sys.stderr)
        return EXIT_ABORTED

    try:
        system = system_factory()
    except BaseException as exc:  # Ollama / embeddings / Chroma / MCP did not start: invalid run
        return abort("startup", exc)
    try:
        manifest["system"] = system.describe()
        write_json(manifest_path, manifest)
        with raw_path.open("a", encoding="utf-8", newline="\n") as out:
            for item in validation["items"]:  # D3_Q01 -> D3_Q35, in order, once
                record = run_question(system, item, clock)
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                out.flush()
                os.fsync(out.fileno())
                manifest["question_count_completed"] += 1
                write_json(manifest_path, manifest)
                print(f"[{item['id']}] done" + (f" (error at {record['error']['stage']})" if record["error"] else ""),
                      flush=True)
    except BaseException as exc:  # crash or interruption mid-run: keep the partial run as ABORTED
        try:
            system.close()
        except BaseException as close_exc:
            manifest["close_error"] = {"type": type(close_exc).__name__, "message": str(close_exc)}
        return abort("during_run", exc)
    try:
        manifest["system"].update(system.close())
    except Exception as exc:  # all answers are recorded; the close failure is reported, not hidden
        manifest["close_error"] = {"type": type(exc).__name__, "message": str(exc)}
    manifest.update(status="COMPLETED", valid_experimental_run=True, finished_at=clock().isoformat())
    write_json(manifest_path, manifest)
    (run_dir / "RUN.sha256").write_text(
        f"{sha256_file(raw_path)}  {raw_path.name}\n{sha256_file(manifest_path)}  {manifest_path.name}\n",
        encoding="utf-8", newline="\n")
    print(f"RUN COMPLETED: {run_dir}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_summary(validation: dict[str, Any]) -> None:
    s = validation["summary"]
    print("D3 V1 VALIDATION OK")
    print(f"  questions: {s['questions']} (D3_Q01..D3_Q35)")
    print("  categories: " + ", ".join(f"{c}={n}" for c, n in s["by_category"].items()))
    print(f"  capabilities: RAG={s['capabilities']['rag']} Weather={s['capabilities']['weather']} "
          f"Places={s['capabilities']['places']}")
    print("  expected tools: " + ", ".join(f"{t}={n}" for t, n in sorted(s["expected_tools"].items())))
    for name, digest in validation["dataset_hashes"].items():
        print(f"  {name}: {digest} OK")
    print(f"  {PROTOCOL}: {validation['protocol_sha256']} OK")


def main(argv: list[str] | None = None, cfg: RunnerConfig | None = None,
         system_factory: Callable[[], Any] = RealSystem, clock: Callable[[], datetime] = now_local) -> int:
    cfg = cfg or RunnerConfig()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="D3 V1 raw-results runner (no scoring).")
    parser.add_argument("--validate-only", action="store_true", help="validate and exit (the default)")
    parser.add_argument("--execute", action="store_true", help="run the official evaluation")
    parser.add_argument("--confirm-frozen-v1", action="store_true", help="required together with --execute")
    args = parser.parse_args(argv)
    if args.validate_only and args.execute:
        print("ERROR: --validate-only and --execute are mutually exclusive; nothing was started", file=sys.stderr)
        return EXIT_INVALID
    if args.execute and not args.confirm_frozen_v1:
        print("ERROR: --execute requires --confirm-frozen-v1; nothing was started", file=sys.stderr)
        return EXIT_INVALID
    try:
        validation = validate(cfg)
    except ValidationError as exc:
        print(f"VALIDATION FAILED: {exc}; nothing was started", file=sys.stderr)
        return EXIT_INVALID
    print_summary(validation)
    if not args.execute:
        print("  validate-only: nothing executed; no model, store, MCP server or network used; nothing written")
        return EXIT_OK
    print("STARTING OFFICIAL D3 V1 RUN")
    return execute(cfg, validation, system_factory, clock)


if __name__ == "__main__":
    sys.exit(main())

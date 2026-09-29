"""Train the D1/D2 routing classifier (supervised binary text classification).

The classifier never answers the user: it only decides which agent handles a
message, "eliza_rude" (D1, ELIZA_RUDE chit-chat) or "rag" (D2, Coimbra Tourism
Expert RAG). Following the course Text Classification worksheet: one 70/30
stratified split (random_state=42), the vectorizer fitted on the training part
only, and two small experiments evaluated on the same held-out test set:

    A) CountVectorizer + MultinomialNB
    B) TfidfVectorizer + LogisticRegression

The selected model's vectorizer and classifier are saved with joblib for the
router, and every number of the run is written to results/classifier_results.json.

Usage:
    uv run python integration/train_classifier.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable

import joblib
import sklearn
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB


INTEGRATION_DIR = Path(__file__).resolve().parent
DATASET_PATH = INTEGRATION_DIR / "data" / "routing_dataset.csv"
MODELS_DIR = INTEGRATION_DIR / "models"
VECTORIZER_FILE = "router_vectorizer.joblib"
CLASSIFIER_FILE = "router_classifier.joblib"
RESULTS_PATH = INTEGRATION_DIR / "results" / "classifier_results.json"

LABELS = ("eliza_rude", "rag")
TEST_SIZE = 0.3
RANDOM_STATE = 42
# Largest tolerated class imbalance (share of the majority class).
MAX_MAJORITY_SHARE = 0.55


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


def load_dataset(path: Path = DATASET_PATH) -> tuple[list[str], list[str]]:
    """(texts, labels) from a UTF-8 text,label CSV; a decoding error is not silenced."""

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["text", "label"]:
            raise ValueError(f"{path.name}: expected header text,label, got {reader.fieldnames}")
        rows = list(reader)
    return [row["text"] for row in rows], [row["label"] for row in rows]


def normalize(text: str) -> str:
    """Lowercase, no accents, no punctuation, single spaces: for near-duplicate checks."""

    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def validate_dataset(texts: list[str], labels: list[str]) -> dict[str, Any]:
    """Raise ValueError on any quality problem; return the dataset statistics."""

    if not texts or len(texts) != len(labels):
        raise ValueError("invalid routing dataset: empty, or texts and labels differ in length")
    problems = []
    seen_exact: dict[str, int] = {}
    seen_norm: dict[str, int] = {}
    for line, (text, label) in enumerate(zip(texts, labels), start=2):  # line 1 is the header
        if not text.strip():
            problems.append(f"line {line}: empty text")
        elif text != text.strip():
            problems.append(f"line {line}: leading/trailing whitespace")
        if label not in LABELS:
            problems.append(f"line {line}: invalid label {label!r}")
        key = normalize(text)
        if text in seen_exact:
            problems.append(f"line {line}: exact duplicate of line {seen_exact[text]}")
        elif key in seen_norm:
            problems.append(f"line {line}: duplicate of line {seen_norm[key]} after normalisation")
        seen_exact.setdefault(text, line)
        seen_norm.setdefault(key, line)
    counts = {label: labels.count(label) for label in LABELS}
    if max(counts.values()) / len(labels) > MAX_MAJORITY_SHARE:
        problems.append(f"classes are not balanced: {counts}")
    if problems:
        raise ValueError("invalid routing dataset:\n  " + "\n  ".join(problems))

    lengths = [len(text.split()) for text in texts]
    tokens = [token for text in texts for token in normalize(text).split()]
    return {
        "total": len(texts),
        "per_class": counts,
        "words_per_utterance": {"min": min(lengths), "max": max(lengths), "mean": round(sum(lengths) / len(lengths), 2)},
        "tokens": len(tokens),
        "distinct_tokens": len(set(tokens)),
        "type_token_ratio": round(len(set(tokens)) / len(tokens), 3),
        "mentions_coimbra": {
            label: sum("coimbra" in normalize(t).split() for t, l in zip(texts, labels) if l == label) for label in LABELS
        },
    }


def split(texts: list[str], labels: list[str]):
    """The worksheet split: 70% train / 30% test, random_state=42, stratified by label."""

    return train_test_split(texts, labels, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=labels)


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


def model_a() -> tuple[CountVectorizer, MultinomialNB]:
    return CountVectorizer(ngram_range=(1, 2), strip_accents="unicode"), MultinomialNB()


def model_b() -> tuple[TfidfVectorizer, LogisticRegression]:
    return (
        TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode"),
        LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
    )


EXPERIMENTS: dict[str, tuple[str, Callable[[], tuple[Any, Any]]]] = {
    "A": ("CountVectorizer + MultinomialNB", model_a),
    "B": ("TfidfVectorizer + LogisticRegression", model_b),
}


def train(vectorizer, classifier, X_train: list[str], y_train: list[str]):
    """Fit the vectorizer on the training texts ONLY, then the classifier."""

    classifier.fit(vectorizer.fit_transform(X_train), y_train)
    return vectorizer, classifier


def evaluate(vectorizer, classifier, X_test: list[str], y_test: list[str]) -> dict[str, Any]:
    """Test-set metrics; the vectorizer is only applied (transform), never refitted."""

    features = vectorizer.transform(X_test)
    predicted = classifier.predict(features)
    probabilities = classifier.predict_proba(features)
    classes = list(classifier.classes_)
    report = classification_report(y_test, predicted, labels=list(LABELS), output_dict=True, zero_division=0)
    errors = [
        {
            "text": text,
            "true": true,
            "predicted": pred,
            "probabilities": {label: round(float(proba[classes.index(label)]), 4) for label in LABELS},
        }
        for text, true, pred, proba in zip(X_test, y_test, predicted, probabilities)
        if true != pred
    ]
    return {
        "accuracy": accuracy_score(y_test, predicted),
        "per_class": {label: {m: report[label][m] for m in ("precision", "recall", "f1-score", "support")} for label in LABELS},
        "macro_avg": {m: report["macro avg"][m] for m in ("precision", "recall", "f1-score")},
        "report_text": classification_report(y_test, predicted, labels=list(LABELS), digits=3, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, predicted, labels=list(LABELS)).tolist(),
        "errors": errors,
    }


def class_gap(metrics: dict[str, Any]) -> float:
    """Difference between the two per-class F1 scores (0 = perfectly balanced)."""

    f1 = [metrics["per_class"][label]["f1-score"] for label in LABELS]
    return abs(f1[0] - f1[1])


def select_model(results: dict[str, dict[str, Any]], test_size: int) -> tuple[str, str]:
    """(model key, reason). The rule is fixed before looking at the results.

    Higher macro F1 wins, unless the two differ by less than one test example
    (1 / test_size): then the more balanced model (smaller per-class F1 gap)
    wins, and on a further tie the simpler baseline A.
    """

    margin = 1 / test_size
    a, b = results["A"], results["B"]
    diff = b["macro_avg"]["f1-score"] - a["macro_avg"]["f1-score"]
    if abs(diff) >= margin:
        key = "B" if diff > 0 else "A"
        return key, f"higher macro F1 by {abs(diff):.3f} (>= one test example, {margin:.3f})"
    gap_a, gap_b = class_gap(a), class_gap(b)
    if abs(gap_a - gap_b) >= margin:
        key = "A" if gap_a < gap_b else "B"
        return key, (f"macro F1 within one test example ({abs(diff):.3f} < {margin:.3f}); "
                     f"more balanced per-class F1 (gap {min(gap_a, gap_b):.3f} vs {max(gap_a, gap_b):.3f})")
    return "A", (f"macro F1 ({abs(diff):.3f}) and per-class balance within one test example; "
                 "the simpler baseline A is kept")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_router(vectorizer, classifier, models_dir: Path = MODELS_DIR) -> tuple[Path, Path]:
    models_dir.mkdir(parents=True, exist_ok=True)
    vectorizer_path, classifier_path = models_dir / VECTORIZER_FILE, models_dir / CLASSIFIER_FILE
    joblib.dump(vectorizer, vectorizer_path)
    joblib.dump(classifier, classifier_path)
    return vectorizer_path, classifier_path


def load_router(models_dir: Path = MODELS_DIR):
    return joblib.load(models_dir / VECTORIZER_FILE), joblib.load(models_dir / CLASSIFIER_FILE)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(dataset_path: Path = DATASET_PATH, models_dir: Path = MODELS_DIR, results_path: Path = RESULTS_PATH) -> dict[str, Any]:
    texts, labels = load_dataset(dataset_path)
    stats = validate_dataset(texts, labels)
    X_train, X_test, y_train, y_test = split(texts, labels)

    results = {}
    for key, (name, factory) in EXPERIMENTS.items():
        vectorizer, classifier = train(*factory(), X_train, y_train)
        results[key] = {"name": name, **evaluate(vectorizer, classifier, X_test, y_test)}
    selected, reason = select_model(results, len(X_test))

    # Refit the selected experiment exactly as evaluated (same train split) and persist it.
    vectorizer, classifier = train(*EXPERIMENTS[selected][1](), X_train, y_train)
    save_router(vectorizer, classifier, models_dir)

    output = {
        "dataset": {"path": dataset_path.name, "sha256": sha256(dataset_path), **stats},
        "split": {
            "test_size": TEST_SIZE, "random_state": RANDOM_STATE, "stratify": True,
            "train": len(X_train), "test": len(X_test),
            "train_per_class": {label: y_train.count(label) for label in LABELS},
            "test_per_class": {label: y_test.count(label) for label in LABELS},
            "vocabulary_size_selected": len(vectorizer.vocabulary_),
        },
        "experiments": results,
        "selected": {"model": selected, "name": EXPERIMENTS[selected][0], "reason": reason},
        "artifacts": {
            "vectorizer": VECTORIZER_FILE, "classifier": CLASSIFIER_FILE,
            "classes": list(classifier.classes_), "scikit_learn": sklearn.__version__,
        },
    }
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def print_summary(output: dict[str, Any]) -> None:
    data, split_info = output["dataset"], output["split"]
    print(f"Dataset: {data['total']} utterances {data['per_class']}; "
          f"{data['words_per_utterance']} words; {data['distinct_tokens']} distinct tokens")
    print(f"Split: train {split_info['train']} {split_info['train_per_class']}, "
          f"test {split_info['test']} {split_info['test_per_class']}")
    for key, result in output["experiments"].items():
        print(f"\n=== Model {key}: {result['name']} ===")
        print(f"Accuracy: {result['accuracy']:.3f}  Macro F1: {result['macro_avg']['f1-score']:.3f}")
        print(result["report_text"])
        print(f"Confusion matrix (rows = true, columns = predicted; order {list(LABELS)}):")
        for label, row in zip(LABELS, result["confusion_matrix"]):
            print(f"  {label:<11} {row}")
        print(f"Errors ({len(result['errors'])}):")
        for error in result["errors"]:
            print(f"  [{error['true']} -> {error['predicted']}] {error['text']}  {error['probabilities']}")
    selected = output["selected"]
    print(f"\nSelected: Model {selected['model']} ({selected['name']}): {selected['reason']}")
    print(f"Saved: {MODELS_DIR / VECTORIZER_FILE}\n       {MODELS_DIR / CLASSIFIER_FILE}\n       {RESULTS_PATH}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        output = run()
    except ValueError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    print_summary(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

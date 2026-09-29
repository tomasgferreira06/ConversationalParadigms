"""D1/D2 message router: the trained text classifier, loaded once.

The router never answers the user; it only says which agent should:
"eliza_rude" (D1, ELIZA_RUDE) or "rag" (D2, Coimbra Expert RAG). A message
goes to the RAG when P(rag) >= RAG_THRESHOLD (0.45), otherwise to ELIZA_RUDE.

Usage:
    router = AgentRouter.load()
    router.predict_proba("Que museus existem em Coimbra?")  # {"eliza_rude": ..., "rag": ...}
    router.classify("Que museus existem em Coimbra?")       # "rag"
"""

from __future__ import annotations

from pathlib import Path

from train_classifier import CLASSIFIER_FILE, LABELS, MODELS_DIR, VECTORIZER_FILE, load_router

# Borderline messages (P(rag) between 0.45 and 0.50) go to the RAG instead of ELIZA_RUDE.
RAG_THRESHOLD = 0.45


class RouterError(RuntimeError):
    """The router artifacts are missing or invalid; the message says what to do."""


class AgentRouter:
    def __init__(self, vectorizer, classifier):
        classes = [str(label) for label in classifier.classes_]
        if sorted(classes) != sorted(LABELS):
            raise RouterError(f"[router] classifier classes {classes} are not {list(LABELS)}")
        self.vectorizer = vectorizer
        self.classifier = classifier
        self._classes = classes

    @classmethod
    def load(cls, models_dir: Path = MODELS_DIR) -> "AgentRouter":
        missing = [name for name in (VECTORIZER_FILE, CLASSIFIER_FILE) if not (models_dir / name).exists()]
        if missing:
            raise RouterError(
                f"[router] missing {', '.join(missing)} in {models_dir}. "
                "Run: uv run python integration/train_classifier.py"
            )
        return cls(*load_router(models_dir))

    def predict_proba(self, text: str) -> dict[str, float]:
        """Probability of each label, in LABELS order."""

        proba = self.classifier.predict_proba(self.vectorizer.transform([text]))[0]
        return {label: float(proba[self._classes.index(label)]) for label in LABELS}

    def classify(self, text: str) -> str:
        """"rag" if P(rag) >= RAG_THRESHOLD, otherwise "eliza_rude"."""

        return "rag" if self.predict_proba(text)["rag"] >= RAG_THRESHOLD else "eliza_rude"

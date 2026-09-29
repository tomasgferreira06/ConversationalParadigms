"""Training pipeline of the D1/D2 router: split, no leakage, both experiments, metrics, persistence."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

INTEGRATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INTEGRATION_DIR))

import train_classifier as tc  # noqa: E402


class SplitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts, cls.labels = tc.load_dataset()

    def test_split_is_70_30(self):
        X_train, X_test, _, _ = tc.split(self.texts, self.labels)
        self.assertEqual((len(X_train), len(X_test)), (140, 60))

    def test_split_is_reproducible(self):
        self.assertEqual(tc.split(self.texts, self.labels), tc.split(self.texts, self.labels))

    def test_split_is_stratified(self):
        _, _, y_train, y_test = tc.split(self.texts, self.labels)
        self.assertEqual((y_train.count("eliza_rude"), y_train.count("rag")), (70, 70))
        self.assertEqual((y_test.count("eliza_rude"), y_test.count("rag")), (30, 30))

    def test_train_and_test_are_disjoint(self):
        X_train, X_test, _, _ = tc.split(self.texts, self.labels)
        self.assertFalse(set(X_train) & set(X_test))
        self.assertEqual(sorted(X_train + X_test), sorted(self.texts))


class NoLeakageTests(unittest.TestCase):
    X_train = ["olá tudo bem", "estou cansado", "que museus visitar", "onde fica a sé"]
    y_train = ["eliza_rude", "eliza_rude", "rag", "rag"]
    X_test = ["biblioteca joanina horário", "sinto-me triste"]
    y_test = ["rag", "eliza_rude"]

    def test_vectorizer_is_fitted_on_training_texts_only(self):
        for key, (_name, factory) in tc.EXPERIMENTS.items():
            with self.subTest(model=key):
                vectorizer, classifier = factory()
                with mock.patch.object(vectorizer, "fit_transform", wraps=vectorizer.fit_transform) as fit:
                    tc.train(vectorizer, classifier, self.X_train, self.y_train)
                fit.assert_called_once_with(self.X_train)
                with mock.patch.object(vectorizer, "fit", side_effect=AssertionError("refit")), \
                        mock.patch.object(vectorizer, "fit_transform", side_effect=AssertionError("refit")):
                    tc.evaluate(vectorizer, classifier, self.X_test, self.y_test)

    def test_test_only_words_are_not_in_the_vocabulary(self):
        for key, (_name, factory) in tc.EXPERIMENTS.items():
            with self.subTest(model=key):
                vectorizer, _ = tc.train(*factory(), self.X_train, self.y_train)
                self.assertNotIn("joanina", vectorizer.vocabulary_)
                self.assertNotIn("triste", vectorizer.vocabulary_)
                reference = type(vectorizer)(**vectorizer.get_params()).fit(self.X_train)
                self.assertEqual(vectorizer.vocabulary_, reference.vocabulary_)

    def test_real_split_vocabulary_comes_from_training_part(self):
        texts, labels = tc.load_dataset()
        X_train, _, y_train, _ = tc.split(texts, labels)
        vectorizer, _ = tc.train(*tc.model_b(), X_train, y_train)
        reference = TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode").fit(X_train)
        self.assertEqual(vectorizer.vocabulary_, reference.vocabulary_)


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        texts, labels = tc.load_dataset()
        cls.X_train, cls.X_test, cls.y_train, cls.y_test = tc.split(texts, labels)

    def test_experiment_configurations(self):
        vec_a, clf_a = tc.model_a()
        self.assertIsInstance(vec_a, CountVectorizer)
        self.assertIsInstance(clf_a, MultinomialNB)
        self.assertEqual((vec_a.ngram_range, vec_a.strip_accents), ((1, 2), "unicode"))
        vec_b, clf_b = tc.model_b()
        self.assertIsInstance(vec_b, TfidfVectorizer)
        self.assertIsInstance(clf_b, LogisticRegression)
        self.assertEqual((vec_b.ngram_range, vec_b.strip_accents), ((1, 2), "unicode"))
        self.assertEqual((clf_b.max_iter, clf_b.random_state), (1000, 42))

    def test_both_models_train_and_predict_both_classes(self):
        for key, (_name, factory) in tc.EXPERIMENTS.items():
            with self.subTest(model=key):
                vectorizer, classifier = tc.train(*factory(), self.X_train, self.y_train)
                self.assertEqual(list(classifier.classes_), list(tc.LABELS))
                predicted = set(classifier.predict(vectorizer.transform(self.X_test)))
                self.assertEqual(predicted, set(tc.LABELS))

    def test_metrics_are_computed(self):
        for key, (_name, factory) in tc.EXPERIMENTS.items():
            with self.subTest(model=key):
                metrics = tc.evaluate(*tc.train(*factory(), self.X_train, self.y_train), self.X_test, self.y_test)
                self.assertTrue(0 <= metrics["accuracy"] <= 1)
                for label in tc.LABELS:
                    self.assertEqual(set(metrics["per_class"][label]), {"precision", "recall", "f1-score", "support"})
                    self.assertEqual(metrics["per_class"][label]["support"], 30)
                self.assertEqual(set(metrics["macro_avg"]), {"precision", "recall", "f1-score"})
                matrix = np.array(metrics["confusion_matrix"])
                self.assertEqual(matrix.shape, (2, 2))
                self.assertEqual(matrix.sum(), 60)
                self.assertEqual(len(metrics["errors"]), matrix.sum() - np.trace(matrix))
                self.assertAlmostEqual(metrics["accuracy"], np.trace(matrix) / 60)
                for error in metrics["errors"]:
                    self.assertNotEqual(error["true"], error["predicted"])
                    self.assertAlmostEqual(sum(error["probabilities"].values()), 1, places=3)


class SelectionTests(unittest.TestCase):
    @staticmethod
    def result(macro_f1, f1_eliza, f1_rag):
        return {"macro_avg": {"f1-score": macro_f1},
                "per_class": {"eliza_rude": {"f1-score": f1_eliza}, "rag": {"f1-score": f1_rag}}}

    def test_clearly_better_macro_f1_wins(self):
        key, _ = tc.select_model({"A": self.result(0.90, 0.9, 0.9), "B": self.result(0.95, 0.95, 0.95)}, 60)
        self.assertEqual(key, "B")
        key, _ = tc.select_model({"A": self.result(0.95, 0.95, 0.95), "B": self.result(0.90, 0.9, 0.9)}, 60)
        self.assertEqual(key, "A")

    def test_near_tie_prefers_the_more_balanced_model(self):
        key, reason = tc.select_model({"A": self.result(0.910, 0.95, 0.87), "B": self.result(0.915, 0.92, 0.91)}, 60)
        self.assertEqual(key, "B")
        self.assertIn("balanced", reason)

    def test_full_tie_keeps_the_simpler_baseline(self):
        key, _ = tc.select_model({"A": self.result(0.95, 0.95, 0.95), "B": self.result(0.955, 0.95, 0.96)}, 60)
        self.assertEqual(key, "A")


class PersistenceTests(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        texts, labels = tc.load_dataset()
        X_train, X_test, y_train, _ = tc.split(texts, labels)
        vectorizer, classifier = tc.train(*tc.model_b(), X_train, y_train)
        with tempfile.TemporaryDirectory() as tmp:
            tc.save_router(vectorizer, classifier, Path(tmp))
            loaded_vec, loaded_clf = tc.load_router(Path(tmp))
        np.testing.assert_allclose(
            loaded_clf.predict_proba(loaded_vec.transform(X_test)),
            classifier.predict_proba(vectorizer.transform(X_test)),
        )

    def test_run_is_deterministic_and_writes_artifacts(self):
        outputs = []
        with tempfile.TemporaryDirectory() as tmp:
            for attempt in ("1", "2"):
                models, results = Path(tmp) / attempt / "models", Path(tmp) / attempt / "results.json"
                tc.run(models_dir=models, results_path=results)
                self.assertTrue((models / tc.VECTORIZER_FILE).exists())
                self.assertTrue((models / tc.CLASSIFIER_FILE).exists())
                outputs.append(json.loads(results.read_text(encoding="utf-8")))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0]["split"]["train"], 140)

    def test_committed_results_match_a_fresh_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh = tc.run(models_dir=Path(tmp) / "models", results_path=Path(tmp) / "results.json")
        committed = json.loads(tc.RESULTS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(json.dumps(fresh)), committed)


if __name__ == "__main__":
    unittest.main()

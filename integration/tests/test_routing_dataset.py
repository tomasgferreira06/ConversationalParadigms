"""Quality checks of the D1/D2 routing dataset (integration/data/routing_dataset.csv)."""

import sys
import unicodedata
import unittest
from pathlib import Path

INTEGRATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INTEGRATION_DIR))

import train_classifier as tc  # noqa: E402


class RoutingDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts, cls.labels = tc.load_dataset()

    def test_not_empty_and_expected_size(self):
        self.assertEqual(len(self.texts), 200)
        self.assertEqual(len(self.texts), len(self.labels))

    def test_labels_are_valid(self):
        self.assertEqual(set(self.labels), set(tc.LABELS))

    def test_classes_are_balanced(self):
        self.assertEqual(self.labels.count("eliza_rude"), 100)
        self.assertEqual(self.labels.count("rag"), 100)

    def test_no_exact_duplicates(self):
        self.assertEqual(len(self.texts), len(set(self.texts)))

    def test_no_duplicates_after_normalisation(self):
        normalised = [tc.normalize(t) for t in self.texts]
        self.assertEqual(len(normalised), len(set(normalised)))

    def test_valid_utf8_strings(self):
        tc.DATASET_PATH.read_bytes().decode("utf-8", errors="strict")
        for text in self.texts:
            self.assertEqual(text, text.strip())
            self.assertTrue(text)
            self.assertNotIn("�", text)  # no replacement characters from a bad decode
            self.assertEqual(text, unicodedata.normalize("NFC", text))
            self.assertFalse(any(unicodedata.category(ch) == "Cc" for ch in text), text)

    def test_validation_passes_and_reports_statistics(self):
        stats = tc.validate_dataset(self.texts, self.labels)
        self.assertEqual(stats["total"], 200)
        self.assertEqual(stats["per_class"], {"eliza_rude": 100, "rag": 100})
        # Lexical and length diversity: not a list of minimal variations.
        self.assertGreater(stats["distinct_tokens"], 400)
        self.assertEqual(stats["words_per_utterance"]["min"], 1)
        self.assertGreaterEqual(stats["words_per_utterance"]["max"], 12)

    def test_rag_class_is_not_just_the_word_coimbra(self):
        rag = [t for t, l in zip(self.texts, self.labels) if l == "rag"]
        with_coimbra = [t for t in rag if "coimbra" in tc.normalize(t).split()]
        self.assertLess(len(with_coimbra), len(rag) / 2)

    def test_documented_boundary_cases(self):
        labelled = dict(zip(self.texts, self.labels))
        expected = {
            "Preciso de um restaurante em Coimbra.": "rag",
            "Preciso de férias.": "eliza_rude",
            "Quero sair à noite em Coimbra.": "rag",
            "Quero sair daqui.": "eliza_rude",
            "O meu trabalho está a correr mal.": "eliza_rude",
            "Que trabalho realizou Nicolau Chanterene em Coimbra?": "rag",
            "Estou cansado de andar.": "eliza_rude",
            "Onde posso fazer uma caminhada em Coimbra?": "rag",
            "Quero comer.": "eliza_rude",
        }
        for text, label in expected.items():
            self.assertEqual(labelled[text], label, text)


class ValidationRejectsBadDataTests(unittest.TestCase):
    def assert_rejected(self, texts, labels, fragment):
        with self.assertRaises(ValueError) as ctx:
            tc.validate_dataset(texts, labels)
        self.assertIn(fragment, str(ctx.exception))

    def test_empty_dataset(self):
        self.assert_rejected([], [], "empty")

    def test_invalid_label(self):
        self.assert_rejected(["Olá", "Que museus há?"], ["eliza_rude", "eliza"], "invalid label")

    def test_empty_text(self):
        self.assert_rejected(["  ", "Que museus há?"], ["eliza_rude", "rag"], "empty text")

    def test_exact_duplicate(self):
        self.assert_rejected(["Olá", "Olá", "Museus?", "Sé?"], ["eliza_rude", "eliza_rude", "rag", "rag"],
                             "exact duplicate")

    def test_normalised_duplicate(self):
        self.assert_rejected(["Olá!", "ola", "Museus?", "Sé?"], ["eliza_rude", "eliza_rude", "rag", "rag"],
                             "after normalisation")

    def test_unbalanced_classes(self):
        self.assert_rejected(["a", "b", "c", "d"], ["rag", "rag", "rag", "eliza_rude"], "not balanced")


if __name__ == "__main__":
    unittest.main()

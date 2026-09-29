"""The trained D1/D2 router on new utterances (none of them is in the routing dataset)."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

INTEGRATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INTEGRATION_DIR))

import router as rt  # noqa: E402
import train_classifier as tc  # noqa: E402


RAG_CASES = {
    "monuments": "Quais são os monumentos mais importantes de Coimbra?",
    "museum": "Recomendas algum museu de arte sacra?",
    "university": "A Universidade de Coimbra tem visitas guiadas?",
    "fado": "Onde é que posso assistir a um espetáculo de fado esta noite?",
    "restaurant": "Conheces um restaurante com leitão perto do centro?",
    "nightlife": "Quais são os bares mais animados perto da Praça da República?",
    "sport": "Há clubes onde se possa jogar ténis ou nadar?",
    "history": "Qual a história do Mosteiro de Santa Cruz?",
    "heritage": "Em que século foi construída a Sé Velha?",
}
ELIZA_RUDE_CASES = {
    "greeting": "Olá, boa tarde.",
    "feeling": "Hoje sinto-me mesmo em baixo.",
    "personal problem": "Tenho imensos problemas e ninguém me ajuda.",
    "work": "O meu chefe obriga-me a fazer horas extra.",
    "family": "A minha família não me apoia.",
    "thanks": "Obrigadíssimo, foste útil.",
    "about the agent": "Tu és a assistente mais mal-educada que conheço.",
}
BOUNDARY_CASES = {
    "Preciso de um sítio para jantar perto da Sé Velha.": "rag",
    "Preciso de uma pausa.": "eliza_rude",
    "Onde se pode sair à noite na Baixa?": "rag",
    "Quero ir para casa.": "eliza_rude",
    "Estou cansado de estudar.": "eliza_rude",
}


class TrainedRouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = rt.AgentRouter.load()

    def test_cases_are_new_utterances(self):
        texts, _ = tc.load_dataset()
        known = {tc.normalize(t) for t in texts}
        for text in [*RAG_CASES.values(), *ELIZA_RUDE_CASES.values(), *BOUNDARY_CASES]:
            self.assertNotIn(tc.normalize(text), known, text)

    def test_selected_model_is_tfidf_logistic_regression(self):
        self.assertIsInstance(self.router.vectorizer, TfidfVectorizer)
        self.assertIsInstance(self.router.classifier, LogisticRegression)

    def test_tourism_questions_go_to_rag(self):
        for topic, text in RAG_CASES.items():
            with self.subTest(topic=topic):
                self.assertEqual(self.router.classify(text), "rag", text)

    def test_chit_chat_goes_to_eliza_rude(self):
        for topic, text in ELIZA_RUDE_CASES.items():
            with self.subTest(topic=topic):
                self.assertEqual(self.router.classify(text), "eliza_rude", text)

    def test_boundary_cases(self):
        for text, label in BOUNDARY_CASES.items():
            with self.subTest(text=text):
                self.assertEqual(self.router.classify(text), label)

    def test_predict_proba_is_a_distribution_over_both_labels(self):
        probabilities = self.router.predict_proba("Que museus existem em Coimbra?")
        self.assertEqual(list(probabilities), list(tc.LABELS))
        self.assertAlmostEqual(sum(probabilities.values()), 1.0)
        self.assertGreater(probabilities["rag"], probabilities["eliza_rude"])

    def test_classify_is_the_argmax_of_predict_proba(self):
        for text in [*RAG_CASES.values(), *ELIZA_RUDE_CASES.values(), *BOUNDARY_CASES]:
            probabilities = self.router.predict_proba(text)
            self.assertEqual(self.router.classify(text), max(probabilities, key=probabilities.get))

    def test_persisted_model_equals_a_fresh_training_run(self):
        texts, labels = tc.load_dataset()
        X_train, X_test, y_train, _ = tc.split(texts, labels)
        vectorizer, classifier = tc.train(*tc.model_b(), X_train, y_train)
        fresh = rt.AgentRouter(vectorizer, classifier)
        for text in X_test:
            self.assertEqual(self.router.predict_proba(text), fresh.predict_proba(text))


class RouterLoadingTests(unittest.TestCase):
    def test_artifacts_are_loaded_once(self):
        with mock.patch.object(tc.joblib, "load", wraps=tc.joblib.load) as load:
            router = rt.AgentRouter.load()
            for _ in range(5):
                router.classify("Olá")
        self.assertEqual(load.call_count, 2)  # vectorizer + classifier, at construction only

    def test_missing_artifacts_say_how_to_train(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(rt.RouterError) as ctx:
                rt.AgentRouter.load(Path(tmp))
        self.assertIn("train_classifier.py", str(ctx.exception))

    def test_classifier_with_other_classes_is_rejected(self):
        classifier = mock.Mock(classes_=["eliza", "rag"])
        with self.assertRaises(rt.RouterError):
            rt.AgentRouter(mock.Mock(), classifier)


if __name__ == "__main__":
    unittest.main()

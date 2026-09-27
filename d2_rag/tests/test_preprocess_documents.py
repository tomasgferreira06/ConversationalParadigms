import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from preprocess_documents import (  # noqa: E402
    detect_route_heading,
    normalize_whitespace,
    reconstruct_paragraphs,
    remove_web_navigation_noise,
    repair_spaced_letter_artifacts,
)


class NormalizeWhitespaceTests(unittest.TestCase):
    def test_normalizes_horizontal_whitespace_and_preserves_diacritics_and_dates(self):
        source = "  Câmara\tMunicipal   de Coimbra  \nEm 11 de Agosto de 1919. "

        result = normalize_whitespace(source)

        self.assertEqual(
            result,
            "Câmara Municipal de Coimbra\nEm 11 de Agosto de 1919.",
        )

    def test_preserves_coordinates_and_minus_sign(self):
        source = "coordenadas :   40.211234,  -8.428968"

        result = normalize_whitespace(source)

        self.assertEqual(result, "coordenadas : 40.211234, -8.428968")


class WebNoiseTests(unittest.TestCase):
    def test_removes_known_navigation_tokens_without_removing_content(self):
        source = (
            "keyboard_arrow_leftO que visitar\n"
            "Biblioteca Joanina\n"
            "BILHETES format_list_bulleted\n"
            "chevron_left chevron_right\n"
            "Conteúdo sobre D. João V.\n"
            "fiber_manual_recordfiber_manual_record"
        )

        result = remove_web_navigation_noise(source)

        self.assertIn("O que visitar", result)
        self.assertIn("Biblioteca Joanina", result)
        self.assertIn("Conteúdo sobre D. João V.", result)
        self.assertNotIn("keyboard_arrow_left", result)
        self.assertNotIn("format_list_bulleted", result)
        self.assertNotIn("chevron_", result)
        self.assertNotIn("fiber_manual_record", result)

    def test_separates_words_when_noise_token_is_embedded(self):
        source = "temperatura,BILHETESos livros podem aguardarformat_list_bulletedpor catalogação"

        result = remove_web_navigation_noise(source)

        self.assertEqual(
            result,
            "temperatura, os livros podem aguardar por catalogação",
        )

    def test_removes_browser_print_header_and_footer(self):
        source = (
            "25/09/26, 23:12 UnivCoimbra - UCTour\n"
            "Biblioteca Joanina\n"
            "https://visit.uc.pt/engine.io/space-list/joanina 2/6"
        )

        result = remove_web_navigation_noise(source)

        self.assertEqual(result, "Biblioteca Joanina")


class ParagraphTests(unittest.TestCase):
    def test_joins_wrapped_lines_but_preserves_paragraph_breaks(self):
        lines = [
            "A Biblioteca Joanina é o expoente máximo do Barroco",
            "português e conserva milhares de volumes.",
            "",
            "Piso Nobre",
            "",
            "O andar nobre é composto por três salas.",
        ]

        result = reconstruct_paragraphs(lines)

        self.assertEqual(
            result,
            [
                "A Biblioteca Joanina é o expoente máximo do Barroco português e conserva milhares de volumes.",
                "",
                "Piso Nobre",
                "",
                "O andar nobre é composto por três salas.",
            ],
        )


class SpacedLetterTests(unittest.TestCase):
    def test_repairs_long_lowercase_letter_sequence(self):
        source = "c a s a d a l i v r a r i a"

        self.assertEqual(repair_spaced_letter_artifacts(source), "casa da livraria")

    def test_repairs_reviewed_multiword_spaced_phrase(self):
        source = "O b r a í m p a r e r e c o n h e c i d a internacionalmente"

        self.assertEqual(
            repair_spaced_letter_artifacts(source),
            "Obra ímpar e reconhecida internacionalmente",
        )

    def test_does_not_join_short_or_uppercase_initial_sequences(self):
        self.assertEqual(repair_spaced_letter_artifacts("D. Afonso I"), "D. Afonso I")
        self.assertEqual(repair_spaced_letter_artifacts("a b c"), "a b c")


class RouteHeadingTests(unittest.TestCase):
    def test_detects_numbered_uppercase_route_heading(self):
        self.assertEqual(
            detect_route_heading("2. IGREJA DE SANTA CRUZ | PANTEÃO NACIONAL"),
            (2, "IGREJA DE SANTA CRUZ | PANTEÃO NACIONAL"),
        )

    def test_does_not_promote_dates_or_regular_sentences(self):
        self.assertIsNone(detect_route_heading("Em 2017, a praça foi requalificada."))
        self.assertIsNone(detect_route_heading("2. Esta frase não é um título"))


if __name__ == "__main__":
    unittest.main()

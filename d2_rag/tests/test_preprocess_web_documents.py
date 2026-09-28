"""Tests for the web corpus preprocessing (offline: synthetic HTML + local raw)."""

import hashlib
import json
import re
import sys
import unicodedata
import unittest
from pathlib import Path
from unittest import mock

from bs4 import BeautifulSoup


D2_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(D2_ROOT / "scripts"))

import preprocess_web_documents as web  # noqa: E402


TAXONOMY = {
    "university_heritage", "city_history", "built_heritage", "museums_collections",
    "culture_traditions", "gastronomy", "landscape_gardens", "visitor_orientation",
    "transport_access",
}


def _widget(kind: str, inner: str, classes: str = "") -> str:
    return f'<div class="elementor-widget {classes}" data-widget_type="{kind}.default">{inner}</div>'


def _page(*widgets: str) -> str:
    """Minimal copy of the site template: header/menu twice, page, footer."""

    menu = "<ul><li><a href='/o-que-visitar/'>O que visitar</a></li><li>Guia prático</li></ul>"
    return (
        "<html lang='pt-PT'><body>"
        f"<div data-elementor-type='wp-post' class='header'>Agentes e profissionais {menu}{menu}</div>"
        f"<div data-elementor-type='wp-page'>{''.join(widgets)}</div>"
        "<div data-elementor-type='wp-post' class='footer'>© Página oficial Turismo de Coimbra "
        "turismo@cm-coimbra.pt</div>"
        "</body></html>"
    )


def _flip(title: str, description: str) -> str:
    return _widget(
        "flip-box",
        "<div class='elementor-flip-box__front'>"
        f"<h1 class='elementor-flip-box__layer__title'>{title}</h1>"
        f"<div class='elementor-flip-box__layer__description'>{description}</div></div>"
        "<div class='elementor-flip-box__back'><a href='x'>Preparar visita</a></div>",
    )


def _render(html: str, document_id: str = "web-test") -> str:
    blocks, _stats = web.html_to_blocks(html, document_id)
    record = {"document_id": document_id, "title": "Teste", "source_organization": "Org",
              "url": "https://visitecoimbra.pt/teste/", "language": "pt"}
    return web.render_markdown(record, blocks)


class TemplateAndWidgetTests(unittest.TestCase):
    def test_menus_and_footer_are_removed(self):
        markdown = _render(_page(_widget("text-editor", "<p>A Sé Velha data do século XII.</p>")))
        self.assertIn("A Sé Velha data do século XII.", markdown)
        for residue in ("O que visitar", "Guia prático", "Agentes e profissionais", "turismo@cm-coimbra.pt", "© Página"):
            self.assertNotIn(residue, markdown)

    def test_desktop_hidden_duplicate_is_skipped(self):
        quote = "<h1>“Uma citação de destaque”</h1>"
        markdown = _render(_page(
            _widget("heading", quote, "elementor-hidden-desktop"),
            _widget("heading", quote, "elementor-hidden-mobile"),
        ))
        self.assertEqual(markdown.count("Uma citação de destaque"), 1)

    def test_pull_quote_and_long_heading_become_quotes_not_headings(self):
        long_heading = "Visitar Coimbra e explorar o Mosteiro de Santa Cruz é reviver a história fundadora de Portugal"
        markdown = _render(_page(
            _widget("heading", "<h1>\"O Fado de Coimbra é único\"</h1>"),
            _widget("heading", f"<h1>{long_heading}</h1>"),
            _widget("heading", "<h1>Doces a não perder</h1>"),
            _widget("text-editor", "<p>Texto.</p>"),
        ))
        self.assertIn('> "O Fado de Coimbra é único"', markdown)
        self.assertIn(f"> {long_heading}", markdown)
        self.assertIn("## Doces a não perder", markdown)
        self.assertNotIn("# \"O Fado", markdown)

    def test_empty_player_section_and_media_are_removed(self):
        markdown = _render(_page(
            _widget("text-editor", "<p>Conteúdo cultural.</p>"),
            _widget("heading", "<h1>Playlist Canção de Coimbra</h1>"),
            _widget("html", "<iframe src='https://player'></iframe>"),
            _widget("image", "<img alt='foto'>"),
            _widget("button", "<a href='x'>Saber mais</a>"),
        ))
        self.assertIn("Conteúdo cultural.", markdown)
        for gone in ("Playlist", "Saber mais", "foto", "iframe"):
            self.assertNotIn(gone, markdown)

    def test_flip_box_keeps_entity_with_its_text_and_drops_back_layer(self):
        markdown = _render(_page(_flip("Sé Nova de Coimbra", "Tornou-se a catedral de Coimbra em 1772.")))
        self.assertIn("## Sé Nova de Coimbra\n\nTornou-se a catedral de Coimbra em 1772.", markdown)
        self.assertNotIn("Preparar visita", markdown)

    def test_accordion_nesting_and_untitled_items(self):
        accordion = _widget(
            "nested-accordion",
            "<details><summary>Igrejas e Mosteiros</summary><div>"
            + _flip("Sé Velha de Coimbra", "Construída no século XII.")
            + "</div></details>",
        )
        untitled = _widget(
            "nested-accordion",
            "<details><summary></summary><div>"
            + _widget("heading", "<h1>Projeto MIKVEH</h1>")
            + _widget("text-editor", "<p>Empreitada de conservação e restauro.</p>")
            + "</div></details>",
        )
        markdown = _render(_page(accordion, untitled))
        self.assertIn("## Igrejas e Mosteiros\n\n### Sé Velha de Coimbra\n\nConstruída no século XII.", markdown)
        self.assertIn("## Projeto MIKVEH", markdown)

    def test_heading_levels_never_skip(self):
        blocks = web._close_level_gaps([web.Block("heading", "A", 2), web.Block("heading", "B", 4)])
        self.assertEqual([b.level for b in blocks], [2, 3])

    def test_operational_sentence_removed_historical_dates_kept(self):
        markdown = _render(_page(_widget(
            "text-editor",
            "<p>A Casa-Museu foi inaugurada em Junho de 2018. Fundado em 1131, foi o mosteiro "
            "mais influente. O horário de abertura é à 2ª feira das 10h às 13h.</p>",
        )))
        self.assertIn("inaugurada em Junho de 2018.", markdown)
        self.assertIn("Fundado em 1131", markdown)
        self.assertNotIn("10h às 13h", markdown)

    def test_line_breaks_kept_for_lists_but_not_for_visual_wraps(self):
        markdown = _render(_page(
            _widget("text-editor", "<p>1. República Baco<br>2. República dos Kagados<br>3. Real República Prá-Kys-Tão<br>4. República Ay-Ó-Linda</p>"),
            _widget("text-editor", "<p>D. Sesnando está sepultado na<br>Sé Velha<br>de Coimbra.</p>"),
        ))
        self.assertIn("1. República Baco\n2. República dos Kagados\n3. Real República", markdown)
        self.assertIn("sepultado na Sé Velha de Coimbra.", markdown)

    def test_configured_section_is_dropped_until_next_heading(self):
        html = _page(
            _widget("heading", "<h1>Casas para ouvir</h1>"),
            _flip("Fado ao Centro", "Um espetáculo."),
            _widget("heading", "<h1>História</h1>"),
            _widget("text-editor", "<p>Texto histórico.</p>"),
        )
        with mock.patch.dict(web.DROP_SECTIONS, {"web-test": ["Casas para ouvir"]}):
            markdown = _render(html)
        self.assertNotIn("Fado ao Centro", markdown)
        self.assertIn("## História\n\nTexto histórico.", markdown)

    def test_card_list_document_renders_cards_as_one_list_in_source_order(self):
        html = _page(
            _widget("text-editor", "<p>Texto sobre bares.</p>"),
            _flip("BREW!", "Festival de cerveja artesanal"),
            _flip("Epicura", "Cerveja Artesanal"),
            _flip("Sem descrição", ""),
            _widget("text-editor", "<p>Depois.</p>"),
        )
        with mock.patch.object(web, "CARD_LIST_DOCUMENTS", {"web-test"}):
            markdown = _render(html)
        self.assertIn("Texto sobre bares.\n\n- BREW! — Festival de cerveja artesanal\n- Epicura — Cerveja Artesanal\n"
                      "- Sem descrição\n\nDepois.", markdown)
        self.assertNotIn("## BREW!", markdown)
        self.assertNotIn("Preparar visita", markdown)

    def test_directory_loop_grid_filters_form_and_price_tier(self):
        html = _page(
            _widget("nested-accordion", "<details><summary>Preço</summary><div>"
                    + _widget("taxonomy-filter", "<button>€</button><button>€€</button>") + "</div></details>"),
            _widget("loop-grid", "<div class='e-loop-item'>"
                    + _flip("A Taberna", "<strong>Tradicional Portuguesa | €€</strong><br>Um restaurante típico.")
                    + "</div>"),
            _widget("text-editor", "<p>Faça parte desta lista!</p>"),
            _widget("nested-accordion", "<details><summary>Clique aqui</summary><div>"
                    + _widget("form", "<input placeholder='Nome do Restaurante'>") + "</div></details>"),
        )
        with mock.patch.object(web, "CARD_LIST_DOCUMENTS", {"web-test"}):
            markdown = _render(html)
        self.assertIn("- A Taberna — Tradicional Portuguesa — Um restaurante típico.", markdown)
        for gone in ("€", "Preço", "Faça parte", "Clique aqui", "Nome do Restaurante"):
            self.assertNotIn(gone, markdown)

    def test_empty_accordion_item_does_not_adopt_following_content(self):
        blocks, _stats = web.html_to_blocks(_page(
            _widget("nested-accordion", "<details><summary>Filtros</summary><div>"
                    + _widget("form", "<input>") + "</div></details>"),
            _widget("text-editor", "<p>Conteúdo da página.</p>"),
        ), "web-test")
        self.assertEqual([(b.kind, b.text) for b in blocks], [("paragraph", "Conteúdo da página.")])

    def test_page_without_single_content_container_is_rejected(self):
        with self.assertRaises(ValueError):
            web.html_to_blocks("<html><body><p>sem container</p></body></html>", "web-test")


def _web_records():
    return [json.loads(l) for l in (D2_ROOT / "data" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip() and json.loads(l).get("source_type") == "web_page"]


def _processed(document_id: str) -> str:
    return (D2_ROOT / "data" / "processed" / "web" / f"{document_id}.md").read_text(encoding="utf-8")


class CorpusIntegrationTests(unittest.TestCase):
    """Checks on the real acquired pages (local raw snapshots, no network)."""

    def test_cancao_keeps_culture_and_fado_houses_and_drops_player(self):
        markdown = _processed("web-visitecoimbra-cancao-de-coimbra")
        self.assertIn("A guitarra portuguesa de Coimbra é um dos elementos mais icónicos", markdown)
        self.assertIn("> \"O Fado de Coimbra é uma expressão musical única no mundo.", markdown)
        # Fado houses: reviewed INCLUDE (WEB_CONTENT_CARD_FIX_REPORT.md).
        self.assertRegex(markdown, r"## Casas para ouvir a Canção de Coimbra\n\n- Fado ao Centro — Um espetáculo"
                                   r"[^\n]*\n- À Capella — Instalado[^\n]*\n- Café Santa Cruz — Um café centenário")
        for gone in ("Playlist", "Saber mais", "fadoaocentro.com", "acapella.com.pt"):
            self.assertNotIn(gone, markdown)

    def test_ceramica_keeps_reviewed_places_to_see_and_buy_pottery(self):
        markdown = _processed("web-visitecoimbra-ceramica-de-coimbra")
        self.assertIn("### Refeitro\n\nEspaço que combina gastronomia e olaria", markdown)
        self.assertIn("### Carlos Tomás\n\nArtesão renomado, com a sua galeria na Sé Velha", markdown)
        self.assertIn("### Lojas de artesanato da Baixa\n\nDiversos estabelecimentos", markdown)
        self.assertNotIn("wp-content", markdown)

    def test_still_excluded_cards_and_sections_stay_absent(self):
        # Navigation cards ("Ver também"), app promotion and event: EXCLUDE.
        estudantes = _processed("web-visitecoimbra-coimbra-dos-estudantes")
        for gone in ("Ver também", "Roteiro das Tradições Académicas"):
            self.assertNotIn(gone, estudantes)
        self.assertNotIn("APP - Exposição", _processed("web-visitecoimbra-heranca-judaica"))
        self.assertNotIn("Mostra de Doçaria", _processed("web-visitecoimbra-docaria-conventual-de-coimbra"))

    def test_beer_page_recovers_the_four_cards_once_in_order_without_back_layer(self):
        markdown = _processed("web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira")
        cards = ["BREW! — Festival de cerveja artesanal", "Epicura — Cerveja Artesanal",
                 "Portuguese Pedro — Cerveja", "Praxis — Cervejaria, Restaurante"]
        self.assertIn("\n".join(f"- {card}" for card in cards), markdown)
        for name in ("BREW!", "Epicura", "Portuguese Pedro", "Praxis"):
            self.assertEqual(markdown.count(name), 1, name)
        body = markdown.split("\n---\n", 1)[1]
        for gone in ("Saber mais", "http", "beerpraxis", "instagram", "## BREW!", "## Praxis"):
            self.assertNotIn(gone, body)
        # The narrative is kept, and the cards follow it.
        narrative = "Além das microcervejarias, a cidade conta com vários bares especializados em cerveja artesanal"
        self.assertIn("Coimbra tem uma forte ligação à cerveja, que remonta aos tempos medievais.", markdown)
        self.assertLess(markdown.index(narrative), markdown.index("- BREW!"))

    def test_new_pages_keep_their_entities_and_drop_directory_ui(self):
        night = _processed("web-visitecoimbra-coimbra-by-night")
        self.assertIn("## 10 locais imperdíveis para sair à noite em Coimbra\n\n- Quebra Costas — Situado nas famosas escadas", night)
        self.assertIn("## 6 rooftops a não perder\n\n- Bar do Hotel Oslo — ", night)
        self.assertEqual(night.count("\n- "), 19)
        restaurants = _processed("web-visitecoimbra-restauracao")
        self.assertEqual(restaurants.count("\n- "), 70)
        self.assertIn("- Cervejaria Praxis — Cervejaria — Descubra a 1ª microcervejeira artesanal portuguesa.", restaurants)
        for gone in ("€", "Tipo de Cozinha", "Preço", "Apagar filtro", "Faça parte", "Clique aqui", "Nome do Restaurante"):
            self.assertNotIn(gone, restaurants)
        sport = _processed("web-visitecoimbra-desporto")
        self.assertIn("- 1. Paddle no Rio Mondego — Explore o rio", sport)
        self.assertIn("- 10. Atletismo — ", sport)
        self.assertIn("A Associação Académica de Coimbra (AAC), fundada em 1887", sport)
        for markdown in (night, restaurants, sport):
            self.assertGreater(len(markdown.split("\n---\n", 1)[1].split()), 600)
            self.assertNotIn("Saber mais", markdown)

    def test_docaria_drops_event_and_keeps_sweets_with_their_names(self):
        markdown = _processed("web-visitecoimbra-docaria-conventual-de-coimbra")
        self.assertNotIn("Mostra de Doçaria", markdown)
        self.assertIn("## Doces a não perder", markdown)
        self.assertRegex(markdown, r"### Pastéis de Santa Clara\n\nOs Pastéis de Santa Clara são")

    def test_heranca_keeps_entities_and_preserves_source_wording_of_known_conflict(self):
        markdown = _processed("web-visitecoimbra-heranca-cultural-e-religiosa")
        self.assertIn("## Igrejas e Mosteiros", markdown)
        section = markdown.split("### Mosteiro de Santa Clara-a-Velha", 1)[1].split("###", 1)[0]
        self.assertIn("Fundado pela Rainha Santa Isabel", section)  # not corrected
        self.assertNotIn("Não sabe por onde começar", markdown)

    def test_museus_drops_hours_and_promotions_keeps_history(self):
        markdown = _processed("web-visitecoimbra-museus")
        self.assertNotIn("10h às 13h", markdown)
        self.assertIn("A Casa-Museu foi inaugurada em Junho de 2018.", markdown)
        self.assertIn("## Museu Nacional de Machado de Castro", markdown)
        for gone in ("Planeie a sua visita", "Ver experiências", "Tuk a Day", "Preparar visita"):
            self.assertNotIn(gone, markdown)

    def test_diacritics_and_historical_dates_are_preserved(self):
        markdown = _processed("web-visitecoimbra-pedro-e-ines")
        for text in ("Em 1355", "em 1357", "Inês de Castro", "D. Afonso IV", "“linda Inês"):
            self.assertIn(text, markdown)

    def test_no_template_residue_and_no_source_page_in_any_document(self):
        for record in _web_records():
            with self.subTest(document_id=record["document_id"]):
                body = _processed(record["document_id"]).split("\n---\n", 1)[1]
                for residue in ("Agentes e profissionais", "© Página oficial", "turismo@cm-coimbra.pt",
                                "Preparar visita", "Ver experiências", "source_page"):
                    self.assertNotIn(residue, body)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.records = _web_records()

    def test_web_records_are_complete_and_consistent(self):
        self.assertEqual(len(self.records), 27)
        required = ("document_id", "title", "source_organization", "url", "canonical_url", "language",
                    "primary_category", "source_type", "status", "acquired_at", "access_checked_at",
                    "content_hash", "local_raw_path", "processed_path", "decision_reason")
        for record in self.records:
            with self.subTest(document_id=record["document_id"]):
                for key in required:
                    self.assertTrue(record.get(key), key)
                self.assertRegex(record["document_id"], r"^web-visitecoimbra-[a-z0-9-]+$")
                self.assertEqual(record["status"], "accepted")
                self.assertIn(record["primary_category"], TAXONOMY)
                self.assertTrue(record["url"].startswith("https://visitecoimbra.pt/"))
        self.assertEqual(len({r["document_id"] for r in self.records}), len(self.records))
        self.assertEqual(len({r["canonical_url"] for r in self.records}), len(self.records))
        self.assertEqual({r["source_organization"] for r in self.records}, {"Câmara Municipal de Coimbra"})

    def test_raw_hashes_match_and_pdf_records_are_untouched(self):
        for record in self.records:
            with self.subTest(document_id=record["document_id"]):
                raw = (D2_ROOT / record["local_raw_path"]).read_bytes()
                self.assertEqual("sha256:" + hashlib.sha256(raw).hexdigest(), record["content_hash"])
        lines = (D2_ROOT / "data" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
        pdf = [json.loads(l) for l in lines if json.loads(l).get("source_type") == "pdf"]
        self.assertEqual(len(pdf), 8)
        self.assertTrue(all("canonical_url" not in r for r in pdf))

    def test_establishment_pages_record_their_validity_limit(self):
        notes = {r["document_id"]: r.get("validity_notes") or "" for r in self.records}
        for document_id in ("web-visitecoimbra-coimbra-by-night", "web-visitecoimbra-restauracao",
                            "web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira"):
            self.assertIn("may close or change", notes[document_id])

    def test_known_conflicts_are_recorded(self):
        notes = {r["document_id"]: r.get("conflict_notes") for r in self.records}
        self.assertIn("Santa Clara-a-Velha", notes["web-visitecoimbra-heranca-cultural-e-religiosa"])
        self.assertIn("Santa Clara-a-Velha", notes["web-visitecoimbra-museus"])


class ReproducibilityTests(unittest.TestCase):
    def test_processed_files_equal_a_fresh_offline_render(self):
        for record in _web_records():
            with self.subTest(document_id=record["document_id"]):
                markdown, _stats, problems = web.render_document(record)
                self.assertEqual(problems, [])
                self.assertEqual(markdown, _processed(record["document_id"]))

    def test_rendering_is_deterministic(self):
        record = next(r for r in _web_records() if r["document_id"] == "web-visitecoimbra-restauracao")
        self.assertEqual(web.render_document(record)[0], web.render_document(record)[0])

    def test_no_words_are_introduced(self):
        word = re.compile(r"[^\W_]+")
        for record in _web_records():
            with self.subTest(document_id=record["document_id"]):
                html = (D2_ROOT / record["local_raw_path"]).read_text(encoding="utf-8")
                # Preprocessing normalises to NFC; some raw pages use decomposed accents.
                raw_text = unicodedata.normalize("NFC", BeautifulSoup(html, "lxml").get_text(" "))
                raw_words = {w.lower() for w in word.findall(raw_text)}
                body = _processed(record["document_id"]).split("\n---\n", 1)[1]
                introduced = {w.lower() for w in word.findall(body)} - raw_words
                self.assertEqual(introduced, set())


if __name__ == "__main__":
    unittest.main()

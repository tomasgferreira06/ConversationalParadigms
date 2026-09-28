# Web Content Gap Audit

## 1. Problem

The current Web corpus has 24 approved/acquired `visitecoimbra.pt` pages. The
processed Markdown keeps the main editorial text, but some domain entities are
represented by Elementor content cards and are lost by page-specific section
exclusions. The concrete gap is the beer page: the narrative survives, while
four visible beer-related entities do not.

This is a content-selection problem, not a raw acquisition or chunking problem.
The existing raw HTML is available and the PDF corpus is out of scope.

## 2. Beer Page DOM Investigation

Raw snapshot: `data/raw/web/web-visitecoimbra-coimbra-uma-cidade-com-tradicao-cervejeira.html`.

The four items are in the single `[data-elementor-type="wp-page"]` content
container, inside one grid container (`data-id="605f053"`, class
`e-grid e-con-full elementor-invisible`) as four sibling widgets:

| Entity | Widget | Elementor element id | Semantic fields |
|---|---|---|---|
| BREW! | `elementor-widget-flip-box` | `1fb5ce9` | front title + front description |
| Epicura | `elementor-widget-flip-box` | `6e5bb02` | front title + front description |
| Portuguese Pedro | `elementor-widget-flip-box` | `62bd222` | front title + front description |
| Praxis | `elementor-widget-flip-box` | `dc940ba` | front title + front description |

The semantic values in the front layer are:

- `BREW!` — `Festival de cerveja artesanal`
- `Epicura` — `Cerveja Artesanal`
- `Portuguese Pedro` — `Cerveja`
- `Praxis` — `Cervejaria, Restaurante`

The destination links are present on the flip-box anchor, but the visible
button text is only `Saber mais` and is not useful knowledge by itself.

The `Walker` does not discard these cards generically. Its `flip-box` handler
extracts the front title and description and counts the back layer as dropped.
The loss happens afterwards in `_drop_sections`: the beer document has an
explicit `DROP_SECTIONS` entry for all four titles. This is therefore a
document-specific exclusion rule. The fix is to remove that exclusion and keep
the already-existing flip-box front extraction, rendered as one related block
sequence under the existing page flow; no artificial heading is added.

## 3. Current 24-page Corpus

The same Elementor flip-box widget structure occurs in five current raw pages:

- `cancao-de-coimbra`
- `coimbra-uma-cidade-com-tradicao-cervejeira`
- `coimbra-dos-estudantes`
- `heranca-cultural-e-religiosa`
- `museus`

The current tests and configured exclusions show that the remaining cases are
deliberate, page-specific editorial decisions (for example private fado-house
cards, named pottery shops, or an app promotion), not a general card-removal
rule. They remain unchanged in this focused fix. The beer page is the confirmed
content-card false negative.

Other similar structures needing continued human review are the fado-house
cards on `cancao-de-coimbra` and named shop cards on `ceramica-de-coimbra`.
They may be useful domain entities, but their current exclusion is a separate
curation decision and is not silently changed here.

## 4. Missing Valuable Pages

| URL | Discovered | Candidate | Approved | Raw | Processed | Recommendation |
|---|---:|---:|---:|---:|---:|---|
| `/o-que-fazer/coimbra-by-night/` | yes | yes | no | no | no | INCLUDE: stable evening venues and nightlife orientation; note business volatility |
| `/gastronomia/restauracao/` | yes | yes | no | no | no | INCLUDE: curated restaurant/cervejaria names; exclude volatile operational details during preprocessing |
| `/o-que-fazer/desporto/` | yes | yes | no | no | no | INCLUDE: stable activity types and places for visitor questions |

For all three, discovery metadata contains a successful HTTP 200 sample
extraction, but the URL is only `review` in `candidate_urls.jsonl`, absent from
`approved_urls.jsonl`, and consequently absent from the manifest and raw/processed
corpus. This is “not selected for acquisition”, not preprocessing loss.

## 5. Additional Candidates

The discovery inventory contains other relevant pages, including Natureza e
Rio, Atividades em Família, Cultura, and Ciência e Tecnologia. They are not
included in this focused wave: some overlap substantially with existing PDF/Web
coverage and some mix broad activity promotion with short-lived or operational
information. `Mercados` and `Gastronomia em Coimbra` are already in the current
24-page corpus. They remain candidates for a later, separately reviewed wave.

## 6. Proposed Fix

1. Remove the beer page’s four titles from `DROP_SECTIONS`.
2. Keep the existing structural `flip-box` handler: front title and front
   description are emitted in source order; image, back layer, and generic
   `Saber mais` are not emitted.
3. Do not create a heading per card and do not emit long destination URLs.
4. Add fixture tests covering recovery, ordering, navigation/template
   exclusion, responsive duplication, and deterministic rendering.
5. Approve and acquire only the three curated pages above through the existing
   discovery → approval → immutable raw → manifest → offline preprocessing
   workflow.

## 7. Risks

- Template noise must remain excluded by the content selector and widget drop
  list.
- Flip-box back layers contain images and generic CTA text; they must not leak
  into Markdown.
- Related cards can become too small if converted to independent headings; the
  current block sequence avoids that new chunking failure mode.
- Restaurant and nightlife names can become stale; the report records this as a
  validity limitation and does not preserve opening hours/prices.
- The new pages may add short sections and increase the Web/chunk counts.

## 8. Decision

READY FOR TARGETED WEB CORPUS FIX? **YES**

The root cause is confirmed in code and raw HTML, the minimal fix is clear, and
the three missing pages have already been discovered and sampled locally by the
existing discovery workflow.


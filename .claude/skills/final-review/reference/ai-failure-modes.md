# GenAI failure-mode catalogue (and how to read the audit)

This is the field guide for the `final-review` skill. It names the recurring ways
Generative-AI-assisted manuscripts fail an integrity check, maps each to a concrete
signature you can detect, and explains how to interpret the verifier's output.

The examples are drawn from the InDor/LREC 2026 retraction, which is a near-complete
taxonomy of the problem.

---

## 1. Fabricated references (the headline failure)

A reference that looks perfectly formatted but describes a paper that does not exist.
The model assembles a *plausible* citation from fragments of real ones: a real
author, a real venue, a believable title, a believable year.

**Sub-types, from the LREC notice:**

- **Wholly invented** — author, title, and venue are all fabricated. *Example:*
  `Lupi, M., Cavalcanti, G., and Caselli, T. (2023). VeraAI: A NLP System for the
  Detection of Online Disinformation. In Proceedings of PoliticalNLP at
  LREC-COLING 2024.` (Note the internal contradiction: a "(2023)" paper "In
  ... LREC-COLING 2024" — date/venue inconsistency is itself a tell.)
- **Real authors, fake paper** — the authors are real researchers, but they never
  wrote the cited work. *Example:* `Wührl, A., Sander, M., Müller, J., and Klinger,
  R. (2023). AskVera: Informed Consent for News Credibility Assessment. EMNLP
  Demos.` Hardest to catch by eye because the names check out.
- **Real paper, wrong metadata** — the work exists but the title, authors, venue,
  volume, or pages are altered. *Example:* `Hassan, N., Li, C., and Tremayne, M.
  (2017). ClaimBuster: The First-Ever End-to-End FactChecking System. PVLDB
  10(12).` — ClaimBuster is real, but the title/framing is wrong.

**Detection:** `scripts/verify_references.py`. It does not trust formatting; it asks
Crossref and OpenAlex whether the work exists and whether the metadata matches.

### Reading verifier scores

The script labels each reference by the best title-similarity it found:

- **`FOUND` (similarity ≥ 0.90)** — a near-exact title match exists. *Still* read the
  reported metadata diff: if `year`, `first_author`, or `venue` differ, you have a
  "wrong metadata" case (real paper, mis-cited).
- **`CHECK` (0.62–0.90)** — a partial match. Two possibilities: (a) the real paper
  with a paraphrased title in your bib, or (b) a different real paper the search
  surfaced. Open the candidate (the script prints its DOI/title) and decide. Do not
  auto-trust.
- **`NOT FOUND` (< 0.62, or zero results)** — no database knows this work. **Treat as
  fabricated.** The legitimate exceptions are narrow: very recent preprints, non-English
  venues, books, theses, and some workshop proceedings not indexed. Confirm those
  manually with a direct search; everything else is a BLOCKER.

**Tells that push a borderline case toward "fabricated":**
- Date/venue contradiction (a 2023 paper "in LREC-COLING 2024").
- A title that is a tidy concatenation of buzzwords ("A Comprehensive Survey",
  "The First-Ever ...", "A Cross-Cultural Comparison").
- Page ranges that are suspiciously clean (`pp. 1–10`).
- A DOI that 404s or resolves to a different paper.
- Several references by the *same* real author cluster that all fail to verify.

---

## 2. Citation↔claim mismatch ("incorrect literature review")

The cited paper is real, but the sentence citing it misstates what it says — a wrong
finding, an over-claimed result, or an attribution of a method to the wrong work.
This is the failure behind "false/incorrect literature review, especially in sections
1, 2 and 3.3" in the LREC notice.

**Detection is semantic, not mechanical.** For each in-text citation:
1. Retrieve the source abstract (`msc_search_papers`, or the DOI from Dimension 1).
2. Read the claim in *your* sentence.
3. Mark `supported` / `partial` / `unsupported`.

A reference can be perfectly real (Dimension 1 = `FOUND`) and still be a finding here.
The two checks are independent; run both.

---

## 3. Captions for not-reported figures/tables

A `\caption{...}` (sometimes a whole `figure`/`table` environment) describing a
result that is never actually shown — the image file is missing, or the float is
defined but never `\ref`-ed from the body, so the reader is told about a figure they
cannot see. Listed explicitly in the LREC notice ("Captions of not reported figures").

**Detection:** `scripts/check_figures.py` reports four classes:
- `MISSING_GRAPHIC` — `\includegraphics{X}` where `X` (with common extensions) is not
  on disk. The figure is described but cannot render.
- `ORPHAN_CAPTION` — a float with a `\caption` but no `\label`: it can never be
  referenced, a strong sign it was generated to pad the paper.
- `UNREFERENCED_FLOAT` — a float whose `\label` is never `\ref`-ed in the text: the
  caption exists but nothing in the prose points to it ("not reported").
- `DANGLING_REF` — `\ref`/`\cref`/`\autoref{Y}` with no matching `\label{Y}`: the prose
  references a figure/table/equation that doesn't exist.

---

## 4. Fabricated statistics, placeholders, and templated prose

- **Invented numbers** — quantitative claims with no traceable source (no table, no
  figure, no citation, not in your results). "Accuracy improves by 14.3%" with nothing
  behind it. The most damaging fabrication because reviewers test it.
- **Placeholders left in** — `TODO`, `TBD`, `FIXME`, `[cite]`, `??`, `XXXX`,
  `\todo{...}`, residual `lorem ipsum`. Cheap to grep, fatal to leave in.
- **Templated AI phrasing** — "It is important to note that", "plays a crucial role
  in", "in the ever-evolving landscape of", "delve into", paragraphs that restate the
  prompt. Not a retraction cause on its own, but a reliable smell that GenAI wrote
  unsupervised — wherever you see it, check the surrounding facts harder.

**Detection:** `grep` sweep for placeholders + a manual pass building a
`number → source` table for every statistic.

---

## 5. Missing AI-disclosure

Increasingly a hard requirement (LREC uses the AID framework). Absence where the venue
requires it is itself a violation. See `aid-disclosure.md`.

---

## How to weight findings

| Finding | Severity |
|---------|----------|
| `NOT FOUND` reference (unresolved after manual check) | **BLOCKER** |
| Reference metadata mismatch (wrong author/title/venue/year) | **FIX** |
| Citation↔claim `unsupported` | **BLOCKER** |
| Citation↔claim `partial` | **FIX** |
| `MISSING_GRAPHIC` / `DANGLING_REF` | **FIX** (BLOCKER if it's a core result) |
| `ORPHAN_CAPTION` / `UNREFERENCED_FLOAT` | **FIX** |
| Untraceable statistic | **BLOCKER** |
| Placeholder text | **FIX** |
| Templated phrasing | **NOTE** |
| Missing required AI-disclosure | **BLOCKER** |

**`SAFE TO SUBMIT` requires zero open BLOCKERs.** Anything less, say so plainly.

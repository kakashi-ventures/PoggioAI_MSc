---
name: final-review
description: Pre-submission integrity audit for research manuscripts — the forensic "last gate" before a paper is sent to a venue. Hunts the failure modes typical of Generative-AI-assisted writing that get papers desk-rejected or retracted: fabricated or mismatched references, in-text claims not actually supported by the cited source, captions for figures/tables that are never shown or never referenced, fabricated statistics and placeholders, and missing AI-disclosure. Use this when the user mentions "final review", "pre-submission check", "review the paper before submitting", "check the references", "verify citations", "hallucinated references", "fake citations", "camera-ready", "proofread for AI errors", or names a venue/proceedings (LREC, ACL, EMNLP, etc.) it must pass.
allowed-tools: Bash Read Edit Write Grep Glob
---

# Final Review — pre-submission integrity audit

This skill is the **last gate before submission**. It does *not* judge whether the
science is good (the `reviewer_agent` already does that). It assumes the prose is
written and asks one adversarial question: **can every factual artifact in this
manuscript be verified against ground truth — and would a venue's integrity check
survive it?**

It exists because Generative-AI-assisted manuscripts fail in a recognisable,
checkable way. The InDor/LREC retraction (June 2026) is the canonical example:
fabricated references, real authors attached to papers they never wrote, citations
whose claims don't match the source, captions for figures that were never reported.
None of that is a "writing quality" problem — it is a *grounding* problem, and it
is detectable mechanically.

## When to apply

Apply when the user is **about to submit or release** a paper and wants it audited
for AI-introduced defects. Trigger phrases: "final review", "pre-submission",
"camera-ready", "check the references / citations", "is this safe to submit",
"find the hallucinations", "before we send it to <venue>".

Do **not** use this to improve argumentation, novelty, or experimental design —
route those to `reviewer_agent` / the writeup agents instead.

## The five audit dimensions

Run all five. Each maps to a real retraction cause and to a concrete check.

| # | Dimension | Failure it catches | Primary check |
|---|-----------|--------------------|---------------|
| 1 | **Reference existence** | Wholly fabricated references; real authors on fake papers; wrong title/venue/year/pages | `scripts/verify_references.py` against Crossref + OpenAlex |
| 2 | **Citation↔claim grounding** | A real paper is cited but does not actually support the sentence citing it | Manual/LLM read of each in-text citation against the source abstract |
| 3 | **Figure/table integrity** | Caption for a figure never shown; `\ref` to a non-existent float; `\includegraphics` of a missing file; float defined but never referenced in the text | `scripts/check_figures.py` |
| 4 | **Fabrication & placeholders** | Invented statistics ("improves by 14.3%"), `TODO`/`TBD`/`[cite]`/`??`, suspiciously round or unsourced numbers, templated AI phrasing | `grep` sweep + numeric-claim traceability |
| 5 | **AI-disclosure compliance** | No declaration of GenAI assistance where the venue requires it (LREC AID framework) | `reference/aid-disclosure.md` checklist |

## Workflow

1. **Locate the manuscript and its parts.** Ask for / find: the main source
   (`.tex`, `.md`, or `.docx`→text), the bibliography (`.bib`, `.bbl`, or a
   "References" section), and the figures directory. In an MSc run these live in
   `results/consortium_*/` (`final_paper.tex`, `paper_workspace/`, figure files).

2. **Dimension 1 — references (automated, highest value).**
   ```bash
   python "${CLAUDE_SKILL_DIR}/scripts/verify_references.py" path/to/refs.bib \
       --mailto "$USER_EMAIL" --out review/references_audit.md
   ```
   It queries Crossref and OpenAlex (free, no key) for every entry and labels each
   `FOUND` / `CHECK` / `NOT FOUND`. **`NOT FOUND` = treat as fabricated until proven
   otherwise.** For `CHECK`/`FOUND` it reports metadata mismatches (year, first
   author, venue) — those are the "real authors, wrong paper" cases. Read
   `reference/ai-failure-modes.md` for how to interpret borderline scores.
   *If the environment has no outbound network, the script says so — run it where
   the network policy allows api.crossref.org / api.openalex.org, or have the user
   run it locally.*

3. **Dimension 3 — figures/tables (automated).**
   ```bash
   python "${CLAUDE_SKILL_DIR}/scripts/check_figures.py" path/to/paper.tex --figdir figures/
   ```
   Flags: dangling `\ref`/`\cref` with no `\label`; `\includegraphics` files that
   don't exist; floats with a caption but no label; floats whose label is never
   referenced in the body (the "caption of a not-reported figure" pattern).

4. **Dimension 4 — fabrication sweep (automated triage, manual confirm).**
   ```bash
   grep -nE 'TODO|TBD|FIXME|\[cite|\?\?|XX+|\\todo|lorem ipsum' path/to/*.tex
   ```
   Then list every quantitative claim and check each has a traceable source
   (a table, a figure, a cited work, or your own results). Numbers with no origin
   are the single most damaging fabrication class — see `reference/ai-failure-modes.md`.

5. **Dimension 2 — citation grounding (the part only a careful reader can do).**
   For each in-text citation, open the cited source's abstract (use
   `msc_search_papers` via the `poggio-ai` MCP server, or the DOI/URL from the
   audited bib) and confirm the sentence's claim is actually supported. Build a
   table: `claim → citation → supported? (yes/partial/no) → evidence`. Anything
   `no`/`partial` is a finding. This is where "incorrect literature review" lives.

6. **Dimension 5 — disclosure.** Walk `reference/aid-disclosure.md`. Confirm the
   manuscript contains the disclosure the target venue requires.

7. **Produce the audit report.** Write `review/final_review_report.md`:
   per-dimension findings, a severity (BLOCKER / FIX / NOTE) on each, and a
   one-line **verdict** (`SAFE TO SUBMIT` only if zero BLOCKERs). Offer to apply
   the fixes you can (delete fabricated refs, fix mismatched metadata, remove
   orphan captions) — but never invent a replacement reference to fill a gap.

## Hard rules

- **Never fabricate a fix for a fabrication.** If a reference is fake, the fix is to
  remove the citation and the claim it supported, or to find a *real* source — never
  to "correct" it into another plausible-looking but unverified entry. Inventing a
  replacement reproduces the exact violation.
- **`NOT FOUND` is guilty until proven innocent.** A clean automated pass is
  necessary, not sufficient — Crossref/OpenAlex miss some legitimate venues. Escalate
  every `NOT FOUND` to a manual check; do not silently downgrade it.
- **A reference existing ≠ the citation being correct.** Dimension 1 proves the paper
  is real; only Dimension 2 proves it says what you claim. Always run both.
- **Report verbatim.** State the verdict plainly. If there are 7 fabricated refs, the
  report says 7 — do not soften, summarise away, or mark `SAFE TO SUBMIT` with open
  BLOCKERs.

## Reference docs

- `reference/ai-failure-modes.md` — catalogue of GenAI failure signatures, how to
  read borderline verification scores, and worked examples from the LREC retraction.
- `reference/aid-disclosure.md` — the AI-Disclosure (AID) compliance checklist and
  links to the LREC framework.

## Scripts

- `scripts/verify_references.py` — verifies every reference against Crossref + OpenAlex
  (stdlib only, no install, no API key). `.bib` / `.bbl` / `.tex` / `.md` input.
- `scripts/check_figures.py` — figure/table/label/ref integrity for LaTeX (stdlib only).

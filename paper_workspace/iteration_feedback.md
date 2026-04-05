# Iteration Feedback — Dual-Salience Retrieval Paper

**Source:** MSc Reviewer Agent (review_verdict.json, review_report.tex)
**Score:** 5/10 — Borderline reject (revise and resubmit)
**Gate result:** FAILED (6 validation errors)

---

## Validation Gate Errors

1. `overall_score below threshold: 5 < 8`
2. `hard_blockers present: 1` (B1: missing research questions)
3. `intro_compliance failed: has_questions != true`
4. `intro_compliance failed: has_takeaways != true`
5. `intro_compliance failed: questions_answered != true`
6. `intro_compliance failed: takeaways_supported != true`

## Routing Decision

**Primary fix_type: `experiment`** → validation_router routes to `experiment_track`

However, 3 of 5 must-fix items are `writeup` and 1 is `theory`. A full revision cycle should address all tracks.

---

## Must-Fix Actions (ranked by priority)

### M1 [EXPERIMENT] — Run ablation A5
**Priority:** 1 (Critical)
**Action:** Run at minimum ablation A5 (tag-and-boost vs. full dual-salience system at equal token budget) and report results. Even partial results on the decisive test would transform this from an architecture specification into an empirical contribution.
**Target:** experiments/, final_paper.tex §11
**Acceptance test:** At least one empirical result (A5 or H1/H2) is reported with effect size and statistical significance test.

### M2 [WRITEUP] — Add explicit research questions
**Priority:** 2 (Critical — hard blocker B1)
**Action:** Add 2-3 explicit research questions to the introduction. Distinguish between design claims (the architecture has property X) and empirical hypotheses (the architecture achieves outcome Y).
**Suggested RQs:**
- RQ1: Does decomposing retrieval salience into epistemic and action components improve retrieval quality over unified salience?
- RQ2: Does treating surprise (contradiction, deviation, novelty) as a positive retrieval signal improve epistemic precision?
- RQ3: Does context-dependent ρ-routing outperform fixed salience mixing across different cognitive frames?
**Target:** final_paper.tex §1
**Acceptance test:** Introduction contains at least 2 explicitly labeled research questions (RQ1, RQ2, ...) that are answered or marked "pending empirical validation" in the conclusion.

### M3 [THEORY] — Fix Proposition 1
**Priority:** 3 (Important)
**Action:** Proposition 1 (Bounded Modulation) follows trivially from the clamp definition. Either:
  - (a) Prove a non-trivial property (e.g., bounds are tight, or optimal under some criterion, or the system converges), OR
  - (b) Demote to a "Design Property" / "Design Constraint" box without the Proposition environment.
**Target:** final_paper.tex §7
**Acceptance test:** Proposition 1 either has a proof establishing a non-trivial property, or is reframed as a Design Constraint.

### M4 [WRITEUP] — Reduce repetition
**Priority:** 4 (Important)
**Action:** The "relevance vs. emergence" argument appears in abstract, §1 para 1, §1 para 2, §1 para 3, and §15 conclusion (~5 times). State it once clearly (abstract + §1 para 2) and thereafter reference. This should save 1-1.5 pages for empirical content.
**Target:** final_paper.tex abstract, §1, §15
**Acceptance test:** The core argument appears in at most 2 locations. Conclusion summarizes contributions without restating full motivation.

### M5 [WRITEUP] — Add System Status table
**Priority:** 5 (Important)
**Action:** Add a "System Status" table early in the paper (§3 or §1) clearly showing which components are: (a) implemented, (b) specified but unimplemented, (c) planned.
**Target:** final_paper.tex §3
**Acceptance test:** A table appears before §4 showing implementation status of each major component (KGE, Salience Engine phases 1-3, Surprise types, Regime transitions, ρ-routing).

---

## Nice-to-Fix Actions

1. Formalize "behavior(i) contradicts pattern(j)" in surprise-by-deviation (Eq. 5)
2. Discuss similarity × salience interaction in final ranking (Eq. 9); consider minimum similarity threshold
3. Replace closing rhetorical sentence with technical summary
4. Add baselines to Table 1: ColBERT, RAPTOR, HyDE
5. Clarify whether WORKING KOs can trigger surprise-by-contradiction against CANONICAL KOs
6. Report computational cost of salience engine vs. gravity-only

---

## Questions Requiring Author Response

- Q1: Multiplicative ranking (Eq. 9) allows high-salience low-similarity KOs to dominate. Intended?
- Q2: How were ρ routing values (Table 4) determined? Expert judgment? How many experts?
- Q3: How is "behavior contradicts pattern" operationalized in surprise-by-deviation?
- Q4: Has the 60% stability floor been stress-tested with >40% CANONICAL corpus?
- Q5: Can WORKING KOs trigger surprise-by-contradiction? If not, why not?
- Q6: Is the full salience machinery justified at ~500 KO scale vs. simpler heuristic?
- Q7: What is the latency overhead of salience computation per query?

# AI-Disclosure (AID) compliance checklist

Many venues now require authors to declare how Generative AI was used in producing a
manuscript. LREC adopted the **Artificial Intelligence Disclosure (AID)** framework;
absence of a required disclosure is itself an ethics violation, independent of any
fabricated content.

Primary sources:
- LREC 2026 FAQ — https://lrec2026.info/faq/
- AID framework (C&RL News) — https://crln.acrl.org/index.php/crlnews/article/view/26548/34482

> The links above are external. Treat their *current* wording as authoritative — fetch
> them when you need the exact policy; the checklist below is a working summary, not a
> substitute for the venue's own rules.

## The core principle

AID-style frameworks ask for **functional transparency**: not "did you use AI yes/no"
but *which tool, for which task, to what extent, and who verified the output*. The
human authors remain fully accountable for every claim, citation, and figure — using
AI never transfers responsibility.

## Checklist

For the manuscript under review, confirm each:

- [ ] **A disclosure statement exists** in the location the venue specifies (often a
      footnote, an acknowledgements paragraph, or a dedicated "Use of AI" section).
- [ ] **It names the tool(s)** used (model/product and, where relevant, version).
- [ ] **It states the function** each tool served, by task. Typical buckets:
      - *Ideation / brainstorming*
      - *Literature search / discovery*
      - *Drafting / paraphrasing prose*
      - *Code or experiment generation*
      - *Figure/table generation*
      - *Editing / proofreading / translation*
- [ ] **It states the extent** (e.g. "first draft of Section 2, then human-edited" vs
      "spelling/grammar only").
- [ ] **It affirms human verification** — that the authors checked all AI-produced
      content, especially references, quantitative claims, and figures, and take
      responsibility for them.
- [ ] **No prohibited use** under the venue's policy occurred (some venues forbid AI as
      a listed "author", or forbid undisclosed AI-generated text entirely).

## Why this matters for this skill specifically

The other four audit dimensions catch *defects*. This one catches a *process* gap. A
paper can be factually clean and still be rejected for failing to disclose — and,
conversely, disclosure does **not** excuse fabricated references or captions. The two
are orthogonal: the manuscript needs both a clean integrity audit *and* a compliant
disclosure.

## Drafting a disclosure (when asked)

If the user asks you to draft the statement, write a truthful, specific one based on
how the manuscript was actually produced — for an MSc-generated paper, that means
disclosing the multi-agent pipeline, the models used (from `.llm_config.yaml`), the
tasks they performed (literature review, drafting, figure generation, proofreading),
and an explicit statement that the human authors verified all references, statistics,
and figures before submission. Never overstate the verification that actually happened.

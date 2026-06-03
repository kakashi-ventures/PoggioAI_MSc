#!/usr/bin/env python3
"""
verify_references.py — flag fabricated / mis-cited references in a manuscript.

For every reference it finds, it asks Crossref and OpenAlex (both free, no API key)
whether a matching work exists, and reports metadata mismatches (year, first author,
venue). It is the automated front line of the `final-review` skill against the
"fabricated references" failure mode that gets GenAI-assisted papers retracted.

Standard library only — no pip install required.

Input formats (auto-detected by extension, override with --format):
  .bib / .bbl   BibTeX entries / compiled bibliography
  .tex          \\bibitem entries inside thebibliography
  .md / .txt    a "References" / "Bibliography" section, one entry per item

Usage:
  python verify_references.py refs.bib
  python verify_references.py paper.tex --mailto you@example.com --out audit.md
  python verify_references.py refs.bib --json audit.json

Exit code is non-zero if any reference is NOT FOUND (so it can gate CI).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher
from typing import Optional

CROSSREF = "https://api.crossref.org/works"
OPENALEX = "https://api.openalex.org/works"

# Similarity thresholds on the best title match found.
FOUND = 0.90
CHECK = 0.62


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Reference:
    raw: str
    key: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: str = ""
    venue: str = ""
    doi: str = ""


@dataclass
class Result:
    reference: Reference
    verdict: str = "NOT FOUND"          # FOUND | CHECK | NOT FOUND | NO NETWORK
    score: float = 0.0
    source: str = ""                    # crossref | openalex | doi
    matched_title: str = ""
    matched_year: str = ""
    matched_first_author: str = ""
    matched_venue: str = ""
    matched_doi: str = ""
    mismatches: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def _norm(s: str) -> str:
    s = re.sub(r"[{}\\]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _title_key(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def parse_bibtex(text: str) -> list[Reference]:
    refs: list[Reference] = []
    for m in re.finditer(r"@\w+\s*\{\s*([^,]+),(.*?)\n\}", text, re.DOTALL):
        key, body = m.group(1).strip(), m.group(2)

        def field_val(name: str) -> str:
            fm = re.search(rf"\b{name}\s*=\s*[{{\"](.+?)[}}\"]\s*,?\s*\n",
                           body, re.IGNORECASE | re.DOTALL)
            return _norm(fm.group(1)) if fm else ""

        title = field_val("title")
        authors_raw = field_val("author")
        authors = [a.strip() for a in re.split(r"\s+and\s+", authors_raw) if a.strip()]
        venue = field_val("journal") or field_val("booktitle")
        refs.append(Reference(
            raw=_norm(m.group(0))[:400], key=key, title=title, authors=authors,
            year=field_val("year"), venue=venue, doi=field_val("doi"),
        ))
    return refs


def parse_bibitems(text: str) -> list[Reference]:
    refs: list[Reference] = []
    parts = re.split(r"\\bibitem(?:\[[^\]]*\])?\{([^}]*)\}", text)
    # parts = [pre, key1, body1, key2, body2, ...]
    for i in range(1, len(parts) - 1, 2):
        key, body = parts[i].strip(), _norm(parts[i + 1])
        refs.append(_ref_from_freeform(body, key))
    return refs


def parse_freeform(text: str) -> list[Reference]:
    # isolate a References / Bibliography section if present
    m = re.search(r"(?:^|\n)\s*#{0,3}\s*(references|bibliography|works cited)\s*\n",
                  text, re.IGNORECASE)
    if m:
        text = text[m.end():]
    lines = text.splitlines()
    entries: list[str] = []
    buf = ""
    for ln in lines:
        s = ln.strip()
        if not s:
            if buf:
                entries.append(buf); buf = ""
            continue
        # new numbered / bulleted item starts a new entry
        if re.match(r"^(\[\d+\]|\d+[.)]|[-*•])\s+", s) and buf:
            entries.append(buf); buf = s
        else:
            buf = f"{buf} {s}".strip() if buf else s
    if buf:
        entries.append(buf)
    return [_ref_from_freeform(re.sub(r"^(\[\d+\]|\d+[.)]|[-*•])\s+", "", e), f"ref{i+1}")
            for i, e in enumerate(entries) if len(e) > 20]


def _ref_from_freeform(s: str, key: str) -> Reference:
    s = _norm(s)
    year = ""
    ym = re.search(r"\((\d{4})[a-z]?\)|\b(19|20)\d{2}\b", s)
    if ym:
        year = re.search(r"(19|20)\d{2}", ym.group(0)).group(0)
    doi = ""
    dm = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", s)
    if dm:
        doi = dm.group(0).rstrip(".")
    # crude title guess: the chunk after the year, before the venue "In ..."
    title = ""
    if ym:
        after = s[ym.end():].lstrip(" .")
        title = re.split(r"\.\s|\bIn\b|\bProceedings\b", after)[0].strip(" .")
    if len(title) < 6:
        title = s
    authors = []
    if ym:
        before = s[:ym.start()].strip(" .,")
        authors = [a.strip() for a in re.split(r",| and |&", before) if a.strip()]
    return Reference(raw=s[:400], key=key, title=title, authors=authors,
                     year=year, doi=doi)


def parse(text: str, fmt: str) -> list[Reference]:
    if fmt == "bib":
        return parse_bibtex(text)
    if fmt == "tex":
        return parse_bibitems(text) or parse_freeform(text)
    return parse_freeform(text)


def detect_format(path: str, text: str) -> str:
    if path.endswith(".bib"):
        return "bib"
    if path.endswith((".bbl", ".tex")):
        return "tex" if "\\bibitem" in text else ("bib" if "@" in text else "tex")
    if "@article" in text or "@inproceedings" in text:
        return "bib"
    if "\\bibitem" in text:
        return "tex"
    return "free"


# --------------------------------------------------------------------------- #
# Lookup
# --------------------------------------------------------------------------- #
def _get(url: str, mailto: str, timeout: int = 20) -> Optional[dict]:
    headers = {"User-Agent": f"final-review-skill/1.0 (mailto:{mailto or 'anon@example.com'})"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def lookup_crossref(ref: Reference, mailto: str) -> Optional[dict]:
    if ref.doi:
        try:
            data = _get(f"{CROSSREF}/{urllib.parse.quote(ref.doi)}", mailto)
            it = data.get("message")
            if it:
                return _normalize_crossref(it, via="doi")
        except Exception:
            pass
    q = urllib.parse.urlencode({
        "query.bibliographic": f"{ref.title} {' '.join(ref.authors[:2])}".strip(),
        "rows": 5,
    })
    try:
        data = _get(f"{CROSSREF}?{q}", mailto)
        items = data.get("message", {}).get("items", [])
        return _best(ref, [_normalize_crossref(i, via="crossref") for i in items])
    except Exception:
        return None


def _normalize_crossref(it: dict, via: str) -> dict:
    title = (it.get("title") or [""])[0]
    authors = it.get("author") or []
    first = ""
    if authors:
        a = authors[0]
        first = f"{a.get('family', '')}".strip() or a.get("name", "")
    yr = ""
    for k in ("published-print", "published-online", "issued", "created"):
        parts = (it.get(k) or {}).get("date-parts")
        if parts and parts[0] and parts[0][0]:
            yr = str(parts[0][0]); break
    venue = (it.get("container-title") or [""])[0]
    return {"title": title, "first_author": first, "year": yr,
            "venue": venue, "doi": it.get("DOI", ""), "source": via}


def lookup_openalex(ref: Reference, mailto: str) -> Optional[dict]:
    q = urllib.parse.urlencode({
        "search": ref.title,
        "per-page": 5,
        "mailto": mailto or "anon@example.com",
    })
    try:
        data = _get(f"{OPENALEX}?{q}", mailto)
        cands = []
        for it in data.get("results", []):
            auth = it.get("authorships") or []
            first = ""
            if auth:
                first = (auth[0].get("author") or {}).get("display_name", "")
            cands.append({
                "title": it.get("title") or it.get("display_name") or "",
                "first_author": first,
                "year": str(it.get("publication_year") or ""),
                "venue": ((it.get("primary_location") or {}).get("source") or {}).get("display_name", "") or "",
                "doi": (it.get("doi") or "").replace("https://doi.org/", ""),
                "source": "openalex",
            })
        return _best(ref, cands)
    except Exception:
        return None


def _best(ref: Reference, cands: list[dict]) -> Optional[dict]:
    best, best_score = None, 0.0
    rt = _title_key(ref.title)
    for c in cands:
        sc = SequenceMatcher(None, rt, _title_key(c["title"])).ratio()
        if sc > best_score:
            best, best_score = c, sc
    if best is not None:
        best = dict(best)
        best["_score"] = best_score
    return best


# --------------------------------------------------------------------------- #
# Verify
# --------------------------------------------------------------------------- #
def verify(ref: Reference, mailto: str) -> Result:
    res = Result(reference=ref)
    cand = None
    try:
        cand = lookup_crossref(ref, mailto)
        if not cand or cand.get("_score", 0) < FOUND:
            alt = lookup_openalex(ref, mailto)
            if alt and alt.get("_score", 0) > (cand.get("_score", 0) if cand else 0):
                cand = alt
    except Exception:
        res.verdict = "NO NETWORK"
        return res

    if cand is None:
        res.verdict = "NOT FOUND"
        return res

    score = cand.get("_score", 0.0)
    if cand.get("source") == "doi":
        score = max(score, FOUND)  # exact DOI hit is authoritative
    res.score = round(score, 3)
    res.source = cand.get("source", "")
    res.matched_title = cand.get("title", "")
    res.matched_year = cand.get("year", "")
    res.matched_first_author = cand.get("first_author", "")
    res.matched_venue = cand.get("venue", "")
    res.matched_doi = cand.get("doi", "")

    if score >= FOUND:
        res.verdict = "FOUND"
    elif score >= CHECK:
        res.verdict = "CHECK"
    else:
        res.verdict = "NOT FOUND"
        return res

    # metadata mismatches (only meaningful once we have a match)
    if ref.year and res.matched_year and ref.year != res.matched_year:
        res.mismatches.append(f"year: cited {ref.year} vs found {res.matched_year}")
    if ref.authors and res.matched_first_author:
        cited_last = re.sub(r"[^a-z]", "", ref.authors[0].split(",")[0].split()[-1].lower()) \
            if ref.authors[0] else ""
        found_last = re.sub(r"[^a-z]", "", res.matched_first_author.split()[-1].lower()) \
            if res.matched_first_author else ""
        if cited_last and found_last and cited_last != found_last:
            res.mismatches.append(
                f"first author: cited '{ref.authors[0]}' vs found '{res.matched_first_author}'")
    return res


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def render_md(results: list[Result]) -> str:
    n = len(results)
    found = sum(r.verdict == "FOUND" for r in results)
    check = sum(r.verdict == "CHECK" for r in results)
    missing = sum(r.verdict == "NOT FOUND" for r in results)
    nonet = sum(r.verdict == "NO NETWORK" for r in results)
    out = ["# Reference verification audit", ""]
    if nonet:
        out += ["> ⚠️ **No network access** — could not reach Crossref/OpenAlex for "
                f"{nonet} reference(s). Run where the network policy allows "
                "`api.crossref.org` and `api.openalex.org`, or run locally.", ""]
    out += [f"**{n} references** — ✅ {found} found · ⚠️ {check} check · "
            f"❌ {missing} NOT FOUND" + (f" · 🔌 {nonet} no-network" if nonet else ""), ""]
    if missing:
        out += [f"> ❌ **{missing} reference(s) could not be verified. Treat as "
                "fabricated until a manual search proves otherwise.**", ""]
    icon = {"FOUND": "✅", "CHECK": "⚠️", "NOT FOUND": "❌", "NO NETWORK": "🔌"}
    out += ["| Key | Verdict | Score | Cited title | Notes |",
            "|-----|---------|-------|-------------|-------|"]
    for r in results:
        notes = "; ".join(r.mismatches) if r.mismatches else ""
        if r.verdict in ("CHECK", "FOUND") and r.matched_doi:
            notes = (notes + " · " if notes else "") + f"match: {r.matched_doi}"
        title = (r.reference.title[:60] + "…") if len(r.reference.title) > 60 else r.reference.title
        out.append(f"| {r.reference.key or '?'} | {icon.get(r.verdict,'')} {r.verdict} "
                   f"| {r.score:.2f} | {title.replace('|','/')} | {notes.replace('|','/')} |")
    # detail for problems
    probs = [r for r in results if r.verdict in ("NOT FOUND", "CHECK") or r.mismatches]
    if probs:
        out += ["", "## Items needing attention", ""]
        for r in probs:
            out.append(f"### `{r.reference.key or '?'}` — {r.verdict} ({r.score:.2f})")
            out.append(f"- **Cited:** {r.reference.raw}")
            if r.matched_title:
                out.append(f"- **Closest real match ({r.source}):** "
                           f"{r.matched_title} — {r.matched_first_author} "
                           f"({r.matched_year}) {r.matched_venue} {r.matched_doi}".strip())
            if r.mismatches:
                out.append(f"- **Metadata mismatch:** {'; '.join(r.mismatches)}")
            if r.verdict == "NOT FOUND":
                out.append("- **Action:** no database match — verify manually; if it "
                           "cannot be found, remove the citation and the claim it supports.")
            out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="bibliography or manuscript file")
    ap.add_argument("--format", choices=["bib", "tex", "free", "auto"], default="auto")
    ap.add_argument("--mailto", default="", help="email for Crossref/OpenAlex polite pool")
    ap.add_argument("--out", help="write the markdown report to this path")
    ap.add_argument("--json", dest="json_out", help="write machine-readable JSON here")
    ap.add_argument("--delay", type=float, default=0.5, help="seconds between API calls")
    ap.add_argument("--limit", type=int, default=0, help="only check first N refs (0=all)")
    args = ap.parse_args()

    try:
        with open(args.path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as e:
        print(f"error: cannot read {args.path}: {e}", file=sys.stderr)
        return 2

    fmt = detect_format(args.path, text) if args.format == "auto" else args.format
    refs = parse(text, fmt)
    if args.limit:
        refs = refs[: args.limit]
    if not refs:
        print(f"error: no references parsed from {args.path} (format={fmt})", file=sys.stderr)
        return 2

    print(f"Parsed {len(refs)} references (format={fmt}). Verifying…", file=sys.stderr)
    results: list[Result] = []
    for i, ref in enumerate(refs, 1):
        res = verify(ref, args.mailto)
        results.append(res)
        print(f"  [{i}/{len(refs)}] {res.verdict:9s} {ref.key or ref.title[:40]}",
              file=sys.stderr)
        if i < len(refs):
            time.sleep(args.delay)

    report = render_md(results)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"\nReport written to {args.out}", file=sys.stderr)
    else:
        print("\n" + report)

    if args.json_out:
        payload = [{**asdict(r), "reference": asdict(r.reference)} for r in results]
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"JSON written to {args.json_out}", file=sys.stderr)

    return 1 if any(r.verdict == "NOT FOUND" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())

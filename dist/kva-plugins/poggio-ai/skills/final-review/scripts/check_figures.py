#!/usr/bin/env python3
"""
check_figures.py — figure/table/label/ref integrity for LaTeX manuscripts.

Catches the "captions of not-reported figures" failure mode (an explicit cause in the
InDor/LREC 2026 retraction) plus the related label/ref/graphic defects:

  MISSING_GRAPHIC    \\includegraphics{X} but no such file on disk
  ORPHAN_CAPTION     a float with \\caption but no \\label (can never be referenced)
  UNREFERENCED_FLOAT a float whose \\label is never \\ref'd in the body ("not reported")
  DANGLING_REF       \\ref/\\cref/\\autoref{Y} with no matching \\label{Y}

Standard library only. Scans one .tex file or a whole directory of them.

Usage:
  python check_figures.py paper.tex
  python check_figures.py paper.tex --figdir figures/
  python check_figures.py paper_workspace/ --json fig_audit.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

GRAPHIC_EXTS = [".pdf", ".png", ".jpg", ".jpeg", ".eps", ".ps", ".svg", ".gif", ".tikz", ""]
FLOAT_ENVS = ("figure", "table", "figure*", "table*", "wrapfigure", "subfigure", "sidewaysfigure")


def gather_tex(path: str) -> list[str]:
    if os.path.isfile(path):
        return [path]
    files = []
    for root, _, names in os.walk(path):
        for n in names:
            if n.endswith(".tex"):
                files.append(os.path.join(root, n))
    return sorted(files)


def strip_comments(s: str) -> str:
    # remove % comments (not escaped \%)
    return re.sub(r"(?<!\\)%.*", "", s)


def find_floats(text: str):
    """Yield (env, body, start_line) for each float environment (handles nesting)."""
    for env in FLOAT_ENVS:
        e = re.escape(env)
        for m in re.finditer(rf"\\begin\{{{e}\}}(.*?)\\end\{{{e}\}}", text, re.DOTALL):
            line = text[: m.start()].count("\n") + 1
            yield env, m.group(1), line


def analyze(files: list[str], figdir: str | None):
    findings: list[dict] = []
    all_labels: set[str] = set()
    all_refs: set[str] = set()
    float_labels: dict[str, tuple[str, int, str]] = {}   # label -> (env, line, file)

    per_file_text: dict[str, str] = {}
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            per_file_text[f] = strip_comments(fh.read())

    # pass 1: collect labels, refs, graphics, float structure
    for f, text in per_file_text.items():
        base = os.path.dirname(f)
        for lm in re.finditer(r"\\label\{([^}]*)\}", text):
            all_labels.add(lm.group(1))
        # \ref \eqref \autoref \pageref \cref \Cref \vref ... (cref may list multiple)
        for rm in re.finditer(r"\\(?:c|C|auto|page|eq|v|name)?ref\*?\{([^}]*)\}", text):
            for part in rm.group(1).split(","):
                if part.strip():
                    all_refs.add(part.strip())

        # graphics existence
        for gm in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}", text):
            target = gm.group(1).strip()
            line = text[: gm.start()].count("\n") + 1
            if not _graphic_exists(target, base, figdir):
                findings.append({
                    "type": "MISSING_GRAPHIC", "file": f, "line": line,
                    "detail": f"\\includegraphics{{{target}}} — no matching file found",
                })

        # float structure
        for env, body, line in find_floats(text):
            has_caption = bool(re.search(r"\\caption\b", body))
            labels = re.findall(r"\\label\{([^}]*)\}", body)
            if has_caption and not labels:
                cap = re.search(r"\\caption(?:\[[^\]]*\])?\{(.{0,60})", body, re.DOTALL)
                captxt = (cap.group(1).strip().replace("\n", " ") + "…") if cap else ""
                findings.append({
                    "type": "ORPHAN_CAPTION", "file": f, "line": line,
                    "detail": f"{env} has a caption but no \\label "
                              f"(cannot be referenced). Caption: \"{captxt}\"",
                })
            for lb in labels:
                float_labels[lb] = (env, line, f)

    # pass 2: cross-file consistency
    for lb, (env, line, f) in float_labels.items():
        if lb not in all_refs:
            findings.append({
                "type": "UNREFERENCED_FLOAT", "file": f, "line": line,
                "detail": f"{env} \\label{{{lb}}} is never \\ref'd in the text "
                          f"(caption present but float not reported)",
            })
    for r in sorted(all_refs):
        if r not in all_labels:
            findings.append({
                "type": "DANGLING_REF", "file": "?", "line": 0,
                "detail": f"\\ref{{{r}}} has no matching \\label (points to nothing)",
            })

    stats = {
        "files": len(files), "labels": len(all_labels), "refs": len(all_refs),
        "floats_with_label": len(float_labels),
    }
    return findings, stats


def _graphic_exists(target: str, base: str, figdir: str | None) -> bool:
    roots = [base, os.getcwd()]
    if figdir:
        roots = [figdir, os.path.join(base, figdir)] + roots
    has_ext = os.path.splitext(target)[1].lower() in GRAPHIC_EXTS and os.path.splitext(target)[1]
    for root in roots:
        cand = os.path.join(root, target)
        if has_ext and os.path.isfile(cand):
            return True
        if not has_ext:
            for ext in GRAPHIC_EXTS:
                if ext and os.path.isfile(cand + ext):
                    return True
    return False


def render_md(findings: list[dict], stats: dict) -> str:
    by_type: dict[str, list[dict]] = {}
    for fn in findings:
        by_type.setdefault(fn["type"], []).append(fn)
    out = ["# Figure / table integrity audit", "",
           f"Scanned **{stats['files']} file(s)** — {stats['labels']} labels, "
           f"{stats['refs']} refs, {stats['floats_with_label']} labelled floats.", ""]
    if not findings:
        out += ["✅ **No figure/table integrity issues found.**"]
        return "\n".join(out)
    order = ["MISSING_GRAPHIC", "DANGLING_REF", "ORPHAN_CAPTION", "UNREFERENCED_FLOAT"]
    out += [f"❌ **{len(findings)} issue(s) found.**", ""]
    for t in order:
        items = by_type.get(t)
        if not items:
            continue
        out += [f"## {t} ({len(items)})", ""]
        for it in items:
            loc = f"{it['file']}:{it['line']}" if it["line"] else it["file"]
            out.append(f"- `{loc}` — {it['detail']}")
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help=".tex file or directory of .tex files")
    ap.add_argument("--figdir", help="directory holding figure files")
    ap.add_argument("--out", help="write markdown report here")
    ap.add_argument("--json", dest="json_out", help="write JSON findings here")
    args = ap.parse_args()

    files = gather_tex(args.path)
    if not files:
        print(f"error: no .tex files at {args.path}", file=sys.stderr)
        return 2

    findings, stats = analyze(files, args.figdir)
    report = render_md(findings, stats)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"Report written to {args.out}", file=sys.stderr)
    else:
        print(report)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump({"stats": stats, "findings": findings}, fh, indent=2)
        print(f"JSON written to {args.json_out}", file=sys.stderr)

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

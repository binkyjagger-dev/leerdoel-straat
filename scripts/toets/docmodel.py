"""One document structure, rendered to Markdown (the source) and to Word with python-docx (specs/35 §1).

Blocks: ("h1"|"h2"|"h3", text) · ("p", text) — **bold** spans allowed · ("bullets", [text]) · ("table", rows, header: bool)
· ("img", path, caption) · ("pagebreak",). Word layout: A4, Arial 11, margins 2 cm, tables with a light header fill,
figures 14 cm wide.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

BOLD = re.compile(r"\*\*(.+?)\*\*")


def to_md(blocks: list[tuple], md_dir: Path) -> str:
    out = []
    for b in blocks:
        k = b[0]
        if k in ("h1", "h2", "h3"):
            out += ["#" * int(k[1]) + " " + b[1], ""]
        elif k == "p":
            out += [b[1], ""]
        elif k == "bullets":
            out += [f"- {x}" for x in b[1]] + [""]
        elif k == "table":
            rows = [[str(c).replace("|", "/").replace("\n", " ") for c in r] for r in b[1]]
            if not rows:
                continue
            w = max(len(r) for r in rows)
            rows = [r + [""] * (w - len(r)) for r in rows]
            out += ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * w] + ["| " + " | ".join(r) + " |" for r in rows[1:]] + [""]
        elif k == "img":
            rel = os.path.relpath(b[1], md_dir).replace(os.sep, "/")
            out += [f"![{b[2] if len(b) > 2 else ''}]({rel})", ""]
        elif k == "pagebreak":
            out += ["---", ""]
    return "\n".join(out)


def _runs(par, text: str) -> None:
    pos = 0
    for m in BOLD.finditer(text):
        if m.start() > pos:
            par.add_run(text[pos:m.start()])
        par.add_run(m.group(1)).bold = True
        pos = m.end()
    if pos < len(text):
        par.add_run(text[pos:])


def _shade(cell, fill: str) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def to_docx(blocks: list[tuple], path: Path) -> None:
    from docx import Document
    from docx.enum.text import WD_BREAK
    from docx.shared import Cm, Pt
    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(2))
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Arial", Pt(11)
    for h in ("Heading 1", "Heading 2", "Heading 3"):
        doc.styles[h].font.name = "Arial"
    for b in blocks:
        k = b[0]
        if k in ("h1", "h2", "h3"):
            doc.add_heading(b[1], level=int(k[1]))
        elif k == "p":
            _runs(doc.add_paragraph(), b[1])
        elif k == "bullets":
            for x in b[1]:
                _runs(doc.add_paragraph(style="List Bullet"), x)
        elif k == "table":
            rows = b[1]
            if not rows:
                continue
            w = max(len(r) for r in rows)
            t = doc.add_table(rows=len(rows), cols=w)
            t.style = "Table Grid"
            for i, r in enumerate(rows):
                for j in range(w):
                    cell = t.cell(i, j)
                    cell.text = ""
                    _runs(cell.paragraphs[0], str(r[j]) if j < len(r) else "")
                    if i == 0 and (len(b) < 3 or b[2]):
                        _shade(cell, "E7E6E6")
                        for run in cell.paragraphs[0].runs:
                            run.bold = True
            doc.add_paragraph()
        elif k == "img":
            if Path(b[1]).exists():
                doc.add_picture(str(b[1]), width=Cm(14))
                if len(b) > 2 and b[2]:
                    doc.add_paragraph(b[2])
        elif k == "pagebreak":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


def write(blocks: list[tuple], md_path: Path) -> tuple[Path, Path]:
    """Write <name>.md and <name>.docx side by side. On Windows an open file blocks the write: say so in Dutch."""
    md_path.parent.mkdir(parents=True, exist_ok=True)
    docx_path = md_path.with_suffix(".docx")
    try:
        md_path.write_text(to_md(blocks, md_path.parent), encoding="utf-8")
        to_docx(blocks, docx_path)
    except PermissionError:
        raise SystemExit(f"[export_toets] kan {docx_path.name} niet schrijven: sluit het bestand (bijv. in Word) en probeer opnieuw")
    return md_path, docx_path

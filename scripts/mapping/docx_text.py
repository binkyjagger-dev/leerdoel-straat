#!/usr/bin/env python3
"""Extract the text of a .docx (exercise workbook) in reading order, with list numbering resolved (specs/11 §2.2).

Usage: docx_text.py <file.docx> <out_dir>

Writes <out_dir>/document.txt and <out_dir>/media/* (embedded images). Per body element one line:
- paragraphs: list label as Word renders it ("a.", "1.", "•") + text; tabs kept, line breaks as " / ";
- images: "[afbeelding: media/<name>]" where they sit in the text (icons, tables pasted as pictures);
- tables: one line per row, "| cel | cel |", paragraphs inside a cell joined with " / ".
Empty paragraphs are dropped. Automatic numbering (sub-question letters) is not in the raw XML text,
which is why plain unzip/grep loses the a/b/c that the answer key uses.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
V = "urn:schemas-microsoft-com:vml"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
q = lambda ns, tag: f"{{{ns}}}{tag}"


def roman(n: int) -> str:
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
            (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    s = ""
    for v, r in vals:
        while n >= v:
            s, n = s + r, n - v
    return s


def letters(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(97 + r) + s
    return s


def fmt(n: int, kind: str) -> str:
    return {"decimal": str(n), "lowerLetter": letters(n), "upperLetter": letters(n).upper(),
            "lowerRoman": roman(n), "upperRoman": roman(n).upper()}.get(kind, str(n))


class Numbering:
    """Word list counters: num instances share their abstractNum's counters unless they override the start."""

    def __init__(self, xml: bytes | None):
        self.levels, self.nums, self.counters, self.seen = {}, {}, {}, set()
        if not xml:
            return
        root = ET.fromstring(xml)
        for an in root.findall(q(W, "abstractNum")):
            aid = an.get(q(W, "abstractNumId"))
            for lvl in an.findall(q(W, "lvl")):
                il = int(lvl.get(q(W, "ilvl")))
                g = lambda t, d: (lvl.find(q(W, t)).get(q(W, "val")) if lvl.find(q(W, t)) is not None else d)
                self.levels[(aid, il)] = {"start": int(g("start", "1")), "fmt": g("numFmt", "decimal"),
                                          "text": g("lvlText", f"%{il + 1}.")}
        for num in root.findall(q(W, "num")):
            nid = num.get(q(W, "numId"))
            aid = num.find(q(W, "abstractNumId")).get(q(W, "val"))
            overrides = {}
            for ov in num.findall(q(W, "lvlOverride")):
                so = ov.find(q(W, "startOverride"))
                if so is not None:
                    overrides[int(ov.get(q(W, "ilvl")))] = int(so.get(q(W, "val")))
            self.nums[nid] = (aid, overrides)

    def label(self, nid: str, il: int) -> str:
        if nid not in self.nums or nid == "0":
            return ""
        aid, overrides = self.nums[nid]
        lvl = self.levels.get((aid, il))
        if not lvl:
            return ""
        cnt = self.counters.setdefault(aid, {})
        if (nid, il) not in self.seen and il in overrides:
            cnt[il] = overrides[il] - 1
        self.seen.add((nid, il))
        cnt[il] = cnt.get(il, lvl["start"] - 1) + 1
        for deeper in [k for k in cnt if k > il]:
            del cnt[deeper]
        if lvl["fmt"] == "bullet":
            return "•"
        if lvl["fmt"] == "none":
            return ""
        def sub(m):
            k = int(m.group(1)) - 1
            lk = self.levels.get((aid, k), {"start": 1, "fmt": "decimal"})
            return fmt(cnt.get(k, lk["start"]), lk["fmt"])
        return re.sub(r"%(\d)", sub, lvl["text"])


def run_text(el, rels: dict) -> str:
    parts = []
    for node in el.iter():
        if node.tag == q(W, "t"):
            parts.append(node.text or "")
        elif node.tag == q(W, "tab"):
            parts.append("\t")
        elif node.tag in (q(W, "br"), q(W, "cr")):
            parts.append(" / ")
        elif node.tag == q(A, "blip") and node.get(q(R, "embed")) in rels:
            parts.append(f" [afbeelding: {rels[node.get(q(R, 'embed'))]}] ")
        elif node.tag == q(V, "imagedata") and node.get(q(R, "id")) in rels:
            parts.append(f" [afbeelding: {rels[node.get(q(R, 'id'))]}] ")
    return "".join(parts)


def paragraph(p, rels: dict, numbering: Numbering) -> str:
    text = run_text(p, rels)
    text = re.sub(r"[ \t]{2,}", lambda m: "\t" if "\t" in m.group(0) else " ", text).strip()
    if not text.replace("/", "").strip():
        return ""
    numpr = p.find(f"{q(W, 'pPr')}/{q(W, 'numPr')}")
    if numpr is not None and text:
        nid = numpr.find(q(W, "numId"))
        il = numpr.find(q(W, "ilvl"))
        lab = numbering.label(nid.get(q(W, "val")) if nid is not None else "0",
                              int(il.get(q(W, "val"))) if il is not None else 0)
        if lab:
            text = f"{lab} {text}"
    return text


def body_lines(parent, rels: dict, numbering: Numbering) -> list[str]:
    lines = []
    for el in parent:
        if el.tag == q(W, "p"):
            t = paragraph(el, rels, numbering)
            if t:
                lines.append(t)
        elif el.tag == q(W, "tbl"):
            for tr in el.findall(q(W, "tr")):
                cells = []
                for tc in tr.findall(q(W, "tc")):
                    cells.append(" / ".join(x for x in body_lines(tc, rels, numbering) if x))
                if any(cells):
                    lines.append("| " + " | ".join(cells) + " |")
        elif el.tag == q(W, "sdt"):
            content = el.find(q(W, "sdtContent"))
            if content is not None:
                lines += body_lines(content, rels, numbering)
    return lines


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    src, out = Path(argv[1]), Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as z:
        names = set(z.namelist())
        rels = {}
        if "word/_rels/document.xml.rels" in names:
            for rel in ET.fromstring(z.read("word/_rels/document.xml.rels")).findall(q(PR, "Relationship")):
                target = rel.get("Target", "")
                if target.startswith("media/"):
                    rels[rel.get("Id")] = target
        numbering = Numbering(z.read("word/numbering.xml") if "word/numbering.xml" in names else None)
        body = ET.fromstring(z.read("word/document.xml")).find(q(W, "body"))
        lines = body_lines(body, rels, numbering)
        media = [n for n in names if n.startswith("word/media/")]
        for n in media:
            dest = out / n[len("word/"):]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(n))
    (out / "document.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[docx_text] {src.name}: {len(lines)} lines, {len(media)} images -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

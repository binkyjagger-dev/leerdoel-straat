#!/usr/bin/env python3
"""Extract text per page from a PDF, with OCR fallback for scanned pages (specs/11 §2.1).

Usage: ocr_pdf.py <file.pdf> <out_dir> [--dpi 200] [--lang nld+eng] [--force-ocr]

Writes <out_dir>/page-NNN.txt per page and <out_dir>/pages.json
  {"pages": N, "text_pages": [...], "ocr_pages": [...], "lang": "...", "method": "pdftotext|ocr|mixed"}.
A page is OCR'd when pdftotext yields < 50 characters (or --force-ocr). OCR uses tesseract via
pdftoppm; language falls back from the requested one to whatever is installed (eng works acceptably
for Dutch body text). Without tesseract the script writes pages.json with "ocr_pages" unresolved and
exit code 3, so the ingest agent can fall back to reading page images itself.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    pdf, out = Path(argv[1]), Path(argv[2])
    dpi = argv[argv.index("--dpi") + 1] if "--dpi" in argv else "200"
    lang = argv[argv.index("--lang") + 1] if "--lang" in argv else "nld+eng"
    force = "--force-ocr" in argv
    out.mkdir(parents=True, exist_ok=True)

    info = run(["pdfinfo", str(pdf)])
    n = int(next((l.split()[-1] for l in info.splitlines() if l.startswith("Pages:")), "0"))
    text_pages, ocr_pages, unresolved = [], [], []
    tess = shutil.which("tesseract")
    if tess:
        langs = run(["tesseract", "--list-langs"]).split()
        wanted = [l for l in lang.split("+") if l in langs] or (["eng"] if "eng" in langs else [])
        lang = "+".join(wanted) if wanted else None
    for p in range(1, n + 1):
        txt = "" if force else run(["pdftotext", "-layout", "-f", str(p), "-l", str(p), str(pdf), "-"])
        if len(txt.strip()) >= 50:
            text_pages.append(p)
        else:
            if tess and lang:
                prefix = out / f"img-{p:03d}"
                subprocess.run(["pdftoppm", "-r", dpi, "-f", str(p), "-l", str(p), "-png", str(pdf), str(prefix)],
                               capture_output=True)
                img = next(out.glob(f"img-{p:03d}*.png"), None)
                if img:
                    txt = run(["tesseract", str(img), "-", "-l", lang])
                    img.unlink(missing_ok=True)
                ocr_pages.append(p)
            else:
                unresolved.append(p)
        (out / f"page-{p:03d}.txt").write_text(txt, encoding="utf-8")
    method = "pdftotext" if not ocr_pages and not unresolved else ("ocr" if not text_pages else "mixed")
    meta = {"pages": n, "text_pages": text_pages, "ocr_pages": ocr_pages, "unresolved_pages": unresolved,
            "lang": lang, "method": method, "dpi": int(dpi)}
    (out / "pages.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[ocr_pdf] {pdf.name}: {n} pages, text={len(text_pages)}, ocr={len(ocr_pages)}, unresolved={len(unresolved)}, lang={lang}")
    return 3 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

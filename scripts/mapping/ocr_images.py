#!/usr/bin/env python3
"""OCR a folder of page images (photos/scans) as draft text per page (specs/11 §2.2).

Usage: ocr_images.py <image_dir> <out_dir> [--lang nld+eng] [--no-ocr]

Pages are the images in natural filename order (H16_16.1_2.jpg < H16_16.1_10.jpg); extensions
jpg/jpeg/png/tif/tiff. Writes <out_dir>/page-NNN.txt per image (tesseract draft, empty with --no-ocr
or without tesseract) and <out_dir>/pages.json
  {"pages": N, "files": [{"page": 1, "file": "<name>", "chars": n}, ...], "ocr_pages": [...],
   "unresolved_pages": [...], "lang": "...", "method": "ocr"}.
Photos (skew, show-through of the reverse page) give noisy OCR: the ingest agent reads every image
itself and overwrites page-NNN.txt with its transcription; the draft is only a reading aid.
Exit code 3 when pages are unresolved (no tesseract or --no-ocr), like ocr_pdf.py.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def natural_key(name: str) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    src, out = Path(argv[1]), Path(argv[2])
    lang = argv[argv.index("--lang") + 1] if "--lang" in argv else "nld+eng"
    no_ocr = "--no-ocr" in argv
    images = sorted((p for p in src.iterdir() if p.is_file() and p.suffix.lower() in EXTS),
                    key=lambda p: natural_key(p.name))
    if not images:
        print(f"[ocr_images] no images in {src}")
        return 2
    out.mkdir(parents=True, exist_ok=True)
    tess = None if no_ocr else shutil.which("tesseract")
    if tess:
        langs = run(["tesseract", "--list-langs"]).split()
        wanted = [l for l in lang.split("+") if l in langs] or (["eng"] if "eng" in langs else [])
        lang = "+".join(wanted) if wanted else None
    files, ocr_pages, unresolved = [], [], []
    for i, img in enumerate(images, start=1):
        txt = ""
        if tess and lang:
            txt = run(["tesseract", str(img), "-", "-l", lang])
            ocr_pages.append(i)
        else:
            unresolved.append(i)
        (out / f"page-{i:03d}.txt").write_text(txt, encoding="utf-8")
        files.append({"page": i, "file": img.name, "chars": len(txt.strip())})
    meta = {"pages": len(images), "source_dir": str(src), "files": files, "ocr_pages": ocr_pages,
            "unresolved_pages": unresolved, "lang": lang, "method": "ocr"}
    (out / "pages.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[ocr_images] {src.name}: {len(images)} images, ocr={len(ocr_pages)}, unresolved={len(unresolved)}, lang={lang}")
    return 3 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

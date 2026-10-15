#!/usr/bin/env python3
"""Outline all PDF fonts while keeping the output as a vector PDF."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
except ImportError as exc:
    raise SystemExit(
        "pypdf is required. Install the packages listed in requirements.txt."
    ) from exc


PAINT_OPS = {b"S", b"s", b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*"}
TEXT_SHOW_OPS = {b"Tj", b"TJ", b"'", b'"'}


def resolve(obj):
    return obj.get_object() if hasattr(obj, "get_object") else obj


def resource_fonts(resources, seen=None):
    seen = seen or set()
    resources = resolve(resources)
    if not resources or id(resources) in seen:
        return []
    seen.add(id(resources))
    found = []
    fonts = resolve(resources.get("/Font")) if "/Font" in resources else None
    if fonts:
        found.extend(str(name) for name in fonts.keys())
    xobjects = resolve(resources.get("/XObject")) if "/XObject" in resources else None
    if xobjects:
        for xobject in xobjects.values():
            xobject = resolve(xobject)
            if xobject.get("/Subtype") == "/Form" and "/Resources" in xobject:
                found.extend(resource_fonts(xobject["/Resources"], seen))
    return found


def analyze_content(container, reader, resources=None, seen=None):
    seen = seen or set()
    container = resolve(container)
    if id(container) in seen:
        return {"vector_paints": 0, "images": 0, "text_shows": 0}
    seen.add(id(container))
    resources = resolve(resources or container.get("/Resources"))
    counts = {"vector_paints": 0, "images": 0, "text_shows": 0}
    try:
        stream = ContentStream(container.get_contents() if hasattr(container, "get_contents") else container, reader)
    except Exception:
        return counts
    xobjects = resolve(resources.get("/XObject")) if resources and "/XObject" in resources else {}
    for operands, operator in stream.operations:
        if operator in PAINT_OPS:
            counts["vector_paints"] += 1
        elif operator in TEXT_SHOW_OPS:
            counts["text_shows"] += 1
        elif operator == b"Do" and operands:
            target = resolve(xobjects.get(operands[0])) if xobjects else None
            if target is None:
                continue
            subtype = target.get("/Subtype")
            if subtype == "/Image":
                counts["images"] += 1
            elif subtype == "/Form":
                nested = analyze_content(target, reader, target.get("/Resources", resources), seen)
                for key in counts:
                    counts[key] += nested[key]
    return counts


def page_geometry(page):
    box = page.mediabox
    return (
        round(float(box.width), 3),
        round(float(box.height), 3),
        int(page.get("/Rotate", 0)) % 360,
    )


def find_ghostscript(explicit=None):
    candidates = [explicit, shutil.which("gs"), "/opt/homebrew/bin/gs", "/usr/local/bin/gs"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise SystemExit("Ghostscript was not found. Install it or pass --gs /path/to/gs.")


def validate(source_path, output_path):
    source = PdfReader(str(source_path))
    output = PdfReader(str(output_path))
    if len(source.pages) != len(output.pages):
        raise RuntimeError(f"Page count changed: {len(source.pages)} -> {len(output.pages)}")

    pages = []
    for index, (before, after) in enumerate(zip(source.pages, output.pages), start=1):
        before_geometry = page_geometry(before)
        after_geometry = page_geometry(after)
        if before_geometry != after_geometry:
            raise RuntimeError(
                f"Page {index} geometry changed: {before_geometry} -> {after_geometry}"
            )
        fonts = resource_fonts(after.get("/Resources"))
        if fonts:
            raise RuntimeError(f"Page {index} still contains font resources: {fonts}")
        content = analyze_content(after, output)
        if content["text_shows"]:
            raise RuntimeError(f"Page {index} still contains text-show operators")
        if content["vector_paints"] == 0:
            raise RuntimeError(
                f"Page {index} has no vector paint operations; it may be raster-only or flattened"
            )
        pages.append({"page": index, "geometry": after_geometry, **content})
    return pages


def preflight(source_path):
    reader = PdfReader(str(source_path))
    pages = []
    total_fonts = 0
    total_text_shows = 0
    total_vector_paints = 0
    for index, page in enumerate(reader.pages, start=1):
        fonts = sorted(set(resource_fonts(page.get("/Resources"))))
        content = analyze_content(page, reader)
        total_fonts += len(fonts)
        total_text_shows += content["text_shows"]
        total_vector_paints += content["vector_paints"]
        pages.append(
            {
                "page": index,
                "font_resources": fonts,
                **content,
            }
        )
    if total_vector_paints == 0:
        classification = "raster-only-or-no-editable-vector"
    elif total_fonts or total_text_shows:
        classification = "live-text-or-font-resources"
    else:
        classification = "already-outlined-vector"
    return {
        "classification": classification,
        "font_resource_count": total_fonts,
        "text_show_operators": total_text_shows,
        "vector_paint_operations": total_vector_paints,
        "pages": pages,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("output_pdf", type=Path)
    parser.add_argument("--gs", help="Path to Ghostscript executable")
    parser.add_argument("--force", action="store_true", help="Replace an existing output")
    args = parser.parse_args()

    source = args.input_pdf.expanduser().resolve()
    output = args.output_pdf.expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"Input PDF not found: {source}")
    if source == output:
        raise SystemExit("Input and output paths must differ.")
    if output.exists() and not args.force:
        raise SystemExit(f"Output exists; use --force to replace it: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    source_report = preflight(source)
    if source_report["classification"] == "raster-only-or-no-editable-vector":
        raise SystemExit(
            "Source PDF has no meaningful vector paint operations. Outlining fonts cannot recover separable vector objects."
        )

    with tempfile.NamedTemporaryFile(suffix=".pdf", dir=output.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        if source_report["classification"] == "already-outlined-vector":
            shutil.copy2(source, temporary)
            conversion = "preserved-without-redistillation"
        else:
            gs = find_ghostscript(args.gs)
            command = [
                gs,
                "-q",
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                "-sDEVICE=pdfwrite",
                "-dNoOutputFonts",
                "-dPDFSETTINGS=/prepress",
                "-dCompatibilityLevel=1.6",
                "-dAutoRotatePages=/None",
                f"-sOutputFile={temporary}",
                str(source),
            ]
            subprocess.run(command, check=True)
            conversion = "ghostscript-font-outlining"
        pages = validate(source, temporary)
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()

    print(
        json.dumps(
            {
                "input_preflight": source_report,
                "conversion": conversion,
                "output": str(output),
                "output_font_resources": 0,
                "output_pages": pages,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

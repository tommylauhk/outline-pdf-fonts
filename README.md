# Outline PDF Fonts

An agent-agnostic skill and standalone Python tool that converts live text in a PDF into vector outlines while preserving vector artwork. The output remains a PDF.

It is designed for missing-font handoffs. The tool does not convert a PDF into an AI file; it creates a font-independent PDF that can be opened manually in Illustrator.

## What it does

1. Preflights the source before changing anything.
2. Detects font resources, live text operators, vector paint operations, and images.
3. Converts fonts to vector outlines with Ghostscript only when needed.
4. Leaves an already-outlined vector PDF byte-for-byte unchanged.
5. Rejects raster-only PDFs instead of claiming that a flat image is editable artwork.
6. Validates page count, geometry, font removal, text removal, and retained vector paint operations.

## What it does not promise

- It does not recreate original named Illustrator layers when that metadata is absent from the PDF.
- It does not vectorize raster artwork.
- It does not convert the document to AI, EPS, or another format.
- It does not make artwork print-ready without the printer's dieline, bleed, spot-color, trapping, and overprint requirements.

## Requirements

- Python 3.9 or newer
- [`pypdf`](https://pypi.org/project/pypdf/)
- [Ghostscript](https://www.ghostscript.com/)

Install the Python dependency:

```bash
python3 -m pip install -r requirements.txt
```

Install Ghostscript with your operating system's package manager, or pass its executable explicitly with `--gs`.

## Standalone usage

```bash
python3 scripts/outline_pdf_fonts.py input.pdf output_outlined.pdf
```

Options:

```text
--gs /path/to/gs   Use a specific Ghostscript executable
--force            Replace an existing output file
```

The command prints a JSON report containing the input classification and per-page validation results.

## Use with an AI agent

Place this repository in your agent's skills directory, or give the agent access to this folder. The agent must be able to read `SKILL.md` and run local Python commands. Skill locations and invocation syntax vary by agent.

Example request:

```text
Use the outline-pdf-fonts skill to outline the fonts in this PDF while keeping the output as a PDF.
```

The conversion script has no dependency on Codex, OpenAI, Claude, Cursor, or any other specific agent. `agents/openai.yaml` is optional UI metadata for compatible OpenAI clients; other agents can ignore it.

## Illustrator handoff

The canonical output is the outlined PDF. To create an AI document:

1. Open the outlined PDF manually in Adobe Illustrator.
2. Inspect that objects are separable and the artwork is visually correct.
3. Use **Save As > Adobe Illustrator**.

Avoid EPS conversion, raster export, renaming a PDF to `.ai`, or placing the entire page as one image.

## Licensing

This repository is MIT licensed. Ghostscript and `pypdf` are separate third-party projects with their own licenses; users are responsible for complying with those licenses.


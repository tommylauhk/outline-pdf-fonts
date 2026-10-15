---
name: outline-pdf-fonts
description: Outline live PDF text while keeping the output as a PDF and preserving vector objects for object-level editing. Use for missing-font PDF handoffs; this does not convert a PDF to AI or EPS.
---

# Outline PDF Fonts

Create a font-independent PDF by converting every font to outlines. The output format must remain PDF and keep vector objects separable.

## Required outcome

- Preserve page count, page dimensions, rotation, artwork position, color appearance, transparency, and embedded images as closely as possible.
- Remove all PDF font resources. Text editability is intentionally lost; glyph shapes remain as vector outlines.
- Preserve vector paths and object structure. Illustrator may show separate objects or nested groups. Original named Illustrator layers are only preserved when the source PDF contains compatible layer metadata; never promise named layers without checking.
- Treat the outlined PDF as the canonical deliverable. If a native `.ai` file is required, instruct the user to open this PDF manually in Illustrator and use **Save As > Adobe Illustrator**. Do not synthesize an `.ai` by renaming a PDF, converting to EPS, or rasterizing.

## Workflow

1. Preflight the source PDF before changing it: page count, dimensions, rotation, color intent, font resources, text-show operators, and whether meaningful vector artwork exists. Classify it as live-text, already-outlined vector, mixed vector/image, or raster-only.
2. Render every source page for a visual baseline.
3. Run `scripts/outline_pdf_fonts.py` with Python 3, `pypdf`, and a local Ghostscript executable. When the source already has no fonts or live-text operators, the script preserves it without Ghostscript redistillation.
4. Render every output page and compare it visually with the baseline. Check fine text, barcodes, nutrition tables, logos, clipping masks, overprints, gradients, transparency, and page edges.
5. Report the exact validation results. Say “object-level editable” rather than “layered” unless named layers were actually verified in Illustrator.

Example:

```bash
python3 scripts/outline_pdf_fonts.py input.pdf output_outlined.pdf
```

Install the Python dependency from `requirements.txt`. The script discovers `gs` from `PATH` and common Homebrew locations; pass `--gs /path/to/gs` when needed.

## Hard stops

- If the source is already a single full-page raster image with no meaningful vector paint operations, state that separable Illustrator objects cannot be recovered from that PDF. Do not claim success.
- If fonts remain, page geometry changes, any page loses vector paint operations, or visual comparison shows a material difference, do not deliver the output as complete.
- Never use `eps2write`, image export, screenshots, or a placed full-page image as the conversion method for this request.
- Never automate Illustrator multi-page assembly unless the user explicitly requests it and the result can be opened and inspected safely. A successful save alone is not proof of editable structure.

## Delivery language

State clearly:

- Fonts are outlined and no font resources remain.
- The PDF retains separable vector objects when opened in Illustrator.
- Text is no longer editable as text.
- Named layer preservation is verified, unverified, or unavailable.
- Print readiness still depends on the printer's dieline, bleed, spot-color, trapping, and overprint requirements.


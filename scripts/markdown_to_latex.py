#!/usr/bin/env python3
r"""Convert SoA markdown output into robust LaTeX using Pandoc.

Features:
- Supports Pandoc markdown extensions for tables/math/figures.
- Normalizes citations from LaTeX-style ``\cite{...}`` to Pandoc style ``[@...]``.
- Optionally auto-generates a BibTeX file from ``artifacts/extracted/*.json``.
- Optionally ensures Pandoc is installed via pypandoc.
"""

from __future__ import annotations

import argparse
import binascii
import json
import re
import struct
import sys
import zlib
from pathlib import Path
from typing import Iterable

import pypandoc

RGB = tuple[int, int, int]


def _extract_ids_from_cites(text: str) -> set[str]:
    ids: set[str] = set()

    def _is_crossref_label(label: str) -> bool:
        return label.startswith(("fig:", "tbl:", "tab:", "eq:", "sec:"))

    # Pandoc citations: [@id; @id2]
    for bracket in re.findall(r"\[([^\]]+)\]", text):
        for cid in re.findall(r"@([A-Za-z0-9_:\-.]+)", bracket):
            if not _is_crossref_label(cid):
                ids.add(cid)

    # Bare inline @id
    for cid in re.findall(r"(?<!\w)@([A-Za-z0-9_:\-.]+)", text):
        if not _is_crossref_label(cid):
            ids.add(cid)

    # LaTeX style \cite{a,b}
    for chunk in re.findall(r"\\cite\{([^}]+)\}", text):
        for cid in chunk.split(","):
            clean = cid.strip()
            if clean:
                ids.add(clean)

    return ids


def normalize_citations(markdown_text: str) -> str:
    """Normalize citation markers to Pandoc format for reliable citeproc."""

    def repl(match: re.Match[str]) -> str:
        raw = match.group(1)
        items = [x.strip() for x in raw.split(",") if x.strip()]
        if not items:
            return ""
        return "[" + "; ".join(f"@{x}" for x in items) + "]"

    # Convert LaTeX cites to Pandoc cites.
    text = re.sub(r"\\cite\{([^}]+)\}", repl, markdown_text)

    # Convert cross-reference shorthand to explicit LaTeX refs, avoiding citeproc confusion.
    text = re.sub(r"(?<!\w)@(fig:[A-Za-z0-9_\-.]+)", r"\\ref{\1}", text)
    text = re.sub(r"(?<!\w)@(tbl:[A-Za-z0-9_\-.]+)", r"\\ref{\1}", text)
    text = re.sub(r"(?<!\w)@(tab:[A-Za-z0-9_\-.]+)", r"\\ref{\1}", text)
    text = re.sub(r"(?<!\w)@(eq:[A-Za-z0-9_\-.]+)", r"\\ref{\1}", text)
    text = re.sub(r"(?<!\w)@(sec:[A-Za-z0-9_\-.]+)", r"\\ref{\1}", text)
    return text


def _load_known_ids(extracted_dir: Path | None) -> set[str]:
    """Load known paper IDs from extracted metadata files."""
    if extracted_dir is None or not extracted_dir.exists():
        return set()

    known_ids: set[str] = set()
    for fp in sorted(extracted_dir.glob("*.json")):
        known_ids.add(fp.stem)
        try:
            obj = json.loads(fp.read_text(encoding="utf-8"))
            pid = str(obj.get("paper_id") or "").strip()
            if pid:
                known_ids.add(pid)
        except Exception:
            continue

    return {i for i in known_ids if i}


def _autocite_bare_ids(markdown_text: str, known_ids: set[str]) -> str:
    """Wrap standalone paper IDs in Pandoc citation markers when missing."""
    text = markdown_text
    if not known_ids:
        return text

    # Replace longer IDs first to avoid partial overlaps.
    sorted_ids = sorted(known_ids, key=len, reverse=True)

    for pid in sorted_ids:
        escaped = re.escape(pid)

        # Skip IDs that are already inside a citation token like @paper_id.
        pattern = re.compile(rf"(?<![@A-Za-z0-9_:\-.])({escaped})(?![A-Za-z0-9_:\-.])")

        def repl(match: re.Match[str]) -> str:
            start = match.start(1)
            end = match.end(1)

            # Avoid wrapping URL/path fragments and markdown image/link targets.
            left = text[max(0, start - 6):start]
            right = text[end:end + 6]
            if "http" in left.lower() or "/" in left or "/" in right:
                return match.group(1)

            return f"[@{match.group(1)}]"

        text = pattern.sub(repl, text)

    return text


def _parse_year(raw: object) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    m = re.search(r"(19|20)\d{2}", text)
    if not m:
        return None
    year = int(m.group(0))
    if 1900 <= year <= 2100:
        return year
    return None


def _collect_year_counts(extracted_dir: Path | None) -> dict[int, int]:
    counts: dict[int, int] = {}
    if extracted_dir is None or not extracted_dir.exists():
        return counts

    for fp in sorted(extracted_dir.glob("*.json")):
        try:
            obj = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue

        year = _parse_year(obj.get("year"))
        if year is None:
            year = _parse_year((obj.get("extracted_facts") or {}).get("year"))
        if year is None:
            continue
        counts[year] = counts.get(year, 0) + 1

    return counts


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    body = chunk_type + payload
    crc = binascii.crc32(body) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", crc)


def _write_png_rgb(path: Path, pixels: list[list[RGB]]) -> None:
    """Write an RGB PNG without external dependencies."""
    height = len(pixels)
    width = len(pixels[0]) if height else 0
    if width <= 0 or height <= 0:
        raise ValueError("PNG dimensions must be positive")

    raw = bytearray()
    for row in pixels:
        raw.append(0)  # Filter type 0 (None)
        for r, g, b in row:
            raw.extend((r, g, b))

    compressed = zlib.compress(bytes(raw), level=9)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    data = b"".join([
        _png_chunk(b"IHDR", ihdr),
        _png_chunk(b"IDAT", compressed),
        _png_chunk(b"IEND", b""),
    ])

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(signature + data)


def _generate_year_distribution_figure(
    extracted_dir: Path | None,
    output_fig_path: Path,
) -> tuple[Path | None, dict[int, int]]:
    """Create a small publication-year bar chart PNG from extracted metadata."""
    counts = _collect_year_counts(extracted_dir)
    if not counts:
        return None, counts

    years = sorted(counts.keys())
    values = [counts[y] for y in years]

    width = 960
    height = 540
    margin_left = 80
    margin_right = 40
    margin_top = 40
    margin_bottom = 80

    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    max_val = max(values) if values else 1
    bar_gap = max(6, int(plot_w * 0.01))
    bar_w = max(10, int((plot_w - bar_gap * (len(values) + 1)) / max(1, len(values))))

    white: RGB = (255, 255, 255)
    axis: RGB = (50, 50, 50)
    bar: RGB = (52, 113, 176)
    grid: RGB = (226, 232, 240)

    pixels: list[list[RGB]] = [[white for _ in range(width)] for _ in range(height)]

    x0 = margin_left
    y0 = margin_top + plot_h

    # Horizontal grid lines.
    for i in range(0, 6):
        y = margin_top + int(plot_h * i / 5)
        for x in range(margin_left, margin_left + plot_w + 1):
            pixels[y][x] = grid

    # Axes.
    for x in range(margin_left, margin_left + plot_w + 1):
        pixels[y0][x] = axis
    for y in range(margin_top, margin_top + plot_h + 1):
        pixels[y][x0] = axis

    # Bars.
    cursor = margin_left + bar_gap
    for v in values:
        h = int((v / max_val) * (plot_h - 4))
        top = y0 - h
        for x in range(cursor, min(cursor + bar_w, margin_left + plot_w)):
            for y in range(max(margin_top, top), y0):
                pixels[y][x] = bar
        cursor += bar_w + bar_gap

    _write_png_rgb(output_fig_path, pixels)
    return output_fig_path, counts


def _inject_figure_if_missing(markdown_text: str, extracted_dir: Path | None, markdown_dir: Path) -> str:
    """Ensure markdown includes at least one concrete figure with a real asset path."""
    has_figure = re.search(r"!\[[^\]]*\]\([^\)]+\)", markdown_text) is not None
    if has_figure:
        return markdown_text

    fig_path_abs = markdown_dir / "figures" / "publication_year_distribution.png"
    fig_path, counts = _generate_year_distribution_figure(extracted_dir, fig_path_abs)
    if fig_path is None:
        return markdown_text

    rel_path = fig_path.relative_to(markdown_dir).as_posix()
    years = sorted(counts)
    year_span = f"{years[0]}-{years[-1]}" if years else "unknown"
    total = sum(counts.values())

    figure_block = (
        "\n\n"
        "## Visual Evidence\n\n"
        f"![Publication year distribution across included studies (n={total}, years {year_span}).]"
        f"({rel_path}){{#fig:year_distribution width=85%}}\n\n"
        "Figure \\ref{fig:year_distribution} summarizes the temporal spread of the included corpus.\n"
    )

    intro_match = re.search(r"(?mi)^##\s+Introduction\b.*$", markdown_text)
    if intro_match:
        insert_at = intro_match.end()
        return markdown_text[:insert_at] + "\n" + figure_block + markdown_text[insert_at:]
    return markdown_text + figure_block


def preprocess_markdown(markdown_text: str, extracted_dir: Path | None, markdown_dir: Path) -> str:
    """Apply publication-focused normalization before Pandoc conversion."""
    text = normalize_citations(markdown_text)
    known_ids = _load_known_ids(extracted_dir)
    text = _autocite_bare_ids(text, known_ids)
    text = _inject_figure_if_missing(text, extracted_dir, markdown_dir)
    return text


def _safe_bib_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_:\-.]", "_", value)


def _bibtex_escape(value: str) -> str:
    return value.replace("{", "\\{").replace("}", "\\}")


def _load_extracted_metadata(extracted_dir: Path) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    if not extracted_dir.exists():
        return entries

    for fp in sorted(extracted_dir.glob("*.json")):
        try:
            obj = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue

        pid = str(obj.get("paper_id") or fp.stem)
        title = str(obj.get("title") or pid)

        authors = obj.get("authors", "")
        if isinstance(authors, list):
            author_txt = " and ".join(str(a) for a in authors if str(a).strip())
        else:
            author_txt = str(authors or "Unknown")

        year_raw = obj.get("year")
        year = str(year_raw) if year_raw is not None else "2025"
        venue = str(obj.get("venue") or obj.get("journal") or "Unknown venue")

        entries[_safe_bib_id(pid)] = {
            "id": _safe_bib_id(pid),
            "title": title,
            "author": author_txt,
            "year": year,
            "howpublished": venue,
        }

    return entries


def build_bibtex(ids: Iterable[str], extracted_dir: Path | None = None) -> str:
    """Build a BibTeX string covering all citation IDs.

    If extracted metadata exists, use it. Otherwise create minimal placeholder entries.
    """
    ids_set = {_safe_bib_id(i) for i in ids if i.strip()}

    meta: dict[str, dict[str, str]] = {}
    if extracted_dir is not None:
        meta = _load_extracted_metadata(extracted_dir)

    lines: list[str] = []
    for cid in sorted(ids_set):
        m = meta.get(cid)
        if m is None:
            m = {
                "id": cid,
                "title": cid,
                "author": "Unknown",
                "year": "2025",
                "howpublished": "Unspecified",
            }

        lines.extend([
            f"@misc{{{m['id']},",
            f"  title = {{{_bibtex_escape(m['title'])}}},",
            f"  author = {{{_bibtex_escape(m['author'])}}},",
            f"  year = {{{_bibtex_escape(m['year'])}}},",
            f"  howpublished = {{{_bibtex_escape(m['howpublished'])}}}",
            "}",
            "",
        ])

    return "\n".join(lines).strip() + "\n"


def ensure_pandoc_if_requested(ensure: bool) -> None:
    if not ensure:
        return
    try:
        pypandoc.get_pandoc_version()
    except OSError:
        pypandoc.download_pandoc()


def convert_markdown_to_latex(
    markdown_path: Path,
    latex_path: Path,
    bibliography_path: Path | None = None,
    extracted_dir_for_auto_bib: Path | None = None,
    ensure_pandoc: bool = False,
    standalone: bool = True,
) -> Path:
    ensure_pandoc_if_requested(ensure_pandoc)

    if not markdown_path.exists():
        raise FileNotFoundError(f"Markdown input not found: {markdown_path}")

    raw_md = markdown_path.read_text(encoding="utf-8", errors="ignore")
    md = preprocess_markdown(
        markdown_text=raw_md,
        extracted_dir=extracted_dir_for_auto_bib,
        markdown_dir=markdown_path.parent,
    )

    # Keep canonical markdown synchronized with normalized/injected content.
    if md != raw_md:
        markdown_path.write_text(md, encoding="utf-8")

    citation_ids = _extract_ids_from_cites(md)

    if bibliography_path is None and citation_ids:
        bib_text = build_bibtex(citation_ids, extracted_dir_for_auto_bib)
        # Keep bibliography path local and stable so BibTeX can resolve it reliably.
        bibliography_path = latex_path.parent / "refs.bib"
        bibliography_path.write_text(bib_text, encoding="utf-8")

    args = [
        "--from=markdown+pipe_tables+grid_tables+table_captions+fenced_divs+raw_tex+tex_math_dollars+implicit_figures",
        "--to=latex",
    ]

    if standalone:
        args.append("--standalone")

    if bibliography_path is not None:
        bib_abs = bibliography_path.resolve().as_posix()
        args.extend(["--natbib", f"--bibliography={bib_abs}"])

    # Keep generated LaTeX predictable and paper-like.
    args.extend([
        "--number-sections",
        "--toc",
        "--toc-depth=2",
        "--top-level-division=section",
        "--variable=geometry:margin=1in",
        "--variable=fontsize:11pt",
        "--variable=linestretch:1.15",
        "--metadata=title:State of the Art Review",
        "--metadata=author:SOA-CLI",
    ])

    latex = pypandoc.convert_text(md, to="latex", format="md", extra_args=args)

    latex_path.parent.mkdir(parents=True, exist_ok=True)
    latex_path.write_text(latex, encoding="utf-8")

    return latex_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert markdown SoA into LaTeX")
    parser.add_argument("--input", required=True, help="Input markdown path")
    parser.add_argument("--output", required=True, help="Output latex path")
    parser.add_argument("--bibliography", default=None, help="Optional .bib path")
    parser.add_argument(
        "--auto-bib-from-extracted",
        default=None,
        help="Directory containing extracted paper json files for automatic bib generation",
    )
    parser.add_argument("--ensure-pandoc", action="store_true", help="Download pandoc if missing")
    parser.add_argument("--standalone", action="store_true", help="Generate standalone latex document")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    bib_path = Path(args.bibliography) if args.bibliography else None
    extracted_dir = Path(args.auto_bib_from_extracted) if args.auto_bib_from_extracted else None

    try:
        latex_path = convert_markdown_to_latex(
            markdown_path=in_path,
            latex_path=out_path,
            bibliography_path=bib_path,
            extracted_dir_for_auto_bib=extracted_dir,
            ensure_pandoc=args.ensure_pandoc,
            standalone=args.standalone,
        )
        print(f"[converter] Wrote LaTeX: {latex_path}")
    except Exception as exc:
        print(f"[converter] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

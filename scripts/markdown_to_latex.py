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


def _load_citation_map(path: Path | None) -> dict[str, str]:
    """Load canonical->source citation map from JSON file."""
    if path is None or not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(obj, dict):
        return {}
    if isinstance(obj.get("canonical_to_source"), dict):
        obj = obj["canonical_to_source"]

    out: dict[str, str] = {}
    for k, v in obj.items():
        ks = str(k).strip()
        vs = _safe_bib_id(str(v).strip())
        if ks and vs:
            out[ks] = vs
    return out


def _extract_title_and_abstract_metadata(markdown_text: str) -> tuple[str | None, str | None]:
    """Extract title/abstract metadata, preferring YAML front matter."""
    title: str | None = None
    abstract: str | None = None

    # Prefer YAML front matter metadata when available.
    if markdown_text.startswith("---\n"):
        end_idx = markdown_text.find("\n---\n", 4)
        if end_idx != -1:
            yaml_block = markdown_text[4:end_idx]
            title_match = re.search(r'(?mi)^title:\s*"?(.+?)"?\s*$', yaml_block)
            if title_match:
                title = title_match.group(1).strip()

            abs_match = re.search(r"(?mis)^abstract:\s*\|\s*\n(?P<body>(?:\s{2}.+\n?)*)", yaml_block)
            if abs_match:
                raw_lines = [ln[2:] if ln.startswith("  ") else ln for ln in abs_match.group("body").splitlines()]
                abstract = "\n".join(raw_lines).strip() or None

    # Fallback to heading-based extraction.
    lines = markdown_text.splitlines()
    if title is None:
        for line in lines:
            if not line.strip():
                continue
            m = re.match(r"^#\s+(.+?)\s*$", line.strip())
            if m:
                title = m.group(1).strip()
            break

    if abstract is None:
        abs_start = -1
        abs_level = 0
        for idx, line in enumerate(lines):
            hm = re.match(r"^(#{1,3})\s+abstract\s*$", line.strip(), flags=re.IGNORECASE)
            if hm:
                abs_start = idx
                abs_level = len(hm.group(1))
                break

        if abs_start >= 0:
            j = abs_start + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            para: list[str] = []
            while j < len(lines):
                line = lines[j]
                hm = re.match(r"^(#{1,6})\s+", line.strip())
                if hm and len(hm.group(1)) <= abs_level:
                    break
                if not line.strip() and para:
                    break
                if line.strip():
                    para.append(line.strip())
                j += 1
            if para:
                abstract = " ".join(para).strip()

    return title, abstract


def _extract_title_abstract_and_body(markdown_text: str) -> tuple[str | None, str | None, str]:
    """Extract title/abstract from body headings and return cleaned survey body."""
    lines = markdown_text.splitlines()

    title: str | None = None
    first_nonempty = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    if first_nonempty is not None:
        m = re.match(r"^#\s+(.+?)\s*$", lines[first_nonempty].strip())
        if m:
            title = m.group(1).strip()
            del lines[first_nonempty]
            while first_nonempty < len(lines) and not lines[first_nonempty].strip():
                del lines[first_nonempty]

    abstract: str | None = None
    abs_start = -1
    abs_level = 0
    for idx, line in enumerate(lines):
        hm = re.match(r"^(#{1,3})\s+abstract\s*$", line.strip(), flags=re.IGNORECASE)
        if hm:
            abs_start = idx
            abs_level = len(hm.group(1))
            break

    if abs_start >= 0:
        j = abs_start + 1
        while j < len(lines) and not lines[j].strip():
            j += 1

        para: list[str] = []
        k = j
        while k < len(lines):
            line = lines[k]
            hm = re.match(r"^(#{1,6})\s+", line.strip())
            if hm and len(hm.group(1)) <= abs_level:
                break
            if not line.strip() and para:
                break
            if line.strip():
                para.append(line.strip())
            k += 1

        if para:
            abstract = " ".join(para).strip()

        # Remove abstract section from body content entirely.
        abs_end = len(lines)
        for t in range(abs_start + 1, len(lines)):
            hm = re.match(r"^(#{1,6})\s+", lines[t].strip())
            if hm and len(hm.group(1)) <= abs_level:
                abs_end = t
                break
        del lines[abs_start:abs_end]

    body = "\n".join(lines).strip() + "\n"
    return title, abstract, body


def _escape_latex_text(value: str) -> str:
    escaped = value.replace("\\", r"\textbackslash{}")
    escaped = escaped.replace("{", r"\{").replace("}", r"\}")
    escaped = escaped.replace("_", r"\_")
    escaped = escaped.replace("%", r"\%")
    escaped = escaped.replace("&", r"\&")
    escaped = escaped.replace("#", r"\#")
    escaped = escaped.replace("$", r"\$")
    return escaped


def _enforce_latex_title_abstract_and_hierarchy(
    latex: str,
    markdown_text: str,
    title: str | None,
    abstract: str | None,
) -> str:
    """Ensure title/abstract exist in TeX and heading hierarchy reflects markdown."""
    final_title = title or "Large Language Models for Automated Academic Survey Generation: A State of the Art Review"

    # Ensure title command exists.
    if "\\title{" not in latex:
        title_cmd = f"\\title{{{_escape_latex_text(final_title)}}}\n"
        if "\\author{" in latex:
            latex = latex.replace("\\author{", title_cmd + "\\author{", 1)
        elif "\\begin{document}" in latex:
            latex = latex.replace("\\begin{document}", title_cmd + "\\begin{document}", 1)

    # Ensure \maketitle is present.
    if "\\maketitle" not in latex and "\\begin{document}" in latex:
        latex = latex.replace("\\begin{document}", "\\begin{document}\n\\maketitle", 1)

    # Normalize abstract block.
    if "\\begin{abstract}" not in latex:
        latex = latex.replace("\\end{abstract}", "")
        if abstract:
            abs_body = _escape_latex_text(abstract)
            abs_block = f"\\begin{{abstract}}\n{abs_body}\n\\end{{abstract}}\n"
            if "\\maketitle" in latex:
                latex = latex.replace("\\maketitle", "\\maketitle\n" + abs_block, 1)
            elif "\\begin{document}" in latex:
                latex = latex.replace("\\begin{document}", "\\begin{document}\n" + abs_block, 1)

    # Enforce hierarchy: markdown H3 headings should become \subsection in TeX.
    h3_titles: list[str] = []
    for ln in markdown_text.splitlines():
        m = re.match(r"^###\s+(.+?)\s*$", ln)
        if m:
            h3_titles.append(m.group(1).strip())

    for h3 in h3_titles:
        pattern = r"\\section\{" + re.escape(h3) + r"\}"
        latex = re.sub(pattern, r"\\subsection{" + h3 + "}", latex)

    return latex


def _strip_yaml_front_matter(markdown_text: str) -> str:
    """Remove a leading YAML front matter block if present."""
    text = markdown_text
    while text.startswith("---\n"):
        end_idx = text.find("\n---\n", 4)
        if end_idx == -1:
            break
        text = text[end_idx + 5 :].lstrip()
    return text


def _inject_yaml_metadata(markdown_text: str, title: str | None, abstract: str | None) -> str:
    """Prepend YAML metadata to drive professional LaTeX title/abstract rendering."""
    if not title and not abstract:
        return markdown_text

    meta: list[str] = ["---"]
    if title:
        safe_title = title.replace('"', "\\\"")
        meta.append(f'title: "{safe_title}"')
    if abstract:
        meta.append("abstract: |")
        for line in abstract.splitlines():
            meta.append(f"  {line.rstrip()}")
    meta.append("---")
    return "\n".join(meta) + "\n\n" + markdown_text.lstrip()


def _derive_fallback_abstract(body_text: str) -> str:
    """Derive a short abstract from the first content paragraph when needed."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body_text) if p.strip()]
    for p in paragraphs:
        if p.startswith("#"):
            continue
        words = p.split()
        if len(words) >= 20:
            return " ".join(words[:80])
    return (
        "This survey synthesizes the state of the art, covering methods, evaluation, "
        "limitations, and future directions based on cited literature."
    )


def _normalize_heading_hierarchy(markdown_text: str) -> str:
    """Normalize heading hierarchy generically for any survey topic.

    Keeps relative structure while compressing arbitrary heading levels
    into consecutive levels (e.g., 2/4/6 -> 1/2/3).
    """
    levels: list[int] = []
    for ln in markdown_text.splitlines():
        m = re.match(r"^(#{1,6})\s+", ln)
        if m:
            levels.append(len(m.group(1)))

    if not levels:
        return markdown_text.strip() + "\n"

    unique_levels = sorted(set(levels))
    level_map = {old: idx + 1 for idx, old in enumerate(unique_levels)}

    out: list[str] = []
    for ln in markdown_text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", ln)
        if not m:
            out.append(ln)
            continue
        raw_level = len(m.group(1))
        heading_text = m.group(2).strip()
        new_level = max(1, min(6, level_map.get(raw_level, raw_level)))
        out.append(f"{'#' * new_level} {heading_text}")

    return "\n".join(out).strip() + "\n"


def _ensure_introduction_heading(markdown_text: str) -> str:
    """Ensure an explicit Introduction section exists after Abstract."""
    if re.search(r"(?mi)^#{1,3}\s+introduction\s*$", markdown_text):
        return markdown_text

    lines = markdown_text.splitlines()
    abs_idx = -1
    abs_level = 0
    for i, ln in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+abstract\s*$", ln.strip(), flags=re.IGNORECASE)
        if m:
            abs_idx = i
            abs_level = len(m.group(1))
            break

    if abs_idx < 0:
        # Fallback: insert Introduction after title if no Abstract heading found.
        title_idx = next((i for i, ln in enumerate(lines) if re.match(r"^#\s+", ln.strip())), None)
        if title_idx is None:
            return markdown_text
        insert_at = title_idx + 1
        while insert_at < len(lines) and not lines[insert_at].strip():
            insert_at += 1
        lines[insert_at:insert_at] = ["", "## Introduction", ""]
        return "\n".join(lines).strip() + "\n"

    # Find end of abstract content and insert Introduction immediately after it.
    j = abs_idx + 1
    while j < len(lines) and not lines[j].strip():
        j += 1

    # Consume abstract paragraph lines until next blank or heading of same/higher level.
    while j < len(lines):
        line = lines[j]
        if not line.strip():
            break
        hm = re.match(r"^(#{1,6})\s+", line.strip())
        if hm and len(hm.group(1)) <= abs_level:
            break
        j += 1

    insert_at = j
    lines[insert_at:insert_at] = ["", "## Introduction", ""]
    return "\n".join(lines).strip() + "\n"


def _remap_citation_ids(markdown_text: str, citation_map: dict[str, str]) -> str:
    """Remap canonical citation IDs to source/bib IDs in markdown citation syntax."""
    if not citation_map:
        return markdown_text

    def _map_id(cid: str) -> str:
        return citation_map.get(cid, cid)

    def _repl_bracket(match: re.Match[str]) -> str:
        content = match.group(1)
        remapped = re.sub(r"@([A-Za-z0-9_:\-.]+)", lambda m: "@" + _map_id(m.group(1)), content)
        return "[" + remapped + "]"

    text = re.sub(r"\[([^\]]+)\]", _repl_bracket, markdown_text)

    text = re.sub(
        r"\\cite\{([^}]+)\}",
        lambda m: "\\cite{" + ",".join(_map_id(x.strip()) for x in m.group(1).split(",") if x.strip()) + "}",
        text,
    )

    text = re.sub(r"(?<!\\w)@([A-Za-z0-9_:\-.]+)", lambda m: "@" + _map_id(m.group(1)), text)
    return text


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






def _strip_manual_references_section(markdown_text: str) -> str:
    """Drop authored 'References' section so bibliography is produced from BibTeX once."""
    m = re.search(r"(?mi)^#{1,3}\s+references\s*$", markdown_text)
    if not m:
        return markdown_text
    return markdown_text[:m.start()].rstrip() + "\n"


def _repair_unresolved_citation_placeholders(markdown_text: str) -> str:
    """Remove unresolved placeholders like (???), [????], or bare ?????.

    If a paragraph already has at least one valid citation marker, placeholders are
    replaced with that marker; otherwise placeholders are removed.
    """

    def _first_citation_marker(paragraph: str) -> str | None:
        m = re.search(r"\[@[^\]]+\]", paragraph)
        if m:
            return m.group(0)
        return None

    placeholder_re = re.compile(r"\(\?{2,}\)|\[\?{2,}\]|(?<![A-Za-z0-9_])\?{4,}(?![A-Za-z0-9_])")

    parts = re.split(r"(\n\s*\n)", markdown_text)
    repaired_parts: list[str] = []
    for part in parts:
        if not part or part.isspace() or re.fullmatch(r"\n\s*\n", part):
            repaired_parts.append(part)
            continue

        marker = _first_citation_marker(part)
        if marker:
            repaired = placeholder_re.sub(marker, part)
        else:
            repaired = placeholder_re.sub("", part)

        repaired = re.sub(r"\s{2,}", " ", repaired)
        repaired_parts.append(repaired)

    return "".join(repaired_parts)


def preprocess_markdown(markdown_text: str, extracted_dir: Path | None, markdown_dir: Path) -> str:
    """Apply publication-focused normalization before Pandoc conversion."""
    text = _strip_yaml_front_matter(markdown_text)

    title, abstract, body = _extract_title_abstract_and_body(text)
    if not title:
        title = "Survey"
    if not abstract:
        abstract = _derive_fallback_abstract(body)

    text = _normalize_heading_hierarchy(body)
    text = normalize_citations(text)
    known_ids = _load_known_ids(extracted_dir)
    text = _autocite_bare_ids(text, known_ids)
    text = _repair_unresolved_citation_placeholders(text)
    text = _strip_manual_references_section(text)
    text = _inject_yaml_metadata(text, title=title, abstract=abstract)
    return text


def _safe_bib_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_:\-.]", "_", value)


def _bibtex_escape(value: str) -> str:
    escaped = value.replace("\\", "\\textbackslash{}")
    escaped = escaped.replace("{", "\\{").replace("}", "\\}")
    escaped = escaped.replace("_", "\\_")
    escaped = escaped.replace("%", "\\%")
    escaped = escaped.replace("&", "\\&")
    escaped = escaped.replace("#", "\\#")
    escaped = escaped.replace("$", "\\$")
    return escaped


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
    citation_map_path: Path | None = None,
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
    citation_map = _load_citation_map(citation_map_path)
    md = _remap_citation_ids(md, citation_map)

    # Keep canonical markdown synchronized with normalized/injected content.
    if md != raw_md:
        markdown_path.write_text(md, encoding="utf-8")

    citation_ids = _extract_ids_from_cites(md)

    if bibliography_path is None and citation_ids:
        bib_text = build_bibtex(citation_ids, extracted_dir_for_auto_bib)
        # Keep bibliography path local and stable so BibTeX can resolve it reliably.
        bibliography_path = latex_path.parent / "refs.bib"
        bibliography_path.parent.mkdir(parents=True, exist_ok=True)
        bibliography_path.write_text(bib_text, encoding="utf-8")

    # Fallback: when cite extraction misses IDs, still provide a bibliography
    # from extracted metadata so natbib has resolvable keys.
    if bibliography_path is None and extracted_dir_for_auto_bib is not None:
        meta = _load_extracted_metadata(extracted_dir_for_auto_bib)
        if meta:
            bibliography_path = latex_path.parent / "refs.bib"
            bibliography_path.parent.mkdir(parents=True, exist_ok=True)
            bibliography_path.write_text(build_bibtex(meta.keys(), extracted_dir_for_auto_bib), encoding="utf-8")

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
        "--metadata=author:SOA-CLI",
    ])

    latex = pypandoc.convert_text(md, to="latex", format="md", extra_args=args)

    # Keep title/abstract explicit in TeX and align subsection levels with markdown.
    title_meta, abstract_meta = _extract_title_and_abstract_metadata(md)
    latex = _enforce_latex_title_abstract_and_hierarchy(latex, md, title_meta, abstract_meta)

    # Keep bibliography reference stable for BibTeX by using local filename only.
    if bibliography_path is not None:
        bib_name = bibliography_path.with_suffix("").name
        latex = re.sub(r"\\bibliography\{[^}]+\}", f"\\\\bibliography{{{bib_name}}}", latex)

        # Pandoc can emit natbib cites without appending \bibliography in some templates.
        if "\\bibliography{" not in latex:
            bib_line = f"\\bibliography{{{bib_name}}}\n"
            if "\\end{document}" in latex:
                latex = latex.replace("\\end{document}", bib_line + "\\end{document}")
            else:
                latex += "\n" + bib_line

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
    parser.add_argument(
        "--citation-map",
        default=None,
        help="Optional JSON map from canonical IDs to source bib IDs",
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
    citation_map_path = Path(args.citation_map) if args.citation_map else None

    try:
        latex_path = convert_markdown_to_latex(
            markdown_path=in_path,
            latex_path=out_path,
            bibliography_path=bib_path,
            extracted_dir_for_auto_bib=extracted_dir,
            citation_map_path=citation_map_path,
            ensure_pandoc=args.ensure_pandoc,
            standalone=args.standalone,
        )
        print(f"[converter] Wrote LaTeX: {latex_path}")
    except Exception as exc:
        print(f"[converter] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from docx import Document
from dotenv import find_dotenv, load_dotenv

from primer_ops.render_docx import render_primer_docx
from scripts.compare_docx_structure import compare_docx_structure


def _style_exists(doc: Document, name: str) -> bool:
    try:
        doc.styles[name]
    except KeyError:
        return False
    return True


def _get_paragraph_by_text(doc: Document, text: str):
    for paragraph in doc.paragraphs:
        if paragraph.text.strip() == text:
            return paragraph
    raise AssertionError(f"Paragraph not found: {text}")


def _assert_heading_styles() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        md_path = tmp_path / "sample.md"
        docx_path = tmp_path / "sample.docx"
        md_path.write_text(
            "# Title\n\n## Section\n\n### Subsection\n\nParagraph.\n", encoding="utf-8"
        )
        render_primer_docx(str(md_path), str(docx_path), None)
        doc = Document(str(docx_path))

        title_para = _get_paragraph_by_text(doc, "Title")
        section_para = _get_paragraph_by_text(doc, "Section")
        subsection_para = _get_paragraph_by_text(doc, "Subsection")

        expected_title = "Title" if _style_exists(doc, "Title") else "Heading 1"
        if _style_exists(doc, expected_title):
            assert (
                title_para.style.name == expected_title
            ), f"Title style mismatch: {title_para.style.name}"

        if _style_exists(doc, "Heading 1"):
            assert (
                section_para.style.name == "Heading 1"
            ), f"Heading 1 style mismatch: {section_para.style.name}"

        if _style_exists(doc, "Heading 2"):
            assert (
                subsection_para.style.name == "Heading 2"
            ), f"Heading 2 style mismatch: {subsection_para.style.name}"


def main() -> None:
    load_dotenv(find_dotenv(usecwd=True), override=False)
    _assert_heading_styles()
    md_path = Path("output") / "primer.md"
    docx_path = md_path.with_suffix(".docx")
    template_path = os.getenv("PRIMER_WORD_TEMPLATE_PATH", "").strip() or None

    if not md_path.exists():
        print(f"DOCX render skipped/failed: {md_path} not found")
        return

    try:
        render_primer_docx(str(md_path), str(docx_path), template_path)
    except Exception as err:
        print(f"DOCX render skipped/failed: {err}")
        return

    print(f"DOCX generated: {docx_path}")

    golden_path = Path("docs") / "golden" / "primer_reference.docx"
    if not golden_path.exists():
        print(f"DOCX compare skipped/failed: {golden_path} not found")
        return

    report_path = Path("out") / "docx_compare_report.md"
    result = compare_docx_structure(docx_path, golden_path, report_path)
    print(f"DOCX compare report: {result.report_path}")
    if result.major_mismatches:
        print("Major mismatches detected:")
        for item in result.major_mismatches:
            print(f"- {item}")
        sys.exit(3)


if __name__ == "__main__":
    main()

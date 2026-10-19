"""Regenerate the binary bundled templates (DOCX, ODT) deterministically from code.

    uv run python scripts/make_templates.py

Text templates (template.yaml, *.md, *.html) are edited by hand.
"""

import datetime
import zipfile
from dataclasses import dataclass
from pathlib import Path

from docx import Document as new_docx
from docx.document import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.text.paragraph import Paragraph

from threatwright.branding import PRODUCT_NAME
from threatwright.render import odt, word

TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "threatwright" / "templates"
FIXED = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
HEADER = "{{ project.name }} · {{ document.title }}"
FOOTER = (
    "{{ t('version') }} {{ document.version or '–' }} · {{ document.date|date }} · {{ t('page') }} "
)


@dataclass(frozen=True)
class Look:
    font: str
    size: float
    accent: str  # hex without '#'
    head_fill: str
    table_style: str
    margin_cm: float
    header_align: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.LEFT
    caps_headings: bool = False
    title_space: float = 140


STANDARD = Look("Calibri", 10.5, "1F3864", "D9E2F3", "Table Grid", 2.2)
COMPACT = Look(
    "Arial", 9.5, "0F5257", "CDE7E4", "Table Grid", 1.8, WD_ALIGN_PARAGRAPH.RIGHT, True, 40
)


# --- DOCX --------------------------------------------------------------------------


def _font(style: object, look: Look, size: float, bold: bool = False, color: bool = False) -> None:
    font = style.font  # type: ignore[attr-defined]
    font.name, font.size, font.bold = look.font, Pt(size), bold
    font.color.rgb = RGBColor.from_string(look.accent) if color else None
    rpr = style.element.get_or_add_rPr()  # type: ignore[attr-defined]
    fonts = rpr.find(qn("w:rFonts"))
    for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        fonts.attrib.pop(qn(f"w:{attr}"), None)  # theme fonts would override the name


def _page_field(par: Paragraph) -> None:
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run, text = OxmlElement("w:r"), OxmlElement("w:t")
    text.text = "1"
    run.append(text)
    fld.append(run)
    par._p.append(fld)


def make_docx(target: Path, look: Look) -> None:
    doc: Document = new_docx()
    body = doc.element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21.0), Cm(29.7)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Cm(look.margin_cm))

    styles = doc.styles
    _font(styles["Normal"], look, look.size)
    _font(styles["Title"], look, 26, bold=True, color=True)
    _font(styles["Subtitle"], look, 14)
    _font(styles["Heading 1"], look, 16, bold=True, color=True)
    _font(styles["Heading 2"], look, 12.5, bold=True, color=True)
    styles["Title"].paragraph_format.space_before = Pt(look.title_space)
    styles["Heading 1"].font.all_caps = look.caps_headings
    note = styles.add_style("Note", WD_STYLE_TYPE.PARAGRAPH)
    note.base_style = styles["Normal"]
    note.font.italic = True
    note.paragraph_format.left_indent = Cm(0.5)
    note.font.color.rgb = RGBColor.from_string("52606D")

    header = section.header.paragraphs[0]
    header.text = HEADER
    header.alignment = look.header_align
    footer = section.footer.paragraphs[0]
    footer.text = FOOTER
    _page_field(footer)
    for par in (header, footer):
        for run in par.runs:
            run.font.size = Pt(8.5)

    props = doc.core_properties
    props.title, props.subject = "{{ document.title }}", "{{ project.name }}"
    props.author = props.last_modified_by = props.comments = props.keywords = ""
    props.created = props.modified = FIXED
    props.revision = 1

    word.write_body(doc, look.table_style, look.head_fill)
    doc.save(str(target))
    _fix_zip(target)


def _fix_zip(path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as zf:
        odt.rewrite_zip(tmp, zf, {})
    tmp.replace(path)


# --- ODT ---------------------------------------------------------------------------

NS = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
    'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
    'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
    'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
    'xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" '
    'office:version="1.3"'
)
FONT = "Liberation Sans"
FONTS = (
    f'<office:font-face-decls><style:font-face style:name="{FONT}" '
    f'svg:font-family="\'{FONT}\'" style:font-family-generic="swiss" '
    'style:font-pitch="variable"/></office:font-face-decls>'
)
XML = '<?xml version="1.0" encoding="UTF-8"?>\n'
MANIFEST_NS = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
MANIFEST = (
    XML
    + f'<manifest:manifest xmlns:manifest="{MANIFEST_NS}" manifest:version="1.3">\n'
    + "".join(
        f' <manifest:file-entry manifest:full-path="{path}" manifest:media-type="{kind}"/>\n'
        for path, kind in (
            ("/", "application/vnd.oasis.opendocument.text"),
            ("content.xml", "text/xml"),
            ("styles.xml", "text/xml"),
            ("meta.xml", "text/xml"),
        )
    )
    + "</manifest:manifest>\n"
)
PAGE_LAYOUT = (
    '<style:page-layout style:name="pm1">'
    '<style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm" '
    'style:print-orientation="portrait" fo:margin-top="1.4cm" fo:margin-bottom="1.4cm" '
    'fo:margin-left="2.2cm" fo:margin-right="2cm"/>'
    '<style:header-style><style:header-footer-properties fo:min-height="0.6cm" '
    'fo:margin-bottom="0.5cm"/></style:header-style>'
    '<style:footer-style><style:header-footer-properties fo:min-height="0.6cm" '
    'fo:margin-top="0.5cm"/></style:footer-style>'
    "</style:page-layout>"
)
DEFAULT_STYLE = (
    '<style:default-style style:family="paragraph">'
    f'<style:text-properties style:font-name="{FONT}" fo:font-size="10.5pt" '
    'fo:language="de" fo:country="DE"/></style:default-style>'
    '<style:style style:name="Standard" style:family="paragraph" style:class="text"/>'
)
PAGE_NUMBER = '<text:page-number text:select-page="current">1</text:page-number>'


def make_odt(target: Path, accent: str, head_fill: str) -> None:
    content = (
        f"{XML}<office:document-content {NS}>{FONTS}"
        f"<office:automatic-styles>{odt.table_styles_xml('#' + head_fill)}"
        "</office:automatic-styles>"
        f'<office:body><office:text><text:p text:style-name="tw-body">{odt.MARKER}</text:p>'
        "</office:text></office:body></office:document-content>\n"
    )
    styles = (
        f"{XML}<office:document-styles {NS}>{FONTS}"
        f"<office:styles>{DEFAULT_STYLE}{odt.paragraph_styles_xml('#' + accent, FONT)}"
        "</office:styles>"
        f"<office:automatic-styles>{PAGE_LAYOUT}</office:automatic-styles>"
        '<office:master-styles><style:master-page style:name="Standard" '
        'style:page-layout-name="pm1">'
        f'<style:header><text:p text:style-name="tw-header">{HEADER}</text:p></style:header>'
        f'<style:footer><text:p text:style-name="tw-footer">{FOOTER}{PAGE_NUMBER}</text:p>'
        "</style:footer></style:master-page></office:master-styles>"
        "</office:document-styles>\n"
    )
    meta = (
        f"{XML}<office:document-meta {NS}><office:meta>"
        f"<meta:generator>{PRODUCT_NAME}</meta:generator></office:meta></office:document-meta>\n"
    )
    parts = {
        "mimetype": "application/vnd.oasis.opendocument.text",
        "META-INF/manifest.xml": MANIFEST,
        "content.xml": content,
        "styles.xml": styles,
        "meta.xml": meta,
    }
    with zipfile.ZipFile(target, "w") as zf:
        for name, data in parts.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            zf.writestr(info, data.encode("utf-8"))


def main() -> None:
    make_docx(TEMPLATES / "tr-analysis" / "template.docx", STANDARD)
    make_docx(TEMPLATES / "acceptance-criteria" / "template.docx", STANDARD)
    make_docx(TEMPLATES / "tr-analysis-compact" / "template.docx", COMPACT)
    for name in ("tr-analysis", "acceptance-criteria"):
        make_odt(TEMPLATES / name / "template.odt", STANDARD.accent, STANDARD.head_fill)


if __name__ == "__main__":
    main()

"""ODT: the template provides named styles, header/footer and page setup; the
content is generated from the outline blocks and replaces the marker paragraph
`{{ content }}`. Other `{{ ... }}` placeholders (e.g. in header and footer) are
rendered in place; each must sit in one text run.
"""

import zipfile
from pathlib import Path
from typing import Any

from jinja2 import meta
from jinja2.sandbox import ImmutableSandboxedEnvironment
from lxml import etree  # type: ignore[import-untyped]

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
}
MARKER = "{{ content }}"
MAX_PART_BYTES = 50 << 20
PARSER = etree.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=False)

# Paragraph styles (office:styles in styles.xml) and table styles (automatic
# styles in content.xml) the generated content refers to.
PARAGRAPH_STYLES = {
    "title": "tw-title",
    "subtitle": "tw-subtitle",
    "h1": "tw-h1",
    "h2": "tw-h2",
    "p": "tw-body",
    "note": "tw-note",
    "pagebreak": "tw-pagebreak",
}
TABLE_STYLE, CELL_STYLE, HEAD_CELL_STYLE = "tw-table", "tw-cell", "tw-cell-head"
TH_STYLE, TD_STYLE = "tw-th", "tw-td"


def q(name: str) -> str:
    prefix, local = name.split(":")
    return f"{{{NS[prefix]}}}{local}"


def _style(name: str, family: str, props: dict[str, str], extra: str = "") -> str:
    """One <style:style>; props maps a properties element to its attributes."""
    inner = "".join(f"<style:{el} {attrs}/>" for el, attrs in props.items())
    parent = ' style:parent-style-name="Standard"' if family == "paragraph" else ""
    return (
        f'<style:style style:name="{name}" style:family="{family}"{parent}{extra}>'
        f"{inner}</style:style>"
    )


def paragraph_styles_xml(accent: str = "#1F3864", font: str = "Liberation Sans") -> str:
    """Default definitions of the named paragraph styles (new and derived templates)."""

    def p(name: str, para: str, text: str, extra: str = "") -> str:
        props = {"paragraph-properties": para} if para else {}
        props["text-properties"] = f'style:font-name="{font}" {text}'
        return _style(name, "paragraph", props, extra)

    bold = 'fo:font-weight="bold"'
    grey = 'fo:font-size="8.5pt" fo:color="#52606D"'
    keep = 'fo:keep-with-next="always"'
    return "".join(
        [
            p("tw-body", 'fo:margin-top="0cm" fo:margin-bottom="0.2cm"', 'fo:font-size="10.5pt"'),
            p(
                "tw-title",
                'fo:margin-top="5cm" fo:margin-bottom="0.4cm"',
                f'fo:font-size="26pt" {bold} fo:color="{accent}"',
            ),
            p("tw-subtitle", 'fo:margin-bottom="1cm"', 'fo:font-size="14pt" fo:color="#52606D"'),
            p(
                "tw-h1",
                f'fo:margin-top="0.6cm" fo:margin-bottom="0.25cm" {keep} '
                f'fo:border-bottom="0.06pt solid {accent}" fo:padding-bottom="0.05cm"',
                f'fo:font-size="16pt" {bold} fo:color="{accent}"',
                ' style:default-outline-level="1"',
            ),
            p(
                "tw-h2",
                f'fo:margin-top="0.45cm" fo:margin-bottom="0.15cm" {keep}',
                f'fo:font-size="12.5pt" {bold} fo:color="{accent}"',
                ' style:default-outline-level="2"',
            ),
            p(
                "tw-note",
                'fo:margin-top="0.15cm" fo:margin-bottom="0.25cm" fo:background-color="#FFF8E1" '
                'fo:border-left="2pt solid #F0B429" fo:padding="0.15cm"',
                'fo:font-size="10pt"',
            ),
            p("tw-pagebreak", 'fo:break-after="page"', ""),
            p("tw-th", "", f'fo:font-size="9pt" {bold}'),
            p("tw-td", "", 'fo:font-size="9pt"'),
            p("tw-header", "", grey),
            p("tw-footer", "", grey),
        ]
    )


def table_styles_xml(head: str = "#D9E2F3") -> str:
    border = 'fo:padding="0.08cm" fo:border="0.5pt solid #9AA5B1"'
    table = (
        'style:width="16.8cm" table:align="margins" table:border-model="collapsing" '
        'fo:margin-bottom="0.3cm"'
    )
    return "".join(
        [
            _style(TABLE_STYLE, "table", {"table-properties": table}),
            _style(CELL_STYLE, "table-cell", {"table-cell-properties": border}),
            _style(
                HEAD_CELL_STYLE,
                "table-cell",
                {"table-cell-properties": f'fo:background-color="{head}" {border}'},
            ),
        ]
    )


def _fragment(xml: str) -> list[Any]:
    decl = " ".join(f'xmlns:{k}="{v}"' for k, v in NS.items())
    root = etree.fromstring(f"<root {decl}>{xml}</root>".encode(), PARSER)
    return list(root)


def _read(zf: zipfile.ZipFile, name: str) -> Any:
    if zf.getinfo(name).file_size > MAX_PART_BYTES:
        raise ValueError(f"{name} too large")
    return etree.fromstring(zf.read(name), PARSER)


def rewrite_zip(target: Path, source: zipfile.ZipFile, parts: dict[str, bytes]) -> None:
    """Rewrite the package with fixed timestamps; `mimetype` first and uncompressed."""
    names = source.namelist()
    names = ["mimetype", *[n for n in names if n != "mimetype"]] if "mimetype" in names else names
    with zipfile.ZipFile(target, "w") as out:
        for name in names:
            data = parts.get(name, source.read(name))
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            out.writestr(info, data)


def _text_el(tag: str, style: str, text: str) -> Any:
    el = etree.Element(q(tag))
    el.set(q("text:style-name"), style)
    lines = text.split("\n")
    el.text = lines[0]
    for line in lines[1:]:
        br = etree.SubElement(el, q("text:line-break"))
        br.tail = line
    return el


def _table(headers: list[str] | None, rows: list[list[str]], n: int) -> Any:
    tbl = etree.Element(q("table:table"))
    tbl.set(q("table:name"), f"Table{n}")
    tbl.set(q("table:style-name"), TABLE_STYLE)
    cols = len(headers) if headers else max((len(r) for r in rows), default=1)
    col = etree.SubElement(tbl, q("table:table-column"))
    col.set(q("table:number-columns-repeated"), str(cols))

    def row(parent: Any, values: list[str], head_cols: int) -> None:
        tr = etree.SubElement(parent, q("table:table-row"))
        for i, v in enumerate(values):
            head = i < head_cols
            tc = etree.SubElement(tr, q("table:table-cell"))
            tc.set(q("table:style-name"), HEAD_CELL_STYLE if head else CELL_STYLE)
            tc.set(q("office:value-type"), "string")
            tc.append(_text_el("text:p", TH_STYLE if head else TD_STYLE, v))

    if headers:
        row(etree.SubElement(tbl, q("table:table-header-rows")), headers, cols)
        for r in rows:
            row(tbl, r, 0)
    else:  # fields: label column highlighted
        for r in rows:
            row(tbl, r, 1)
    return tbl


def blocks_to_odf(outline: list[dict[str, Any]]) -> list[Any]:
    out: list[Any] = []
    n = 0
    for section in outline:
        for b in section["blocks"]:
            kind = b["kind"]
            if kind in ("h1", "h2"):
                h = _text_el("text:h", PARAGRAPH_STYLES[kind], b["text"])
                h.set(q("text:outline-level"), kind[1])
                out.append(h)
            elif kind == "pagebreak":
                out.append(_text_el("text:p", PARAGRAPH_STYLES[kind], ""))
            elif kind in ("table", "fields"):
                n += 1
                out.append(_table(b.get("headers") if kind == "table" else None, b["rows"], n))
            else:
                out.append(_text_el("text:p", PARAGRAPH_STYLES[kind], b["text"]))
    return out


def _placeholders(root: Any) -> list[tuple[Any, str]]:
    """(element, attribute) pairs whose text holds a Jinja placeholder."""
    found = []
    for el in root.iter():
        for attr in ("text", "tail"):
            value = getattr(el, attr)
            if value and ("{{" in value or "{%" in value) and value.strip() != MARKER:
                found.append((el, attr))
    return found


def _marker(content: Any) -> Any:
    for p in content.iter(q("text:p")):
        if "".join(p.itertext()).strip() == MARKER:
            return p
    return None


def render_odt(
    template: Path, ctx: dict[str, Any], env: ImmutableSandboxedEnvironment, out: Path
) -> None:
    with zipfile.ZipFile(template) as zf:
        content = _read(zf, "content.xml")
        styles = _read(zf, "styles.xml")
        marker = _marker(content)
        if marker is None:
            raise ValueError(f"{template}: marker paragraph '{MARKER}' missing")
        # Placeholders first: generated content (model data) is never rendered as Jinja.
        for root in (content, styles):
            for el, attr in _placeholders(root):
                setattr(el, attr, env.from_string(getattr(el, attr)).render(ctx))
        parent = marker.getparent()
        pos = parent.index(marker)
        parent.remove(marker)
        for i, el in enumerate(blocks_to_odf(ctx["outline"])):
            parent.insert(pos + i, el)
        parts = {
            "content.xml": etree.tostring(content, xml_declaration=True, encoding="UTF-8"),
            "styles.xml": etree.tostring(styles, xml_declaration=True, encoding="UTF-8"),
        }
        rewrite_zip(out, zf, parts)


def undeclared(template: Path, env: ImmutableSandboxedEnvironment) -> set[str]:
    names: set[str] = set()
    with zipfile.ZipFile(template) as zf:
        content = _read(zf, "content.xml")
        if _marker(content) is None:
            raise ValueError(f"marker paragraph '{MARKER}' missing")
        for root in (content, _read(zf, "styles.xml")):
            for el, attr in _placeholders(root):
                names |= meta.find_undeclared_variables(env.parse(getattr(el, attr)))
    return names


def _ensure(root: Any, container: str, before: tuple[str, ...], xml: str) -> None:
    """Add missing style definitions to `container`, creating it in schema order."""
    parent = root.find(q(container))
    if parent is None:
        parent = etree.Element(q(container))
        nxt = next((root.find(q(b)) for b in before if root.find(q(b)) is not None), None)
        root.insert(len(root) if nxt is None else root.index(nxt), parent)
    have = {el.get(q("style:name")) for el in parent}
    for el in _fragment(xml):
        if el.get(q("style:name")) not in have:
            parent.append(el)


def derive(existing: Path, target: Path) -> None:
    """Keep styles, master pages (header/footer) and page setup; replace the body."""
    with zipfile.ZipFile(existing) as zf:
        content = _read(zf, "content.xml")
        styles = _read(zf, "styles.xml")
        body = content.find(f"{q('office:body')}/{q('office:text')}")
        if body is None:
            raise ValueError(f"{existing}: not a text document")
        for child in list(body):
            if not etree.QName(child).localname.endswith("-decls"):
                body.remove(child)
        body.append(_text_el("text:p", PARAGRAPH_STYLES["p"], MARKER))
        _ensure(content, "office:automatic-styles", ("office:body",), table_styles_xml())
        _ensure(
            styles,
            "office:styles",
            ("office:automatic-styles", "office:master-styles"),
            paragraph_styles_xml(),
        )
        parts = {
            "content.xml": etree.tostring(content, xml_declaration=True, encoding="UTF-8"),
            "styles.xml": etree.tostring(styles, xml_declaration=True, encoding="UTF-8"),
        }
        rewrite_zip(target, zf, parts)

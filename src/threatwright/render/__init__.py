"""Documents from templates: DOCX (docxtpl), ODT (named styles), Markdown, HTML, PDF."""

from threatwright.render.build import (
    OUT_FORMATS,
    OutFormat,
    RenderError,
    build_documents,
    check_template,
    derive_template,
    list_templates,
    preview_html,
)
from threatwright.render.context import KNOWN_VARIABLES, build_context
from threatwright.render.package import TemplateError
from threatwright.render.pdf import find_soffice

__all__ = [
    "KNOWN_VARIABLES",
    "OUT_FORMATS",
    "OutFormat",
    "RenderError",
    "TemplateError",
    "build_context",
    "build_documents",
    "check_template",
    "derive_template",
    "find_soffice",
    "list_templates",
    "preview_html",
]

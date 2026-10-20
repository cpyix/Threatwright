"""Fixed document wording in German and English, used via `t(key)` in templates."""

from typing import Literal

Lang = Literal["de", "en"]

LABELS: dict[str, tuple[str, str]] = {
    # sections
    "section.cover": ("Deckblatt", "Cover"),
    "section.scope": ("Untersuchungsgegenstand", "Scope"),
    "section.method": ("Methode", "Method"),
    "section.assets": ("Assets", "Assets"),
    "section.elements_and_flows": ("Elemente und Datenflüsse", "Elements and data flows"),
    "section.threats": ("Bedrohungen", "Threats"),
    "section.rejected": ("Verworfene Bedrohungen", "Rejected threats"),
    "section.measures": ("Maßnahmen", "Measures"),
    "section.traceability": ("Rückverfolgbarkeit", "Traceability"),
    "section.questions": ("Offene Fragen", "Open questions"),
    "section.risk_distribution": ("Risikoverteilung", "Risk distribution"),
    "section.changelog": ("Änderungshistorie", "Change history"),
    "section.custom_fields": ("Zusätzliche Angaben", "Additional fields"),
    "section.text": ("", ""),
    "section.decisions": ("Entscheidungspunkte", "Decision points"),
    "section.signatures": ("Freigabe", "Approval"),
    "section.acceptance_impact": (
        "Anhang: Auswirkung der Optionen auf bestehende Modelle",
        "Appendix: effect of the options on existing models",
    ),
    # columns and fields
    "col.id": ("ID", "ID"),
    "col.title": ("Titel", "Title"),
    "col.description": ("Beschreibung", "Description"),
    "col.asset_class": ("Klasse (TR)", "Class (TR)"),
    "col.c": ("C", "C"),
    "col.i": ("I", "I"),
    "col.a": ("A", "A"),
    "col.protects": ("Schützt", "Protects"),
    "col.configurations": ("Konfigurationen", "Configurations"),
    "col.kind": ("Art", "Kind"),
    "col.zone": ("Zone", "Zone"),
    "col.source": ("Quelle", "Source"),
    "col.target": ("Ziel", "Target"),
    "col.protocol": ("Protokoll", "Protocol"),
    "col.assets": ("Assets", "Assets"),
    "col.stride": ("STRIDE", "STRIDE"),
    "col.targets": ("Betroffene Elemente", "Targets"),
    "col.exposure": ("Exposition", "Exposure"),
    "col.impact": ("Impact", "Impact"),
    "col.risk": ("Risiko", "Risk"),
    "col.treatment": ("Bewertung", "Evaluation"),
    "col.measures": ("Maßnahmen", "Measures"),
    "col.residual_risk": ("Restrisiko", "Residual risk"),
    "col.cra_refs": ("CRA-Bezug", "CRA reference"),
    "col.status": ("Status", "Status"),
    "col.rationale": ("Begründung", "Rationale"),
    "col.by": ("Entschieden von", "Decided by"),
    "col.owner": ("Verantwortlich", "Owner"),
    "col.due": ("Fällig", "Due"),
    "col.evidence": ("Nachweis", "Evidence"),
    "col.threats": ("Bedrohungen", "Threats"),
    "col.threat": ("Bedrohung", "Threat"),
    "col.measure": ("Maßnahme", "Measure"),
    "col.measure_status": ("Status Maßnahme", "Measure status"),
    "col.cra": ("CRA-Anforderung", "CRA requirement"),
    "col.addressee": ("Adressat", "Addressee"),
    "col.answer": ("Antwort", "Answer"),
    "col.level": ("Stufe", "Level"),
    "col.label": ("Bezeichnung", "Label"),
    "col.count": ("Anzahl", "Count"),
    "col.version": ("Version", "Version"),
    "col.date": ("Datum", "Date"),
    "col.summary": ("Änderung", "Change"),
    "col.author": ("Autor", "Author"),
    "col.object": ("Objekt", "Object"),
    "col.field": ("Feld", "Field"),
    "col.value": ("Wert", "Value"),
    "col.interface": ("Schnittstelle", "Interface"),
    "col.access": ("Zugang", "Access"),
    "col.user": ("Nutzer", "User"),
    "col.option": ("Option", "Option"),
    "col.recommended": ("Empfohlen", "Recommended"),
    "col.current": ("Aktuell", "Current"),
    "col.to_treat": ("Zu behandelnde Bedrohungen", "Threats to treat"),
    "col.decision": ("Entscheidungspunkt", "Decision point"),
    "col.name": ("Name", "Name"),
    "col.role": ("Rolle", "Role"),
    "col.signature": ("Unterschrift", "Signature"),
    "col.model": ("Modell", "Model"),
    # field labels
    "project": ("Projekt", "Project"),
    "model": ("Modell", "Model"),
    "models": ("Modelle", "Models"),
    "version": ("Version", "Version"),
    "date": ("Stand", "Date"),
    "method": ("Methode", "Method"),
    "lifecycle": ("Lebenszyklusphase", "Lifecycle phase"),
    "configurations": ("Ausbaustufen / Varianten", "Configurations / variants"),
    "zones": ("Zonen", "Zones"),
    "elements": ("Elemente", "Elements"),
    "flows": ("Datenflüsse", "Data flows"),
    "scenario": ("Szenario", "Scenario"),
    "consequence": ("Auswirkung", "Consequence"),
    "safety_related": ("Sicherheitsbezug (Safety)", "Safety related"),
    "assessment": ("Bewertung", "Assessment"),
    "max_acceptable_risk": ("Akzeptanzgrenze", "Acceptance limit"),
    "rules": ("Angewandte Sonderregeln", "Applied special rules"),
    "acceptance": ("Akzeptanz", "Acceptance"),
    "questions": ("Offene Fragen", "Open questions"),
    "exposure_formula": ("Exposition", "Exposure"),
    "risk_matrix": ("Risikomatrix (Zeile: Exposition, Spalte: Impact)", "Risk matrix"),
    "special_rules": ("Sonderregeln", "Special rules"),
    "enabled": ("aktiv", "enabled"),
    "disabled": ("inaktiv", "disabled"),
    "approvers": ("Freigabeberechtigte", "Approvers"),
    "anyone": ("keine Einschränkung", "no restriction"),
    "none": ("Keine Einträge.", "No entries."),
    "yes": ("ja", "yes"),
    "no": ("nein", "no"),
    "unassessed": ("nicht bewertet", "not assessed"),
    "acceptable": ("akzeptabel", "acceptable"),
    "to_treat": ("zu behandeln", "to be treated"),
    "recommendation": ("Empfehlung", "Recommendation"),
    "decision": ("Entscheidung", "Decision"),
    "current_setting": ("Aktuelle Einstellung", "Current setting"),
    "rejected_note": (
        "Verworfene Bedrohungen sind in der Risikoverteilung nicht enthalten.",
        "Rejected threats are not included in the risk distribution.",
    ),
    "unassessed_count": ("Nicht bewertete Bedrohungen", "Threats not assessed"),
    "assessed_total": ("Bewertete Bedrohungen gesamt", "Assessed threats in total"),
    "exposure_text": (
        "Exposition = rund({offset} + Schnittstelle × Zugang × Nutzer × {scale}), "
        "kaufmännisch gerundet.",
        "Exposure = round({offset} + interface × access × user × {scale}), rounded half up.",
    ),
    "acceptance_text": (
        "Akzeptanzgrenze: Risiken bis einschließlich „{label}“ (Stufe {level}) sind "
        "akzeptabel; höhere Risiken müssen behandelt werden.",
        "Acceptance limit: risks up to and including “{label}” (level {level}) are "
        "acceptable; higher risks must be treated.",
    ),
    "matrix_note.inverted": (
        "Lesart der Risikomatrix: umgekehrt (inverted). Die Formel ergibt für die "
        "ungünstigste Umgebung die höchste Exposition, die abgedruckte Matrix der TR ordnet "
        "das höchste Risiko aber der Zeile „Environment 1“ zu. Die Matrix wird deshalb "
        "umgekehrt gelesen, sodass die höchste Exposition zum höchsten Risiko führt.",
        "Risk matrix reading: inverted. The formula yields the highest exposure for the "
        "worst environment, while the matrix printed in the TR assigns the highest risk to "
        "row “Environment 1”. The matrix is therefore read inverted, so the highest exposure "
        "leads to the highest risk.",
    ),
    "matrix_note.literal": (
        "Lesart der Risikomatrix: wörtlich (literal). Die Matrixzeile entspricht direkt der "
        "berechneten Exposition. Hinweis: Bei dieser Lesart führt die ungünstigste Umgebung "
        "nicht zum höchsten Risiko.",
        "Risk matrix reading: literal. The matrix row equals the computed exposure. Note: "
        "with this reading the worst environment does not lead to the highest risk.",
    ),
    "computed_note": (
        "Exposition, Risiko und Bewertung werden aus der Methodenkonfiguration berechnet und "
        "nicht gespeichert.",
        "Exposure, risk and evaluation are computed from the method configuration and are "
        "never stored.",
    ),
    # acceptance criteria decision document
    "decision.max_acceptable_risk": (
        "Höchste akzeptable Risikostufe",
        "Highest acceptable risk level",
    ),
    "decision.max_acceptable_risk.q": (
        "Bis zu welcher Risikostufe dürfen Risiken ohne weitere Maßnahmen akzeptiert werden?",
        "Up to which risk level may risks be accepted without further measures?",
    ),
    "decision.matrix_reading": ("Lesart der Risikomatrix", "Risk matrix reading"),
    "decision.matrix_reading.q": (
        "Wie wird die Zeile der Risikomatrix aus der Exposition bestimmt?",
        "How is the risk matrix row derived from the exposure?",
    ),
    "decision.rule.q": (
        "Soll diese Sonderregel angewendet werden?",
        "Shall this special rule be applied?",
    ),
    "decision.approvers": ("Freigabeberechtigte je Risikostufe", "Approvers per risk level"),
    "decision.approvers.q": (
        "Wer darf Risiken welcher Stufe akzeptieren?",
        "Who may accept risks of which level?",
    ),
    "option.inverted": ("umgekehrt (inverted)", "inverted"),
    "option.literal": ("wörtlich (literal)", "literal"),
    "option.enabled": ("anwenden", "apply"),
    "option.disabled": ("nicht anwenden", "do not apply"),
    "option.approvers_any": ("keine Einschränkung", "no restriction"),
    "option.approvers_named": ("Festlegung je Stufe", "defined per level"),
    "role.product": ("Produktverantwortung", "Product owner"),
    "role.security": ("Informationssicherheit", "Information security"),
    "acceptance_basis": (
        "Grundlage der Auswertung: {count} bewertete Bedrohungen in {models} Modell(en). "
        "Jede Option wurde mit sonst unveränderter Methode neu berechnet.",
        "Basis: {count} assessed threats in {models} model(s). Each option was re-evaluated "
        "with the method otherwise unchanged.",
    ),
    "tr_default": ("Voreinstellung der Methode", "Method default"),
    # enumerations
    "kind.process": ("Prozess", "Process"),
    "kind.device": ("Gerät", "Device"),
    "kind.datastore": ("Datenspeicher", "Data store"),
    "kind.external": ("Externes Element", "External element"),
    "threat_status.identified": ("identifiziert", "identified"),
    "threat_status.assessed": ("bewertet", "assessed"),
    "threat_status.treated": ("behandelt", "treated"),
    "threat_status.accepted": ("akzeptiert", "accepted"),
    "threat_status.rejected": ("verworfen", "rejected"),
    "measure_status.proposed": ("vorgeschlagen", "proposed"),
    "measure_status.decided": ("beschlossen", "decided"),
    "measure_status.in_progress": ("in Umsetzung", "in progress"),
    "measure_status.implemented": ("umgesetzt", "implemented"),
    "measure_kind.technical": ("technisch", "technical"),
    "measure_kind.organizational": ("organisatorisch", "organisational"),
    "measure_kind.design": ("konstruktiv", "design"),
    "measure_kind.user_information": ("Nutzerinformation", "user information"),
    "measure_kind.supply_chain": ("Lieferkette", "supply chain"),
    "question_status.open": ("offen", "open"),
    "question_status.answered": ("beantwortet", "answered"),
    "lifecycle.development": ("Entwicklung", "Development"),
    "lifecycle.post_market": ("nach dem Inverkehrbringen", "Post market"),
    "stride.S": ("Spoofing (Identitätsvortäuschung)", "Spoofing"),
    "stride.T": ("Tampering (Manipulation)", "Tampering"),
    "stride.R": ("Repudiation (Abstreitbarkeit)", "Repudiation"),
    "stride.I": ("Information Disclosure (Informationspreisgabe)", "Information disclosure"),
    "stride.D": ("Denial of Service (Dienstverweigerung)", "Denial of service"),
    "stride.E": ("Elevation of Privilege (Rechteausweitung)", "Elevation of privilege"),
    "page": ("Seite", "Page"),
    "note": ("Hinweis", "Note"),
}

MONTHS = {
    "de": "Januar Februar März April Mai Juni Juli August September Oktober November Dezember",
    "en": "January February March April May June July August September October November December",
}


def t(key: str, lang: Lang) -> str:
    """Label for `key`; unknown keys are returned unchanged so typos stay visible."""
    pair = LABELS.get(key)
    if pair is None:
        return key
    return pair[0] if lang == "de" else pair[1]

# Vorlagenreferenz: Dokumente erzeugen

Das Werkzeug erzeugt aus einem Projekt Dokumente in den Formaten DOCX, ODT, Markdown, HTML und PDF. Inhalt und Gliederung kommen aus **Vorlagenpaketen**. Layout, Schriften, Kopf- und Fußzeilen kommen aus der Vorlagendatei (Word- bzw. Writer-Dokument).

```text
threatwright build [--model main] [--template tr-analysis] [--format docx|odt|md|html|pdf] [--out build/]
threatwright template check templates/meine-vorlage
threatwright template derive Firmenvorlage.docx templates/meine-vorlage
```

Ohne Optionen erzeugt `build` alle aktiven Vorlagen für alle Modelle in allen Formaten der Vorlage, aber ohne PDF. Die Dateien landen in `<projekt>/build/`, z. B. `main-tr-analysis.docx` (Modell `main`) oder `acceptance-criteria.docx` (projektweite Vorlage).

## Mitgelieferte Vorlagen

| ID | Inhalt | Formate |
|---|---|---|
| `tr-analysis` | Bedrohungs- und Risikoanalyse nach BSI TR-03183-1, je Modell | DOCX, ODT, Markdown, HTML |
| `tr-analysis-compact` | Kurzfassung: Zusammenfassung, Risikoverteilung, Bedrohungen ohne Einzeldarstellung, Maßnahmen. Eigene Schrift und Farben, andere Reihenfolge, weniger Spalten | DOCX |
| `acceptance-criteria` | Risikoakzeptanzkriterien als Entscheidungsvorlage, projektweit | DOCX, ODT, Markdown |

Alle mitgelieferten Vorlagen sind neutral: kein Logo, kein Firmenname. Sie stehen unter CC BY 4.0 und dürfen als Grundlage für eigene Vorlagen dienen. PDF entsteht aus DOCX (sonst ODT), siehe [PDF](#pdf).

Die feste Beschriftung („Bedrohungen“, „zu behandeln“) folgt der Projektsprache (`language: de|en` in `threatwright.yaml`). Eine Vorlage kann die Sprache mit `language` festlegen.

### Entscheidungsvorlage Risikoakzeptanzkriterien

`acceptance-criteria` wird vollständig aus der Methodenkonfiguration erzeugt (siehe [Methodik](methodik.md)). Je Entscheidungspunkt zeigt sie die Optionen, die Empfehlung und die aktuelle Einstellung. Die Empfehlung ist die Voreinstellung der mitgelieferten Methode.

Entscheidungspunkte:
- höchste akzeptable Risikostufe,
- Lesart der Risikomatrix (`inverted` oder `literal`),
- jede Sonderregel (anwenden ja/nein),
- Freigabeberechtigte je Risikostufe.

Dazu kommen Unterschriftsfelder (Name, Rolle, Datum, Unterschrift) und ein Anhang. Der Anhang zeigt je Option, wie viele Bedrohungen der bestehenden Modelle behandelt werden müssten. Dafür bewertet das Werkzeug alle nicht verworfenen Bedrohungen mit einer veränderten Kopie der Methode neu; die übrigen Einstellungen bleiben dabei gleich.

## Vorlagenpaket

Ein Vorlagenpaket ist ein Ordner mit `template.yaml`, den Vorlagendateien und optional weiteren Dateien (z. B. einem Logo, das in der Word-Vorlage eingebettet ist).

| Ort | Bedeutung |
|---|---|
| mitgeliefert (`src/threatwright/templates/<id>/`) | Standardvorlagen |
| `<projekt>/templates/<id>/` | eigene Vorlagen; gleiche ID ersetzt die mitgelieferte |

Welche Vorlagen `build` verwendet, steht in `threatwright.yaml`:

```yaml
templates: [tr-analysis, firmenvorlage]   # leer oder fehlend: alle mitgelieferten
```

Mit `--template <id>` lässt sich jede vorhandene Vorlage einzeln erzeugen, auch wenn sie nicht in der Liste steht.

### template.yaml

```yaml
schema_version: 1
id: firmenvorlage            # = Ordnername; a-z, 0-9, . _ -
name: {de: Risikoanalyse, en: Risk analysis}
description: {de: ..., en: ...}   # optional
format: docx                 # docx | odt | md | html
file: template.docx          # Dateiname im Paket, keine Pfade
language: de                 # optional; sonst Projektsprache
scope: model                 # model (ein Dokument je Modell) | project (eines für das Projekt)
outline:
  - type: cover
  - type: method
  - type: threats
    columns: [id, title, risk, treatment, measures]
```

Mehrere Formate mit derselben Gliederung: statt `format`/`file` die Zuordnung `files` verwenden.

```yaml
files:
  docx: template.docx
  odt: template.odt
  md: template.md
  html: template.html
```

### Gliederung (`outline`)

Die Gliederung bestimmt Abschnitte und Reihenfolge, ohne Codeänderung. Jeder Eintrag hat einen `type` und optional:

| Schlüssel | Bedeutung |
|---|---|
| `enabled: false` | Abschnitt auslassen |
| `title` | eigene Überschrift, Text oder `{de: ..., en: ...}` |
| `columns` | Tabellenspalten in dieser Reihenfolge (siehe unten) |
| `flow_columns` | nur `elements_and_flows`: Spalten der Datenfluss-Tabelle |
| `details: false` | nur `threats`: keine Einzeldarstellung je Bedrohung, nur Tabelle |
| `text` | nur `text`: Freitext mit Platzhaltern, Text oder `{de: ..., en: ...}` |
| `roles` | nur `signatures`: eine Unterschriftszeile je Rolle |

Abschnittstypen und wählbare Spalten (Standardspalten **fett**):

| Typ | Inhalt | Spalten |
|---|---|---|
| `cover` | Titel, Projekt, Modell, Version, Stand, Methode, Lebenszyklus; danach Seitenumbruch | – |
| `scope` | Modellbeschreibung, Ausbaustufen / Varianten, Zonen mit Umgebung | – |
| `method` | Methode, Expositionsformel, **Hinweis zur Matrix-Lesart** (`inverted`/`literal`), **Akzeptanzgrenze**, wirksame Risikomatrix, Sonderregeln, Freigabeberechtigte | – |
| `assets` | Assets mit TR-Klasse und C/I/A-Impact (inkl. Vererbung und Verstärker) | **id, title, asset_class, c, i, a**, protects, configurations, description |
| `elements_and_flows` | Elemente und Datenflüsse | Elemente: **id, title, kind, zone, configurations**, description; Flüsse (`flow_columns`): **id, title, source, target, protocol, assets**, configurations, description |
| `threats` | Bedrohungen nach Risiko sortiert, danach je Bedrohung alle Angaben (STRIDE, Ziele, Bewertung, Exposition, Impact, Risiko, akzeptabel/zu behandeln, Maßnahmen, Restrisiko, CRA-Bezug, Status) | **id, title, stride, targets, risk, treatment, measures, status**, exposure, impact, residual_risk, cra_refs |
| `rejected` | verworfene Bedrohungen mit Begründung; nicht in der Risikoverteilung | **id, title, rationale, by**, stride, targets |
| `measures` | Maßnahmen mit Rückverweis auf Bedrohungen | **id, title, status, owner, evidence, threats**, kind, due, cra_refs |
| `traceability` | Bedrohung → Maßnahme → CRA-Anforderung | **threat, measure, measure_status, cra**, risk |
| `questions` | offene Fragen | **id, title, addressee, status, answer**, threats |
| `risk_distribution` | Anzahl je Risikostufe, akzeptabel/zu behandeln | **level, label, count, treatment** |
| `changelog` | Änderungshistorie der Modelle | **version, date, summary, author**, model |
| `custom_fields` | eigene Felder (`custom`) aller Objekte | **object, field, value** |
| `approvals` | Freigaben: akzeptierte und verworfene Bedrohungen mit Name, Rolle, Datum und Begründung, dazu der Git-Stand (Commit, Tag, nicht eingecheckte Änderungen) | **threat, status, by, role, date, rationale**, risk, model |
| `text` | Freitext | – |
| `decisions` | Entscheidungspunkte der Akzeptanzkriterien | – |
| `signatures` | Unterschriftstabelle | – |
| `acceptance_impact` | Anhang: zu behandelnde Bedrohungen je Option | – |

Beispiel Freitext:

```yaml
  - type: text
    title: {de: Zusammenfassung, en: Summary}
    text:
      de: |
        Für {{ model.title }} wurden {{ threats|length }} Bedrohungen betrachtet,
        davon {{ threats|selectattr("treatment", "equalto", "to_treat")|list|length }} zu behandeln.

        Stand: {{ document.date|date("long") }}.
```

Leerzeilen trennen Absätze.

## Formate

Alle mitgelieferten Vorlagen stellen dieselben **Blöcke** dar, die das Werkzeug aus der Gliederung erzeugt. Dadurch zeigen alle Formate denselben Inhalt. Jeder Abschnitt in `outline` hat eine Liste `blocks`:

| `kind` | Felder | Darstellung |
|---|---|---|
| `title`, `subtitle` | `text` | Dokumenttitel (Deckblatt) |
| `h1`, `h2` | `text` | Abschnitts- und Unterüberschrift |
| `p` | `text` | Absatz |
| `note` | `text` | hervorgehobener Hinweis |
| `table` | `headers`, `rows`, `columns` | Tabelle mit Kopfzeile |
| `fields` | `rows` (je `[Bezeichnung, Wert]`) | zweispaltige Angabentabelle |
| `pagebreak` | – | Seitenumbruch |

Eigene Vorlagen dürfen die Blöcke nutzen oder die Daten direkt verwenden (siehe [Datenmodell](#datenmodell)).

### DOCX (Word)

Platzhalter im Word-Dokument nach [docxtpl](https://docxtpl.readthedocs.io): `{{ variable }}`, `{% if %}`, sowie die Absatz-, Zeilen- und Zellen-Varianten `{%p ... %}`, `{%tr ... %}`, `{%tc ... %}`. Formatvorlagen, Kopf- und Fußzeile, Seitenränder und Logo kommen aus dem Dokument. Platzhalter funktionieren auch in Kopf- und Fußzeile.

Der Rumpf der mitgelieferten Vorlagen ist eine Schleife über die Blöcke. Die Formatvorlagen sind:

| Block | Formatvorlage |
|---|---|
| `title` | Title |
| `subtitle` | Subtitle |
| `h1` | Heading 1 (Überschrift 1) |
| `h2` | Heading 2 (Überschrift 2) |
| `p` | Normal (Standard) |
| `note` | Note |
| `table`, `fields` | Tabellenformat der Vorlage |

Das Aussehen ändern Sie, indem Sie diese Formatvorlagen in Word bearbeiten. Die Schleifenabsätze (`{%p ... %}`) müssen erhalten bleiben. Ein Logo fügen Sie einfach in die Kopfzeile ein.

Ein Platzhalter muss in Word in einem Zug geschrieben sein. Nachträglich teilweise formatierte Platzhalter kann Word in mehrere Textstücke zerlegen; docxtpl fügt sie meist wieder zusammen. Im Zweifel den Platzhalter neu tippen und mit `template check` prüfen.

### ODT (LibreOffice Writer)

Die ODT-Vorlage liefert benannte Formatvorlagen, Kopf-/Fußzeile, Seitenformat und Logo. Den Inhalt erzeugt das Werkzeug: Es ersetzt den Absatz, der nur `{{ content }}` enthält, durch die Blöcke aller Abschnitte. Andere Platzhalter wie `{{ project.name }}` werden an Ort und Stelle ersetzt (auch in Kopf- und Fußzeile). Jeder Platzhalter muss ohne Formatwechsel geschrieben sein.

| Block | Absatzvorlage |
|---|---|
| `title` / `subtitle` | `tw-title` / `tw-subtitle` |
| `h1` / `h2` | `tw-h1` / `tw-h2` (Gliederungsebene 1/2) |
| `p` | `tw-body` |
| `note` | `tw-note` |
| `pagebreak` | `tw-pagebreak` (Umbruch danach) |
| Tabellen | Tabelle `tw-table`, Zellen `tw-cell` / Kopfzellen `tw-cell-head`, Absätze `tw-th` / `tw-td` |

### Markdown und HTML

Jinja-Vorlagen. Die mitgelieferten Dateien enthalten nur `{% extends "document.md.j2" %}` bzw. `{% extends "document.html.j2" %}`. Das allgemeine Layout liegt in `src/threatwright/templates/_shared/` und steht jeder Vorlage zur Verfügung. Überschreibbare Blöcke: `header`, `content`, `footer` (Markdown) sowie `style` und `content` (HTML).

```jinja
{% extends "document.html.j2" %}
{% block style %}{{ super() }} h2 { color: #7a1f1f; }{% endblock %}
```

HTML ist zugleich die Vorschau in der Oberfläche. Die Datei ist in sich geschlossen: CSS steht inline, es gibt keine externen Ressourcen. Vorlagen ohne HTML-Datei zeigt die Vorschau im allgemeinen Layout.

### PDF

PDF wird aus dem DOCX- (sonst ODT-) Dokument mit einem lokal installierten **LibreOffice** erzeugt (`--format pdf`). Gesucht wird `soffice`/`libreoffice` im `PATH` sowie unter Windows in `Program Files` und `Program Files (x86)`, unter macOS in `/Applications/LibreOffice.app`. Fehlt LibreOffice, bricht `build` mit einem Hinweis ab; DOCX und ODT funktionieren weiterhin. Die Umwandlung läuft mit einem temporären LibreOffice-Profil und Zeitlimit. Das Werkzeug lädt nichts aus dem Netz.

## Datenmodell

Alle Werte werden bei jedem Erzeugen neu berechnet und nie gespeichert. Die Vorlage sieht nur einfache Daten: Texte, Zahlen, Listen, Datumswerte. `None` erscheint als „–“, wenn die Blöcke verwendet werden; in eigenen Platzhaltern hilft `{{ x or "–" }}`.

| Variable | Inhalt |
|---|---|
| `lang` | `de` oder `en` |
| `project` | `name`, `uuid`, `method`, `language`, `lifecycle`, `lifecycle_label` |
| `model` | aktuelles Modell (bei `scope: project`: `None`): `name`, `title`, `uuid`, `description`, `configurations[]` (`id`, `title`, `description`), `zones[]` (`id`, `title`, `description`, `interface`, `interface_label`, `access`, `access_label`, `user`, `user_label`), `changelog[]` |
| `models` | Liste aller Modelle im Dokument, Felder wie `model` |
| `document` | `title` (Name der Vorlage), `template` (ID), `scope`, `version` und `date` (jüngster Eintrag der Änderungshistorie), `generator` |
| `method` | `id`, `title`, `matrix_reading` (`inverted`/`literal`), `matrix_note`, `max_acceptable_risk`, `max_acceptable_label`, `acceptance_text`, `exposure_text`, `risk_levels[]` und `impact_levels[]` (`level`, `label`), `rules[]` (`id`, `label`, `enabled`, `source`, `max_acceptable_risk`, `impact_delta`), `approvers` ({Stufe: [Namen]}), `matrix[]` (`exposure`, `risks[]`, Lesart bereits angewendet) |
| `assets[]` | `id`, `title`, `description`, `asset_class`, `c`, `i`, `a` (Impact 1–5 oder `None`), `protects`, `configurations`, `custom`, `model` |
| `elements[]` | `id`, `title`, `description`, `kind`, `kind_label`, `zone`, `zone_title`, `configurations`, `custom` |
| `flows[]` | `id`, `title`, `source`, `source_title`, `target`, `target_title`, `protocol`, `bidirectional`, `assets`, `configurations`, `custom` |
| `threats[]` | alle **nicht verworfenen** Bedrohungen, nach Risiko absteigend (siehe unten) |
| `rejected_threats[]` | verworfene Bedrohungen, gleiche Felder |
| `measures[]` | `id`, `title`, `kind`, `kind_label`, `compensating`, `owner`, `status`, `status_label`, `due`, `evidence`, `cra_refs[]` (`id`, `title`), `threats[]` (Rückverweise `id`, `title`), `custom` |
| `questions[]` | `id`, `title`, `addressee`, `status`, `status_label`, `answer`, `threats[]` |
| `traceability[]` | je Bedrohung und Maßnahme: `threat`, `threat_title`, `risk`, `measure`, `measure_title`, `measure_status`, `cra_refs[]` |
| `risk_distribution[]` | je Risikostufe (hoch nach niedrig): `level`, `label`, `count`, `acceptable` |
| `unassessed_count` | Bedrohungen ohne vollständige Bewertung |
| `changelog[]` | Einträge aller Modelle, neueste zuerst: `version`, `date`, `summary`, `author`, `model` |
| `custom_fields[]` | `object`, `object_type`, `field`, `label`, `value` |
| `acceptance` | Entscheidungsvorlage: `threats_total`, `assessed_total`, `current_to_treat`, `approvers`, `decisions[]` (`id`, `title`, `question`, `note`, `current`, `recommended`, `options[]` mit `label`, `current`, `recommended`, `to_treat`) |
| `approvals[]` | akzeptierte und verworfene Bedrohungen, nach Datum: `threat`, `threat_title`, `model`, `decision` (`accepted`/`rejected`), `decision_label`, `risk`, `by`, `role`, `date`, `rationale` |
| `revision` | Git-Stand des Projekts beim Erzeugen: `commit`, `tag` (Tag auf dem Commit oder `None`), `dirty` (nicht eingecheckte Änderungen); `None` ohne Git |
| `outline[]` | Abschnitte der Gliederung: `type`, `title`, `blocks[]` |

Felder einer Bedrohung (`threats[]`):

| Feld | Inhalt |
|---|---|
| `id`, `uuid`, `title`, `description`, `model` | Kennung und Text |
| `stride`, `stride_names` | Kürzel (`["S", "T"]`) und ausgeschriebene Namen |
| `targets[]`, `assets[]`, `questions[]` | je `id`, `title` |
| `configurations`, `scenario`, `consequence`, `safety_related`, `cyber_cause`, `finding` | Angaben aus dem Modell |
| `assessment` | `interface`/`access`/`user` mit `*_label`, `impact`, `rationale` |
| `exposure`, `impact`, `risk` | berechnet (Impact inkl. Sonderregeln), `None` wenn unvollständig |
| `max_acceptable_risk`, `acceptable`, `rules` | wirksame Grenze, Ergebnis, angewandte Sonderregeln |
| `treatment`, `treatment_label` | `acceptable`, `to_treat` oder `unassessed` |
| `residual` | Restrisiko (gleiche Felder wie die Bewertung) oder `None` |
| `measures[]` | `id`, `title`, `status`, `status_label` |
| `cra_refs[]` | `id`, `title` (aus dem CRA-Katalog) |
| `status`, `status_label`, `acceptance`, `rejection`, `custom` | Status, Entscheidungen (`by`, `role`, `date`, `rationale`), eigene Felder |

### Filter und Funktionen

| Name | Beispiel | Ergebnis |
|---|---|---|
| `t(key)` / `key\|t` | `{{ t("section.threats") }}` | feste Beschriftung in Dokumentsprache („Bedrohungen“) |
| `sort_by_risk` | `{% for th in threats\|sort_by_risk %}` | höchstes Risiko zuerst, unbewertet zuletzt |
| `risk_label` | `{{ th.risk\|risk_label }}` | „mittel“ |
| `impact_label` | `{{ th.impact\|impact_label }}` | „hoch“ |
| `stride_names` | `{{ th.stride\|stride_names\|join(", ") }}` | „Spoofing (Identitätsvortäuschung), …“ |
| `date` | `{{ document.date\|date }}` / `\|date("long")` / `\|date("iso")` | „01.01.2026“ / „1. Januar 2026“ / „2026-01-01“ (en: „2026-01-01“ / „1 January 2026“) |
| `yesno` | `{{ th.safety_related\|yesno }}` | „ja“ / „nein“ |
| `md_cell` | `{{ th.title\|md_cell }}` | Text für eine Markdown-Tabellenzelle |

Dazu kommen die Standardfilter von Jinja (`length`, `join`, `selectattr`, `default`, …). Schlüssel für `t` stehen in `src/threatwright/render/labels.py`, z. B. `section.<typ>`, `col.<spalte>`, `acceptable`, `to_treat`.

Beispiel einer eigenen Markdown-Vorlage ohne Blöcke:

```jinja
# {{ document.title }} – {{ model.title }}

{{ method.matrix_note }}

| ID | Bedrohung | Risiko | Bewertung |
|---|---|---|---|
{% for th in threats|sort_by_risk %}
| {{ th.id }} | {{ th.title|md_cell }} | {{ th.risk|risk_label }} | {{ th.treatment_label }} |
{% endfor %}
```

## Sicherheit

Vorlagen werden wie fremder Code behandelt. Sie laufen ausschließlich in einer abgeschotteten Jinja-Umgebung (Sandbox). Zugriffe auf Python-Interna (`__class__` u. ä.), das Verändern von Daten und das Einbinden von Dateien außerhalb des Vorlagenordners schlagen fehl. Unbekannte Variablen führen zu einem Fehler statt zu leerem Text. Texte aus dem Modell werden nie als Vorlage ausgewertet; in HTML werden sie maskiert.

## Vorlage prüfen

`threatwright template check <ordner>` meldet:
- Fehler in `template.yaml` (fehlende Felder, unbekannte Abschnittstypen oder Spalten, Dateinamen mit Pfadanteil),
- Syntaxfehler und unbekannte Filter in Markdown-, HTML- und Freitext-Vorlagen,
- unbekannte Variablen in allen Formaten (bei DOCX inkl. Kopf- und Fußzeile, bei ODT inkl. fehlendem `{{ content }}`-Absatz).

## Eigene Vorlage aus einem Firmendokument ableiten

```text
threatwright template derive Firmenvorlage.docx templates/firmenvorlage
```

Der Assistent übernimmt Formatvorlagen, Kopf- und Fußzeile (z. B. Logo) und Seitenformat des Dokuments. Den Inhalt ersetzt er durch die Standardgliederung mit Platzhaltern. Fehlende Formatvorlagen (`Note`, `Heading 1` …) bzw. `tw-*`-Vorlagen in ODT legt er an. Er schreibt außerdem `template.yaml`; der Ordnername wird zur Vorlagen-ID. Ein vorhandenes `template.yaml` wird nie überschrieben.

Danach:
1. Formatvorlagen und Kopfzeile in Word/Writer anpassen, Platzhalter wie `{{ project.name }}` in die Kopfzeile setzen.
2. Gliederung in `template.yaml` anpassen.
3. `threatwright template check templates/firmenvorlage` ausführen.
4. Die ID in `templates:` in `threatwright.yaml` eintragen.

## Reproduzierbarkeit

Datum und Version eines Dokuments stammen aus der Änderungshistorie des Modells (`changelog` in `model.yaml`), nie aus der Uhrzeit. Bei unveränderten Eingaben erzeugt `build` byteweise identische Markdown-, HTML-, DOCX- und ODT-Dateien; Zeitstempel in den ZIP-Containern sind fest. Zu den Eingaben zählt auch der Git-Stand (`revision`), den der Abschnitt `approvals` zeigt. Für PDF gilt das nicht, weil LibreOffice eigene Metadaten schreibt.

Die mitgelieferten DOCX/ODT-Dateien erzeugt `uv run python scripts/make_templates.py` aus Code. Änderungen am Layout gehören dorthin, nicht in die Binärdateien.

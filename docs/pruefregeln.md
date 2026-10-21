# Prüfregeln

`threatwright validate [pfad] [--strict] [--format text|json|junit|sarif] [-o datei]`

Exit-Codes:
- `0`: keine Fehler
- `1`: Fehler gefunden, mit `--strict` zählen auch Warnungen
- `2`: Der Ordner ist kein Projekt.

Die Oberfläche zeigt dieselben Meldungen, weil sie dieselbe Prüfung aufruft.

## Fehler

| Code | Bedeutung |
|---|---|
| `schema` | Datei verletzt das Schema (falscher Typ, unbekanntes Feld, ungültiges YAML) |
| `method-invalid` | Methode nicht gefunden oder `method-overrides.yaml` ungültig |
| `library-invalid` | aktivierte Bibliothek fehlt, ist ungültig oder verweist auf unbekannte IDs |
| `duplicate-uuid` | UUID kommt mehrfach vor (z. B. Datei kopiert) |
| `unresolved-ref` | Verweis auf eine ID, die es nicht gibt |
| `unresolved-text-ref` | ID im Fließtext (z. B. „siehe M-0042“), die es nicht gibt |
| `unknown-configuration` | Ausbaustufe / Variante ist im Modell nicht definiert |
| `unknown-zone` | Zone ist im Modell nicht definiert |
| `unknown-asset-class` | Asset-Klasse gibt es in der Methode nicht |
| `unknown-indicator-value` | Wert für Schnittstelle, Zugang oder Nutzer gibt es in der Methode nicht |
| `security-asset-without-protects` | Sicherheits-Asset ohne geschützte Assets, daher kein Impact ableitbar |
| `missing-rationale` | Verstärker, „nicht relevant“ oder „nicht anwendbar“ (CRA-Anforderung) ohne Begründung |
| `incomplete-assessment` | Status „bewertet“ oder höher, aber Bewertung unvollständig |
| `threat-without-measure` | offene Bedrohung ohne Maßnahme, Akzeptanz oder Verwerfung |
| `acceptance-without-rationale` | Akzeptanz ohne Begründung |
| `acceptance-not-allowed` | Risiko liegt über der Akzeptanzgrenze des Projekts |
| `acceptance-not-authorized` | Die Person darf diese Risikostufe nicht akzeptieren |
| `rejection-without-rationale` | Verwerfung ohne Begründung |
| `custom-required` | eigenes Pflichtfeld ist leer |
| `custom-invalid` | eigenes Feld hat einen ungültigen Wert |
| `sbom-missing` | Element nennt in `sbom` eine Datei, die es in `sbom/` nicht gibt |
| `sbom-invalid` | Datei in `sbom/` oder `vulnerabilities/` ist kein lesbares CycloneDX- bzw. CSAF-JSON |
| `vulnerability-untreated` | Eine Schwachstelle betrifft eine Komponente des Elements (Stand betroffen oder in Prüfung), aber keine Bedrohung des Modells nennt sie in `vulnerabilities` ([SBOM und Schwachstellen](sbom.md)) |

## Warnungen

| Code | Bedeutung |
|---|---|
| `coverage-gap` | Element oder Datenfluss hat für eine STRIDE-Kategorie keine Bedrohung und ist nicht als „nicht relevant“ markiert |
| `element-without-threat` | Element (außer externen Einheiten) ohne Bedrohung |
| `threat-without-target` | Bedrohung hängt an keinem Element oder Datenfluss |
| `measure-unreferenced` | Maßnahme ohne Bedrohung |
| `question-unreferenced` | offene Frage ohne Bezug |
| `not-a-cyber-risk` | Ursache ist laut Prüfregel kein Angriff, die Bedrohung ist aber nicht verworfen |
| `cyber-cause-unanswered` | Die Prüfregel „Ist das ein Cyberrisiko?“ ist nicht beantwortet |
| `residual-not-acceptable` | Restrisiko liegt über der Akzeptanzgrenze |
| `custom-unknown` | Feld ist nicht in `custom-fields.yaml` definiert |
| `library-outdated` | Die Bibliothek hat eine neuere Fassung des übernommenen Eintrags |
| `library-ref-unknown` | `library_ref` verweist auf einen Eintrag, den es nicht (mehr) gibt |
| `unknown-cra-ref` | CRA-Bezug ist nicht im CRA-Katalog |
| `cra-requirement-uncovered` | Grundlegende Anforderung aus CRA Anhang I ohne Bedrohung oder Maßnahme mit diesem CRA-Bezug und nicht in `cra_not_applicable` (`model.yaml`) begründet; erst geprüft, sobald das Modell Bedrohungen hat |
| `acceptance-undocumented` | Bei einer Akzeptanz fehlt Name (`by`), Rolle (`role`) oder Datum (`date`) der Freigabe |

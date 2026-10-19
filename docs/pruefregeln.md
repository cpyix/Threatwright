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
| `duplicate-uuid` | UUID kommt mehrfach vor (z. B. Datei kopiert) |
| `unresolved-ref` | Verweis auf eine ID, die es nicht gibt |
| `unresolved-text-ref` | ID im Fließtext (z. B. „siehe M-0042“), die es nicht gibt |
| `unknown-configuration` | Ausbaustufe ist im Modell nicht definiert |
| `unknown-zone` | Zone ist im Modell nicht definiert |
| `unknown-asset-class` | Asset-Klasse gibt es in der Methode nicht |
| `unknown-indicator-value` | Wert für Schnittstelle, Zugang oder Nutzer gibt es in der Methode nicht |
| `security-asset-without-protects` | Sicherheits-Asset ohne geschützte Assets, daher kein Impact ableitbar |
| `missing-rationale` | Verstärker oder „nicht relevant“ ohne Begründung |
| `incomplete-assessment` | Status „bewertet“ oder höher, aber Bewertung unvollständig |
| `threat-without-measure` | offene Bedrohung ohne Maßnahme, Akzeptanz oder Verwerfung |
| `acceptance-without-rationale` | Akzeptanz ohne Begründung |
| `acceptance-not-allowed` | Risiko liegt über der Akzeptanzgrenze des Projekts |
| `acceptance-not-authorized` | Die Person darf diese Risikostufe nicht akzeptieren |
| `rejection-without-rationale` | Verwerfung ohne Begründung |
| `custom-required` | eigenes Pflichtfeld ist leer |
| `custom-invalid` | eigenes Feld hat einen ungültigen Wert |

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

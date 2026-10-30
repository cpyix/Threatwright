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
| `evidence-missing` | Maßnahme verweist in `evidence_refs` auf eine Datei, die es unter `evidence/` nicht gibt |
| `sbom-missing` | Element nennt in `sbom` eine Datei, die es in `sbom/` nicht gibt |
| `sbom-invalid` | Datei in `sbom/` oder `vulnerabilities/` ist kein lesbares CycloneDX- bzw. CSAF-JSON |
| `vulnerability-untreated` | Eine Schwachstelle betrifft eine Komponente des Elements (Stand betroffen oder in Prüfung), aber keine Bedrohung des Modells nennt sie in `vulnerabilities` ([SBOM und Schwachstellen](sbom.md)) |
| `runs-on-invalid` | `runs_on` verweist auf ein Element, das es nicht gibt oder das kein Gerät (`device`) ist |
| `runs-on-cycle` | `runs_on` bildet einen Zyklus (Gerät A läuft auf B, B auf A) |
| `refines-unresolved` | `refines` (`<modell>/<id>`) verweist auf ein Modell oder Element, das es nicht gibt, oder auf das eigene Modell |
| `refines-multiple-parents` | Elemente eines Teilmodells verfeinern Elemente verschiedener Modelle; ein Teilmodell gehört zu genau einem Modell |
| `refines-cycle` | `refines` bildet über Modelle hinweg einen Zyklus |

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
| `implemented-without-evidence` | Maßnahme mit Status „umgesetzt“ ohne Nachweis: weder `evidence` (Text) noch `evidence_refs` (Datei oder Link) |
| `support-period-missing` | `support_until` in `threatwright.yaml` fehlt, obwohl das Projekt Bedrohungen hat oder `lifecycle: post_market` ist (CRA Art. 13 Abs. 8) |
| `support-period-ended` | Der Supportzeitraum (`support_until`) liegt in der Vergangenheit |
| `review-overdue` | Die nächste Überprüfung (`next_review`) liegt in der Vergangenheit |
| `acceptance-undocumented` | Bei einer Akzeptanz fehlt Name (`by`), Rolle (`role`) oder Datum (`date`) der Freigabe |
| `exposed-service-unauthenticated` | Dienst lauscht auf allen Interfaces (`listens_on.interfaces: all`), `authentication` ist `none`, `unknown` oder nicht gesetzt, und keine Bedrohung mit STRIDE S oder E hängt an diesem Element |
| `privilege-boundary-gap` | Datenfluss zwischen zwei Prozessen desselben Hosts mit unterschiedlichem Rechtekontext (`privilege`) ohne Bedrohung mit STRIDE S bzw. E am Fluss oder an der höher privilegierten Seite und nicht als „nicht relevant“ markiert. T, I und D prüft wie bei jedem Fluss `coverage-gap` |
| `host-takeover-understated` | Bedrohung mit STRIDE E auf einem Gerät (oder auf dem Element, das dieses Gerät per `refines` verfeinert): Ein Element, das auf dem Gerät läuft (`runs_on`), verarbeitet ein Asset mit höherem Impact als die Bedrohung, und die Bedrohung nennt das Asset nicht. Asset ergänzen oder Impact prüfen |
| `duplicate-assessment` | Dieselbe Bibliotheksbedrohung ist am verfeinerten Element und im Teilmodell bewertet; ein Risiko wird je Produkt nur einmal bewertet |
| `sbom-ref-invalid` | `sbom_ref.purl` ist keine Package-URL (`pkg:<typ>/<name>…`) oder `sbom_ref.cpe` kein CPE-2.3-Name (bzw. CPE-2.2-URI) |

## Teilmodelle und Abdeckung

Verfeinert ein Element eines Teilmodells per `refines` ein Element eines anderen Modells, zählen Bedrohungen für beide gemeinsam:
- `coverage-gap` und `element-without-threat` am verfeinerten Element sind erfüllt durch Bedrohungen am verfeinernden Element und an allem, was darauf läuft (`runs_on`).
- Umgekehrt zählen Bedrohungen am verfeinerten Element für das verfeinernde.
- `cra-requirement-uncovered` wird je Produkt geprüft (Modell und alle seine Teilmodelle) und nur am übergeordneten Modell gemeldet.

Hintergrund in der [Methodik](methodik.md#teilmodelle-und-rechtekontexte).

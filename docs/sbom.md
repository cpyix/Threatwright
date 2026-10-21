# SBOM und Schwachstellen

Der CRA verlangt, dass ein Produkt ohne bekannte ausnutzbare Schwachstellen auf den Markt kommt (Anhang I Teil I Nr. 2 a) und dass der Hersteller seine Komponenten erfasst und Schwachstellen behandelt (Anhang I Teil II). Threatwright verbindet dafür drei Dinge:

- **SBOM** je Element: Welche Software-Komponenten stecken in diesem Element?
- **Schwachstellenmeldungen**: Welche Schwachstelle betrifft welche Komponente, und wie ist der Stand?
- **Bedrohungen**: Jede Schwachstelle, die eine Komponente betrifft, wird als Bedrohung behandelt, bewertet und mit Maßnahmen versehen.

Alles läuft über Dateien im Projekt. Threatwright fragt keine Schwachstellendatenbank im Netz ab ([ADR-0007](adr/0007-local-first-no-network.md), [ADR-0016](adr/0016-sbom-and-vulnerabilities.md)). Die Meldungen erzeugen Sie mit Ihren eigenen Werkzeugen (Scanner, Lieferanten-Advisories, eigene VEX-Dokumente) und legen sie ins Projekt.

## Ordner und Formate

| Ordner | Inhalt | Formate |
|---|---|---|
| `sbom/` | SBOMs, je Element eine oder mehrere | CycloneDX JSON (`"bomFormat": "CycloneDX"`) |
| `vulnerabilities/` | Schwachstellenmeldungen | CycloneDX VEX/VDR JSON, CSAF 2.x JSON (`document.csaf_version`) |

Dateinamen: Buchstaben, Ziffern, `.`, `_`, `-`, Endung `.json`, z. B. `sbom/firmware-2.3.cdx.json`. Höchstens 32 MB je Datei. Enthält eine SBOM selbst einen Abschnitt `vulnerabilities` (z. B. aus einem Scanner), zählt er ebenfalls.

In der Oberfläche laden Sie die Dateien unter **Analyse → Schwachstellen** hoch; sie landen in den Ordnern oben. Eine Datei mit gleichem Namen wird ersetzt, etwa die SBOM einer neuen Firmware-Version.

## SBOM einem Element zuordnen

Im Element unter **SBOM-Dateien** die passende Datei wählen, oder in der YAML-Datei:

```yaml
# models/main/elements/E-0001.yaml
id: E-0001
title: Steuerung
kind: device
sbom: [firmware-2.3.cdx.json]
```

## Abgleich

Komponenten und Meldungen werden über die Package-URL (purl) abgeglichen, ohne Qualifier und Subpfad (`pkg:generic/openssl@3.0.1?arch=arm` gilt als `pkg:generic/openssl@3.0.1`). Die Version gehört zur purl. Eine Meldung für eine andere Version trifft also nicht.

Stand je Schwachstelle und Komponente:

| Stand | CycloneDX `analysis.state` | CSAF `product_status` |
|---|---|---|
| betroffen | `exploitable`, keine Analyse | `known_affected`, `first_affected`, `last_affected` |
| in Prüfung | `in_triage` | `under_investigation` |
| behoben | `resolved`, `resolved_with_pedigree` | `fixed`, `first_fixed` |
| nicht betroffen | `not_affected`, `false_positive` | `known_not_affected` |

Sagen mehrere Dateien etwas zur selben Schwachstelle und Komponente, gilt „nicht betroffen“ vor „behoben“ vor „in Prüfung“ vor „betroffen“. Typisch: Der Scanner meldet eine Schwachstelle ohne Analyse, Ihr VEX-Dokument stellt fest, dass der betroffene Code nicht erreichbar ist.

## Behandeln

Eine Schwachstelle mit dem Stand **betroffen** oder **in Prüfung** braucht eine Bedrohung im Modell, die sie unter `vulnerabilities` nennt. Sonst meldet `threatwright validate` den Fehler `vulnerability-untreated` am Element.

```yaml
# models/main/threats/T-0012.yaml
title: Bekannte Schwachstelle CVE-2024-0001 in OpenSSL
targets: [E-0001]
vulnerabilities: [CVE-2024-0001]
cyber_cause: true
cra_refs: [AI-I-2-a, AI-II-2]
```

Die Bedrohung wird wie jede andere bewertet und behandelt: Maßnahme (z. B. Update der Komponente), Restrisiko, oder begründete Akzeptanz. Die Schaltfläche **Bedrohung anlegen** in der Ansicht „Schwachstellen“ legt sie mit diesen Angaben vor.

Ist eine Schwachstelle behoben oder nicht betroffen, halten Sie das in einer Meldung fest (eigenes VEX-Dokument in `vulnerabilities/`), nicht in der Bedrohung.

## Befehle und Dokumente

```text
threatwright vulnerabilities mein-produkt   # Schwachstellen je Element; Exit-Code 1, wenn eine unbehandelt ist
threatwright validate mein-produkt          # enthält vulnerability-untreated, sbom-missing, sbom-invalid
```

Der Bericht `tr-analysis` enthält den Abschnitt „Bekannte Schwachstellen“ (Abschnittstyp `vulnerabilities`, siehe [Vorlagenreferenz](vorlagenreferenz.md)).

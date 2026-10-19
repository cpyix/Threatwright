# OSCAL-Import

Threatwright liest OSCAL-Dokumente ein, schreibt aber keine (ADR-0006). Unterstützt werden **Kataloge**, **Profile** und **Komponentendefinitionen** im **JSON**-Format nach OSCAL **1.2.3**. Die Schemas sind mitgeliefert; es gibt keine Netzwerkzugriffe.

```
threatwright oscal validate <datei.json>
threatwright oscal import <datei.json> --as catalog|profile|component
```

## Prüfung

- Nur JSON. XML- und YAML-Dateien werden mit einem Hinweis abgelehnt: vorher nach JSON konvertieren (z. B. mit dem NIST-Werkzeug `oscal-cli`).
- Höchstens 50 MB.
- Das Modell wird am obersten Schlüssel erkannt (`catalog`, `profile`, `component-definition`). Andere OSCAL-Modelle (SSP, Assessment, POA&M, Mapping) werden als „nicht unterstützt“ gemeldet, aber trotzdem gegen das Gesamtschema geprüft.
- Fehler werden mit Pfad im Dokument gemeldet, z. B. `catalog.groups.0.controls.3.id`.
- Dokumente mit älterer `oscal-version` (z. B. 1.1.3) werden gegen 1.2.3 geprüft.

## Katalog → Projektbibliothek

Ein Katalog wird zur Bibliothek `libraries/<name>/` im Projekt. Der Name entsteht aus dem Katalogtitel (Kleinbuchstaben, Umlaute umschrieben) oder wird beim Import vorgegeben.

```
libraries/bsi-methodik-grundschutz/
  library.yaml          # Version und Lizenz aus den Katalog-Metadaten
  measures/gc.1.1.yaml  # eine Datei je Control
  source/<datei>.json   # unveränderte Kopie des importierten Katalogs
```

Zum Aktivieren den Namen in `threatwright.yaml` unter `libraries:` eintragen.

Jedes Control – auch verschachtelte Controls (Erweiterungen) – wird eine Maßnahmenvorlage:

| Feld | Herkunft |
|---|---|
| `id` | Control-ID in Kleinbuchstaben (`GC.1.1` → `gc.1.1`) |
| `title` | Control-Titel, de = en (OSCAL-JSON kennt keine Dokumentsprache) |
| `description` | Text des `statement`-Teils mit Unterpunkten; Parameter werden durch ihren Wert ersetzt, sonst als `[Bezeichnung]` bzw. `[Auswahl a \| b]` angezeigt |
| `kind` | immer `organizational`; bei Bedarf in einer eigenen Bibliothek überschreiben |
| `category` | Gruppenpfad, z. B. `GC Governance und Compliance / GC.1 Grundlagen` |
| `oscal_ref` | Quelle (Titel + Version), Katalog-UUID, Control-ID |
| `controls` | `[{catalog_uuid, control_id}]` |
| `oscal_extra` | das vollständige Control ohne `id`, `title` und Unter-Controls; bei Unter-Controls zusätzlich `parent_control` |

Es geht nichts verloren: Aus `oscal_extra` lässt sich das Control wiederherstellen, und die Originaldatei liegt unter `source/`.

### Erneuter Import

- Gleicher Katalog: Die Dateien bleiben Byte für Byte gleich (kein Diff).
- Neue Katalogversion: Nur geänderte Controls erhalten eine höhere `rev`. `threatwright library update` und die Warnung `library-outdated` zeigen dann, welche übernommenen Maßnahmen betroffen sind. Entfallene Controls werden aus der Bibliothek entfernt.
- Eine von Hand angelegte Bibliothek gleichen Namens (ohne `source/`) wird nie überschrieben.

## Profil

Ein Profil wird als Auswahl nach `profiles/<name>.yaml` gespeichert:

```yaml
schema_version: 1
id: synthetic-field-profile
title: Synthetic field profile
version: '1.0'
oscal_ref: {source: Synthetic field profile 1.0, uuid: ...}
imports:
  - href: '#9a8b...'                 # Verweis aus dem Profil
    library: synthetic-arc-catalog   # aufgelöste Projektbibliothek oder null
    include_all: false
    include_controls: [ARC-1, ARC-9]
    exclude_controls: [ARC-1.1]
    missing_controls: [ARC-9]        # nur wenn aufgelöst: im Katalog nicht vorhanden
set_parameters:
  arc-1_prm1: [12 hours]
oscal_extra: {imports: ..., merge: ..., modify: ..., back-matter: ...}   # Original
```

Der Katalog muss vorher importiert sein. Zugeordnet wird über den Hash im `back-matter` des Profils, den Dateinamen oder den Titel der Ressource. Auswahlregeln mit `matching`-Mustern sowie `merge`/`modify` werden nur in `oscal_extra` aufbewahrt, nicht ausgewertet.

## Komponentendefinition → Elementtypen

Jede Komponente wird ein Elementtyp in `libraries/<name>/elements/<id>.yaml`:

| OSCAL `type` | Elementart |
|---|---|
| software, service | process |
| hardware, physical | device |
| interconnection | flow |
| alle anderen | device |

Die umgesetzten Anforderungen (`control-implementations`) stehen vollständig in `oscal_extra`, die Control-IDs zusätzlich als Liste `oscal_extra.control_ids`.

## Anwendbarkeit von ARC (TR-03183-1 Kapitel 6)

Die TR-03183-1 wählt Controls über Risikoszenarien aus („Adaptable Risk-based Controls“, §6, S. 54–57). Ein Szenario nennt betroffene Assets mit Mindest-Auswirkung und eine Umgebung aus Schnittstelle, Zugang und Nutzer (§6.1, S. 54). Nach §6.2 (S. 54) gilt ein Control für das Produkt oder einen Teil davon, wenn

1. der Teil ein Asset mit mindestens der genannten Auswirkung verarbeitet und
2. jeder Umgebungsparameter des Teils einem der genannten Werte entspricht (`*` passt immer).

Threatwright prüft das je Modell für jedes Control mit Risikoszenario und zeigt eine Begründung (de/en):

- **Teile** sind Elemente (Umgebung aus ihrer Zone; Assets aus angeschlossenen Datenflüssen und aus Bedrohungen, die das Element betreffen) und bewertete Bedrohungen (Umgebung und Assets der Bewertung).
- Die Auswirkung eines Assets ist die Basisauswirkung seiner Klasse inkl. Vererbung und Verstärker, wie in der Methodik.
- Werden mehrere Dimensionen genannt (z. B. C(3) I(3) A(3)), genügt eine davon.
- Optional „kombiniertes Profil“ nach §6.3 (S. 54–55): alle Assets des Modells mit allen vorkommenden Umgebungen zusammen. Das wählt mehr Controls aus als nötig, wie von der TR für den Einstieg empfohlen.

### Risikoszenarien im Katalog (Annahme)

Wie das BSI Risikoszenarien in OSCAL abbildet, ist nicht öffentlich. Threatwright erwartet einen Control-Teil mit dem Namen `risk-scenario`:

```json
{
  "name": "risk-scenario",
  "prose": "Ein Laie installiert keine Updates ...",
  "props": [
    {"name": "asset-impact", "value": "I(3)"},
    {"name": "asset-class", "value": "PII.Generic"},
    {"name": "interface-restriction", "value": "External network"},
    {"name": "access-restriction", "value": "*"},
    {"name": "user-capability", "value": "Layman"}
  ]
}
```

- `asset-impact`: `C(3)` oder `C:3`, mehrfach möglich.
- `asset-class`: optional, schränkt auf diese Asset-Klassen ein.
- Umgebungswerte dürfen im Wortlaut der TR stehen („External network“, „Non-user-related“); sie werden auf die Schlüssel der Methodik abgebildet (`external_network`, `non_user_related`). Fehlt ein Parameter, passt jeder Wert.

In einer selbst geschriebenen Bibliothek steht dieselbe Struktur unter `oscal_extra.parts` der Maßnahmenvorlage.

### Manuelle Entscheidung

Abweichende Entscheidungen werden in `profiles/arc-overrides.yaml` gespeichert, nicht im Modell:

```yaml
schema_version: 1
models:
  main:                 # Modellname
    arc-2:              # ID der Maßnahmenvorlage
      applies: true
      rationale: Fernzugriff ist für Ausbaustufe B geplant.
      by: Produktverantwortliche
```

Eine manuelle Entscheidung hat Vorrang und wird in der Begründung als solche gekennzeichnet.

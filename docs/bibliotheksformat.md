# Bibliotheksformat

Bibliotheken liefern Bausteine:
- **Elementtypen**, z. B. SPS, Antriebsregler, EtherCAT-Strang
- **Bedrohungsvorlagen**
- **Maßnahmenvorlagen**

Mitgeliefert ist die Bibliothek `ot` (CC BY 4.0). Sie liegt unter `src/threatwright/libraries/ot/`.

## Aktivieren und eigene Bibliotheken

In `threatwright.yaml`:

```yaml
libraries: [ot, hausstandard]
```

`hausstandard` liegt im Projekt unter `libraries/hausstandard/`. Spätere Bibliotheken überschreiben Einträge früherer Bibliotheken mit gleicher Art und ID. So lässt sich einzelnes anpassen, ohne die mitgelieferte Bibliothek zu kopieren.

## Aufbau

```
libraries/hausstandard/
  library.yaml        # id, version, license, title (de/en)
  elements.yaml       # elements: [...]
  threats/*.yaml      # threats: [...]
  measures/*.yaml     # measures: [...]
```

Die Aufteilung auf Dateien ist frei. Jede YAML-Datei enthält eine oder mehrere der Listen `elements:`, `threats:` und `measures:`.

### Elementtyp

```yaml
elements:
  - id: plc
    rev: 1
    name:
      de: SPS
      en: PLC
    kind: device            # process | device | datastore | external | flow
    interfaces: [fieldbus, ethernet, usb]
    environment: {interface: known_network, access: restricted}   # Vorschlag
    properties: {firmware: true, default_password: possible}
    assets:
      - title:
          de: Steuerungsprogramm
          en: Control program
        asset_class: BusinessData.Important   # TR-03183-1 Tabellen 1-3
```

### Bedrohungsvorlage

```yaml
threats:
  - id: fieldbus-rogue-master
    rev: 1
    stride: [S, T]
    applies_to: [fieldbus-ethercat]          # Elementtypen
    title:
      de: Fremder Master übernimmt den Feldbus {element}
      en: Rogue master takes over fieldbus {element}
    scenario: {de: ..., en: ...}
    consequence: {de: ..., en: ...}
    environment: {interface: local, access: restricted}
    impact: 4
    safety_related: true
    cra_refs: [AI-I-2-d, AI-I-2-f]           # Katalog cra
    attack_ics: [T0848]                      # Katalog attack-ics (ATT&CK for ICS v20)
    emb3d: [TID-406]                         # Katalog emb3d
    iec62443: [FR1, FR3]                     # nur FR1-FR7
    measures: [fieldbus-physical-protection]
    sources: ["Herkunft der Aussage"]
```

`{element}` wird bei der Übernahme durch den Namen des Elements ersetzt.

### Maßnahmenvorlage

```yaml
measures:
  - id: signed-firmware
    rev: 1
    title: {de: ..., en: ...}
    description: {de: ..., en: ...}
    kind: technical          # technical | organizational | design | user_information | supply_chain
    compensating: false      # gleicht fehlende Schutzmechanismen eines Protokolls aus
    evidence: {de: ..., en: ...}
    cra_refs: [AI-I-2-f]
    iec62443: [FR3]
```

Fließtexte bitte im Blockstil schreiben (`de:` und `en:` auf eigenen Zeilen). In der Kurzschreibweise `{de: ..., en: ...}` trennt jedes Komma den Text.

## Revisionen und Aktualisierung

Erhöhen Sie `rev` bei jeder inhaltlichen Änderung eines Eintrags. Übernommene Objekte merken sich die Herkunft:

```yaml
library_ref: lib:ot/threat/fieldbus-rogue-master@1
```

`threatwright library update` listet alle Objekte, für die es inzwischen eine neuere Revision gibt. `validate` meldet dazu die Warnung `library-outdated`.

## Prüfung

`python scripts/library_coverage.py [bibliothek ...]` prüft eine Bibliothek:
- Schema
- Verweise, nur IDs aus den Katalogen unter `src/threatwright/catalogs/`
- STRIDE-Abdeckung: Jeder Elementtyp braucht je relevanter Kategorie mindestens eine Bedrohung.

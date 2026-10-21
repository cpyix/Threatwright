# Bibliotheksformat

Bibliotheken liefern Bausteine:
- **Elementtypen**, z. B. SPS, Antriebsregler, EtherCAT-Strang
- **Bedrohungsvorlagen**
- **Maßnahmenvorlagen**

Mitgeliefert sind vier Bibliotheken (CC BY 4.0) unter `src/threatwright/libraries/`:

| Bibliothek | Produktart | Bezüge |
|---|---|---|
| `ot` | Maschinen und Anlagen | CRA |
| `iot` | vernetzte Geräte, Consumer | ETSI EN 303 645; Funkgeräte müssen zusätzlich EN 18031 beachten (nicht abgebildet) |
| `software` | Desktop-, Mobil- und Backend-Anwendungen | OWASP ASVS 5.0.0, MASVS v2 |
| `embedded-linux` | Steuerungssoftware als mehrere Prozesse auf einem Linux-Industrie-PC (Teilmodell eines Maschinenmodells) | CRA, MITRE EMB3D, ATT&CK for ICS; baut auf `ot` auf |

Die Produktart wird beim Anlegen des Projekts gewählt (`threatwright init --library ot|iot|software|embedded-linux`, wiederholbar). `embedded-linux` nimmt `ot` automatisch mit auf, weil seine Bedrohungen auf OT-Maßnahmen verweisen.

## Aktivieren und eigene Bibliotheken

In `threatwright.yaml`:

```yaml
libraries: [ot, hausstandard]
```

`hausstandard` liegt im Projekt unter `libraries/hausstandard/`. Spätere Bibliotheken überschreiben Einträge früherer Bibliotheken mit gleicher Art und ID. So lässt sich einzelnes anpassen, ohne die mitgelieferte Bibliothek zu kopieren.

## Aufbau

```
libraries/hausstandard/
  library.yaml        # id, version, license, title (de/en), optional requires: [ot]
  elements.yaml       # elements: [...]
  threats/*.yaml      # threats: [...]
  measures/*.yaml     # measures: [...]
```

`requires` nennt Bibliotheken, deren Elementtypen oder Maßnahmen diese Bibliothek verwendet. Sie müssen in `libraries:` vor ihr stehen, sonst meldet `validate` `library-invalid`. So verweist eine Bibliothek auf vorhandene Maßnahmen, statt sie zu kopieren.

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
    # nur process/device, optional: Vorbelegung neuer Elemente dieses Typs
    privilege: {level: root}                # kernel | root | service | user, account, capabilities
    authentication: unknown                 # none | password | shared-secret | key | certificate | unknown
    listens_on: [{protocol: tcp, port: 22, interfaces: all}]
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
    etsi303645: [5.1-1, 5.3-2]               # Katalog etsi-303645 (ETSI EN 303 645 V3.1.3, IDs wie veröffentlicht)
    asvs: [V6.2.1]                           # Katalog asvs (OWASP ASVS 5.0.0, V<Kapitel>.<Abschnitt>.<Anforderung>)
    masvs: [MASVS-STORAGE-1]                 # Katalog masvs (OWASP MASVS v2)
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
    etsi303645: [5.3-2]                      # wie bei Bedrohungen; auch asvs und masvs
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

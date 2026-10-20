# Design: Threatwright für IoT, Consumer-Geräte und Software

Stand: 2026-10-20 · Status: Entwurf zur Freigabe

## Absicht

Der CRA verlangt für jedes Produkt mit digitalen Elementen eine Risikobewertung
(Art. 13). Threatwright setzt sie nach BSI TR-03183-1 um, ist aber heute erkennbar
auf Maschinen- und Anlagenbau (OT) zugeschnitten: Es gibt nur eine mitgelieferte
Bibliothek (`ot`), und README, Doku und Einrichtungsassistent sprechen
Maschinenbauer an („Schaltschrank, Produktionshalle, Feldbus“).

Künftig sollen auch Hersteller anderer CRA-relevanter Produkte CRA-konform damit
arbeiten können, zum Beispiel:

- **vernetzte Geräte, IoT und Consumer:** ein smartes Thermostat mit Companion-App
  und Cloud-Backend,
- **Software:** eine Desktop-Anwendung, eine Handy-App.

Nutzer bleiben Hersteller: Maschinenbauer wie bisher, dazu Hersteller von Geräten
und Software. Wer das Tool mit einem Thermostat öffnet, soll den Eindruck haben, dass
es auch für ihn gemacht ist, nicht nur für Maschinenbauer.

## Ausgangslage im Code

- Methode, Prüfregeln, CRA-Katalog, Diagramm, STRIDE-Assistent, Berichte: nicht
  OT-spezifisch, bleiben unverändert.
- `ProjectConfig.libraries` ist bereits eine Liste, Projekte können mehrere
  Bibliotheken kombinieren. Neue Projekte bekommen fest `["ot"]`
  (`src/threatwright/scaffold.py:49`). Eine Bibliotheksauswahl in der GUI gibt es
  nicht, `Settings.svelte` zeigt die Liste nur an.
- Bibliotheksformat siehe `docs/bibliotheksformat.md` und ADR-0011. Die
  Referenzfelder für Kataloge sind fest verdrahtet: `attack_ics`, `emb3d`,
  `iec62443` in `ThreatTemplate`/`MeasureTemplate` (`src/threatwright/library.py`,
  Prüfung ab ca. Zeile 251).
- Die Elementkategorien im Assistenten sind im Frontend fest hinterlegt
  (`CATEGORIES` in `app/src/setup-text.ts`). Unbekannte Kategorien landen unter
  „other“.
- Die Leitfragen, Zonenhinweise und das Intro des Assistenten
  (`app/src/setup-text.ts`) sind OT-formuliert („Die vier vorgeschlagenen Zonen
  passen für die meisten Maschinen“).

## Ziele

1. **Zwei neue mitgelieferte Bibliotheken**, schlank und sauber statt in voller
   OT-Tiefe:
   - `iot`: vernetzte Geräte, IoT und Consumer. Typische Elemente sind Gerät/Firmware,
     Funkschnittstellen (WLAN, BLE, Zigbee/Thread/Matter), Pairing/Onboarding,
     Companion-App, Cloud-Backend des Herstellers, OTA-Update,
     Debug-Schnittstellen und lokale Bedienung.
   - `software`: Desktop-Anwendung, Mobile-App, Backend/API als Teil des Produkts,
     Installer/Updater, Lizenz- und Kontoanbindung, lokale Datenhaltung und
     Drittkomponenten.
   - Umfang je Bibliothek **rund 30 bis 50 Bedrohungsvorlagen** mit passenden
     Maßnahmen und Elementtypen. Qualitätsmaßstab ist die OT-Bibliothek: jede
     Bedrohung mit Szenario, Folge, Umgebung, Auswirkung, `cra_refs`, verknüpften
     Maßnahmen und Quellen, zweisprachig de/en, Lizenz CC-BY-4.0.
2. **Referenzkataloge** für die neuen Bibliotheken, neben dem bestehenden
   `cra`-Katalog (CRA Anhang I nach TR-03183-1 Anhang B):
   - `iot`: ETSI EN 303 645 (Provisions, frei verfügbar).
   - `software`: OWASP ASVS 5.0 (Desktop, Backend, API) und OWASP MASVS v2 (Mobile).
   - **EN 18031-1/-2/-3 nicht in v1:** Der Normtext liegt nicht vor (kostenpflichtig),
     eine Zuordnung ohne Text wäre geraten. Nachziehen, sobald jemand mit Lizenz die
     Zuordnung prüfen kann. Die Bibliotheksbeschreibung von `iot` weist darauf hin,
     dass funkfähige Geräte zusätzlich die EN 18031 (RED) betrachten müssen.
3. **Produktart beim Anlegen des Projekts:** Der Nutzer wählt die
   Produktart, Mehrfachauswahl möglich: *Maschine/Anlage*, *vernetztes
   Gerät/IoT/Consumer*, *Software*. Daraus ergeben sich die Bibliotheken des
   Projekts (`ot`, `iot`, `software`). Ein Thermostat mit App wählt Gerät und
   Software. Im Einrichtungsassistenten richten sich Leitfragen, Beispiele,
   Zonenvorschläge und Hinweistexte nach der Auswahl.
4. **CRA-Einstufung als Orientierungshilfe:** ein eigener Schritt im
   Einrichtungsassistenten, überspringbar. Er hilft dem Hersteller einzuschätzen, ob
   sein Produkt unter den CRA fällt und ob es ein Standardprodukt, ein wichtiges
   Produkt (Anhang III, Klasse I oder II) oder ein kritisches Produkt (Anhang IV)
   ist, und was das grob für das Konformitätsbewertungsverfahren bedeutet.
   **Es wird nichts gespeichert**, und nichts davon erscheint im Bericht.
5. **Ansprache verallgemeinern:** README, Schnellstart, Tutorial, FAQ, das Intro des
   Assistenten und die Projekterstellung sprechen von „Herstellern von Produkten mit
   digitalen Elementen“. OT bleibt ein gleichwertiger Fall, wird aber nicht mehr als
   einziger dargestellt.

## Nicht-Ziele

- Keine volle OT-Tiefe (239 Bedrohungen) für die neuen Bereiche in dieser Version.
  Ausbau erst, wenn echte Nutzer Lücken melden.
- Kein Speichern der Einstufung, kein Berichtsabschnitt, keine Prüfregel dazu.
- Keine Änderung an Methode, Risikomatrix, Prüfregeln oder Berichtsvorlagen.
- Keine eigene Ansicht für die Einstufung außerhalb des Assistenten.
- Keine SBOM-/Schwachstellen-Anbindung (steht separat in der ROADMAP).
- Reine SaaS-Angebote ohne zugehöriges Produkt werden nicht eigens unterstützt:
  Sie fallen nicht unter den CRA, nur die Datenfernverarbeitung *als Teil eines
  Produkts*.

## Anti-Ziele (wäre ein Fehlschlag, auch wenn es technisch funktioniert)

- Bestehende OT-Projekte verhalten sich anders, oder OT-Nutzer bemerken Rückschritte.
  Projekte mit `libraries: [ot]` müssen unverändert laden, prüfen und berichten
  (ADR-0015, Kompatibilitätsfixtures unter `tests/fixtures/compat/`).
- Die Einstufung wirkt wie eine verbindliche Rechtsauskunft. Sie muss klar als
  Orientierung gekennzeichnet sein, mit Hinweis auf den Verordnungstext und die
  Durchführungsverordnung zu den technischen Beschreibungen (Art. 7 Abs. 4).
- Urheberrechtlich geschützter Normtext wird übernommen. Für ETSI, EN 18031 und
  OWASP nur Kennungen plus eigene Kurztitel, wie heute bei EMB3D und IEC 62443.
  OWASP steht unter CC-BY-SA; deshalb keine Texte übernehmen, damit die Bibliothek
  CC-BY-4.0 bleiben kann.
- Halbgare Vorlagen: lieber 30 gute als 50 generische.

## Was entschieden ist

| Punkt | Entscheidung | Von |
|---|---|---|
| Zielgruppen | Hersteller: Maschinenbau, IoT/Consumer, Software | Nutzer |
| Umsetzung über Bibliotheken plus Produktart im Assistenten, kombinierbar | ja | Nutzer (Rückspiegelung bestätigt) |
| Tiefe | schlank, ca. 30 bis 50 Bedrohungen je neuem Bereich | Nutzer |
| Einstufung | nur im Assistenten, überspringbar | Nutzer |
| Einstufung speichern / im Bericht | nein, nur Orientierung | Nutzer |
| Kataloge: ETSI EN 303 645, OWASP ASVS, OWASP MASVS | ja | Vorschlag, nicht widersprochen |
| EN 18031 | nicht in v1, Normtext liegt nicht vor | Nutzer |
| Fachliche Prüfung der Vorlagen | Builder verantwortet sie allein auf Basis öffentlicher Quellen; keine externe Abnahme vor v1 | Nutzer |
| Katalogversionen | ASVS 5.0, MASVS v2 (aktuelle Stände, IDs werden in Modellen gespeichert) | meine Entscheidung |
| Element-, Bedrohungs- und Maßnahmen-IDs | in `iot`/`software` keine Kollision mit `ot` oder untereinander; ein Test prüft das, weil spätere Bibliotheken frühere sonst still überschreiben (`_load_one`) | meine Entscheidung |
| Wo die Produktart gewählt wird | beim Anlegen des Projekts (`Start.svelte`, setzt `libraries`), weil Bibliotheken projektweit gelten; der Modell-Assistent richtet Texte danach aus und kann Bibliotheken nur **hinzufügen**, nie entfernen (sonst verlieren andere Modelle Elementtypen) | meine Entscheidung |
| Reihenfolge | erst `iot` komplett (Bibliothek, Katalog, Tests), dann `software`; Assistent, Einstufung und Texte danach | meine Entscheidung |
| MITRE ATT&CK Enterprise/Mobile | **nicht** in v1, um schlank zu bleiben | meine Entscheidung |
| Zwei Bibliotheken (`iot`, `software`) statt einer gemeinsamen | ja, passt zur Mehrfachauswahl | meine Entscheidung |

## Inhalt des Einstufungsschritts (Orientierung)

Reihenfolge, je Frage kurz und in Alltagssprache mit Beispielen:

1. **Fällt das Produkt unter den CRA?** Produkt mit digitalen Elementen, das auf dem
   EU-Markt bereitgestellt wird und eine Daten- oder Netzverbindung hat. Hinweise
   auf Ausnahmen: Medizinprodukte (MDR/IVDR), Kfz-Typgenehmigung, Luftfahrt,
   Schiffsausrüstung, nicht kommerzielle Open Source, reines SaaS.
2. **Ist die Kernfunktion eine aus Anhang III oder IV?** Kategorien als auswählbare
   Liste mit Beispielen, etwa Klasse I Nr. „Smart-Home-Produkte mit
   Sicherheitsfunktionen (Türschlösser, Kameras, Babyphones, Alarmanlagen)“,
   „vernetztes Spielzeug“, „Wearables mit Gesundheitsfunktion“, „Browser“,
   „Passwortmanager“, „VPN“, „Betriebssysteme“, „Router“. Klasse II, zum Beispiel
   Firewalls und Hypervisoren. Anhang IV, zum Beispiel Smart-Meter-Gateways und
   Smartcards.
   Wichtiger Hinweis: Ein Thermostat ist nicht automatisch Anhang III, sondern nur,
   wenn seine Kernfunktion darunter fällt.
3. **Ergebnis:** Standard / wichtig Klasse I / wichtig Klasse II / kritisch, mit dem
   jeweiligen Verfahren in einem Satz: Modul A; Klasse I Modul A nur mit
   harmonisierter Norm, sonst B+C oder H; Klasse II B+C oder H; kritisch
   EUCC-Zertifizierung, sonst wie Klasse II. Dazu der Hinweis, dass die
   Risikobewertung in allen Fällen gleich bleibt.

Der Builder prüft die Listen und Verfahren gegen den Amtsblatttext der
Verordnung (EU) 2024/2847 (Art. 7, 8, 32, Anhang III, IV) und übernimmt sie in
eigenen Worten.

## Dem Builder überlassen

- **Schema der Katalogreferenzen:** neue feste Felder (`etsi303645`,
  `asvs`, `masvs`) nach dem bestehenden Muster oder ein generisches Feld. Bedingungen:
  Die OT-Bibliothek und eigene Bibliotheken bleiben gültig, `docs/bibliotheksformat.md`
  und ADR-0011 werden nachgezogen, eigene Bibliotheken können die neuen Kataloge
  nutzen.
- Konkreter Zuschnitt der Elementtypen und Kategorien je Bibliothek, inklusive
  Einträgen in `CATEGORIES` und Icons.
- Wie die Produktart auf Leitfragen und Zonenvorschläge wirkt (Texte, Presets).
- Neuer Schreibweg für `libraries` in `threatwright.yaml` (nur Hinzufügen), falls
  der bestehende Server keinen hat.
- **CLI:** `threatwright init` bekommt eine Option für die Bibliotheken bzw. die
  Produktart. Der Default bleibt `["ot"]`, damit bestehende Skripte und CI
  unverändert laufen.
- Ob und wie die Produktart nachträglich änderbar ist. Mindestens kann der Nutzer
  den Assistenten erneut öffnen; die Bibliotheksliste in `threatwright.yaml` bleibt
  die Quelle der Wahrheit.
- Ein zweites Demo-Modell (zum Beispiel ein Thermostat) für Screenshots und Tutorial,
  falls es sich anbietet.
- Tests: Die bestehende Bibliotheksprüfung (`check`/Referenzauflösung) läuft für
  `iot` und `software` mit, dazu je ein Test, dass jede Bedrohung mindestens eine
  Maßnahme und gültige `cra_refs` hat, und ein E2E-Test für die Produktwahl im
  Assistenten. Den Einstufungsschritt nur auf Überspringbarkeit und
  „nichts gespeichert“ testen.
- Version: Minor-Release (neue Bibliotheken, keine Schemaänderung an Projektdateien).

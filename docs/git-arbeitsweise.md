# Arbeiten mit Git

Ein Threatwright-Projekt ist ein Ordner mit YAML-Dateien: eine Datei pro Objekt
(Element, Datenfluss, Asset, Bedrohung, Maßnahme, Frage). Damit eignet es sich
direkt für Versionsverwaltung mit Git. Git ist **optional** – Threatwright
funktioniert auch ohne. Mit Git erhalten Sie zusätzlich Änderungsnachweise,
Freigaben per Tag und Change-Markierungen in der Oberfläche.

Das Projekt darf in einem Unterordner eines größeren Repositories liegen
(z. B. neben dem Quellcode des Produkts). Pfade mit Leerzeichen und Umlauten
sind kein Problem.

## Empfohlener Ablauf: Merge Requests

1. Für jede Analyse-Änderung einen Branch anlegen, z. B. `tm/neue-fernwartung`.
2. Im Branch mit Threatwright arbeiten (GUI oder Editor). Threatwright schreibt
   nur Dateien, deren Inhalt sich wirklich geändert hat; Kommentare und
   Formatierung in den YAML-Dateien bleiben erhalten.
3. Vor dem Commit `threatwright validate` ausführen (oder in CI laufen lassen).
4. Merge Request / Pull Request eröffnen. Als Beschreibung eignet sich der
   Änderungsnachweis (siehe unten):

   ```
   threatwright diff main HEAD --format md
   ```

5. Review durch eine zweite Person, insbesondere bei Akzeptanzen und
   Ablehnungen von Bedrohungen (Vier-Augen-Prinzip).

## Freigabe per Git-Tag

Eine freigegebene Fassung der Risikoanalyse wird mit einem annotierten Tag
markiert:

```
git tag -a tm-1.0 -m "Freigabe Risikoanalyse 1.0"
git push origin tm-1.0
```

Annotierte Tags speichern, wer wann freigegeben hat. Die Oberfläche listet alle
Tags (neueste zuerst) und kann Änderungen **seit der letzten Freigabe**
markieren. Tragen Sie die Freigabe zusätzlich in das Änderungsprotokoll
(`changelog` in `model.yaml`) ein, damit sie auch im Bericht erscheint.

## Änderungsnachweis mit `threatwright diff`

```
threatwright diff <rev1> <rev2> [--format md|json] [--path <projektordner>]
```

`rev1` und `rev2` sind beliebige Git-Revisionen (Tag, Branch, Commit). Ohne
`rev2` wird mit der Arbeitskopie verglichen. Der Vergleich ist **semantisch**,
nicht zeilenweise. Er zeigt je Modell:

- hinzugefügte, entfernte und geänderte Objekte mit den geänderten Feldern,
- Statuswechsel, hervorgehoben **neu abgelehnt** und **neu akzeptiert**,
- Risikoänderungen von Bedrohungen (altes Risiko → neues Risiko, berechnet nach
  der Methode des Projekts),
- geänderte Modell-Metadaten (Zonen, Konfigurationen, Änderungsprotokoll) und
  Projekteinstellungen.

Objekte werden zuerst über ihre UUID, dann über ihre ID zugeordnet. Eine
umbenannte ID erscheint daher als Änderung („vorher M-0001“) und nicht als
Löschen plus Neuanlage.

`--format md` (Standard) erzeugt einen Markdown-Text für Merge Requests und
die Dokumentation, `--format json` eine maschinenlesbare Fassung, z. B. für CI.
Das Risiko wird für beide Stände mit der **aktuellen** Methodenkonfiguration
berechnet; geänderte `method-overrides.yaml` erscheinen daher nicht als
Risikoänderung, sondern nur als geänderte Datei im Git-Diff.

## YAML-Diffs reviewen

Der semantische Diff ist die Zusammenfassung, der Git-Diff das Detail. Beim
Review lohnt der Blick auf:

- **`status`, `acceptance`, `rejection`** – jede Akzeptanz und Ablehnung braucht
  eine nachvollziehbare Begründung und, je nach Risiko, die richtige Person
  (`acceptance.by`).
- **`assessment`** – Änderungen an Schnittstelle, Zugang, Nutzer oder Impact
  ändern das Risiko. Die Begründung (`rationale`) sollte mitgeändert sein.
- **`measures`** – entfernte Maßnahmen-Verweise erhöhen meist das Restrisiko.
- **Gelöschte Dateien** – eine gelöschte Bedrohung ist eine fachliche
  Entscheidung; besser ist meist `status: rejected` mit Begründung.
- **`uuid`** – darf sich nie ändern. Eine geänderte UUID deutet auf Kopieren
  statt Bearbeiten hin.

`diagram.layout.yaml` enthält nur Positionen im Diagramm und kann im Review
meist übersprungen werden.

Merge-Konflikte sind selten, weil jedes Objekt eine eigene Datei ist. Legen
zwei Branches parallel neue Objekte an, kann dieselbe ID doppelt vergeben
werden: Git meldet dann einen Konflikt bei einer neuen Datei. Benennen Sie in
diesem Fall eine der beiden Dateien und die `id` darin um (z. B. `T-0007` →
`T-0008`) und passen Sie Verweise an; `threatwright validate` findet
übersehene Verweise.

## Change-Markierungen in der Oberfläche

Ist das Projekt in einem Git-Repository, markiert die Oberfläche Objekte, deren
Datei sich gegenüber dem letzten Commit geändert hat (einschließlich neuer,
noch nicht versionierter Dateien). Alternativ kann ein Tag als Vergleichsbasis
gewählt werden („seit letzter Freigabe“).

## Export und Import

### Export

```
threatwright export --format csv|json|xlsx
```

Exportiert eine Zeile pro Bedrohung (Modell, ID, Titel, Szenario, STRIDE,
Ziele, Assets, Schnittstelle, Zugang, Nutzer, Impact, Exposition, Risiko,
Risikostufe, akzeptabel, Status, Maßnahmen, CRA-Bezüge, sicherheitsrelevant)
und eine Maßnahmenliste (ID, Titel, Art, Status, Verantwortlich, Fällig,
Nachweis, Bedrohungen).

- **CSV** ist für deutsches Excel eingestellt: UTF-8 **mit** BOM (sonst zeigt
  Excel Umlaute falsch an), Trennzeichen **Semikolon** (deutsches
  Listentrennzeichen; Komma ist dort das Dezimaltrennzeichen). Es entstehen zwei
  Dateien: `<name>.csv` (Bedrohungen) und `<name>-measures.csv` (Maßnahmen).
  Ein anderes Trennzeichen ist per Parameter möglich.
- **XLSX** enthält die Blätter „Bedrohungen“ und „Maßnahmen“.
- **JSON** enthält beide Listen mit echten Datentypen (Listen, Zahlen,
  Wahrheitswerte).

Schutz vor Formel-Injektion: Zellen, die mit `=`, `+`, `-`, `@`, Tab oder
Wagenrücklauf beginnen, erhalten im CSV ein vorangestelltes `'`; im XLSX werden
sie ausdrücklich als Text gespeichert. Gleiche Eingabe ergibt byte-identische
Dateien (auch XLSX).

### Import

```
threatwright import --from threat-dragon|csv <datei> --model <name>
```

Ein Import **ergänzt** immer nur: neue Objekte erhalten neue IDs, vorhandene
Objekte werden nie verändert. Existiert das Modell noch nicht, wird es
angelegt. Dateien über 5 MB werden abgelehnt. Hat das Projekt Ladefehler, bricht
der Import ab (sonst könnte eine neue ID eine fehlerhafte Datei überschreiben).
Nach dem Import `threatwright validate` ausführen und die Warnungen des Imports
prüfen.

**OWASP Threat Dragon (Format v2, JSON):**

| Threat Dragon | Threatwright |
|---|---|
| Actor | Element `external` |
| Process | Element `process` |
| Store | Element `datastore` |
| Flow | Datenfluss (Quelle/Ziel über die Zellen-ID; nicht verbundene Flüsse werden übersprungen) |
| Trust Boundary (Box) | Zone; Elemente, deren Mittelpunkt in der Box liegt, erhalten diese Zone |
| Trust Boundary (Linie) | nicht abbildbar, Warnung |
| Threat | Bedrohung, `status: identified` |
| Threat `type` | STRIDE-Kategorie (Spoofing → S … Elevation of privilege → E; CIA-Modell: Confidentiality → I, Integrity → T, Availability → D) |
| Threat `description` | Szenario |
| Threat `mitigation` | neue Maßnahme; Status `implemented`, wenn die Bedrohung „Mitigated“ war, sonst `proposed` |
| `type`, `severity`, `status` | als Hinweis in der Beschreibung der Bedrohung |

Alle importierten Bedrohungen starten als `identified`, auch wenn sie in Threat
Dragon „Mitigated“ oder „NA“ waren: Threat Dragon kennt weder die Bewertung nach
TR-03183-1 noch begründete Akzeptanzen oder Ablehnungen. Diese Entscheidungen
müssen in Threatwright getroffen und begründet werden. Mehrere Diagramme landen
im selben Modell und werden im Layout nebeneinander angeordnet. Das alte Format
v1 wird nicht unterstützt (in Threat Dragon 2 öffnen und speichern).

**CSV:** Spalten wie beim Export, erkannt über die Kopfzeile (nur `title` ist
Pflicht). Semikolon oder Komma wird automatisch erkannt, ein BOM ist optional.
Berechnete Spalten (Exposition, Risiko, Risikostufe, akzeptabel) und die Spalten
`model` und `id` werden ignoriert. Verweise auf Ziele, Assets und Maßnahmen
werden nur übernommen, wenn sie im Zielmodell existieren. Die Status `accepted`
und `rejected` werden als `identified` importiert, da die Begründung fehlt.

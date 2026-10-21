# Schnellstart (10 Minuten)

## 1. Installieren

Sie haben drei Möglichkeiten:

- **Portable Version (empfohlen):** ZIP für Windows bzw. `tar.gz` für Linux von der Release-Seite herunterladen, entpacken und `threatwright` starten. Sie brauchen weder Python noch Administratorrechte. Für macOS gibt es keine portable Version, dort die Variante mit Python nutzen.
- **Mit Python:** `pipx install threatwright`
- **Für CI:** das Container-Image, siehe [ci.md](ci.md)

## 2. Projekt anlegen

```
threatwright init mein-produkt --name "Mein Produkt"
```

Die Produktart wählen Sie mit `--library` (kurz `-l`): `ot` (Maschinen und Anlagen, Standard), `iot` (vernetzte Geräte, Consumer), `software` oder `embedded-linux` (Steuerungssoftware auf einem Linux-Industrie-PC, bringt `ot` mit; das Beispiel legt ein Maschinenmodell und ein Teilmodell `software` an). Die Option ist wiederholbar, z. B. `-l iot -l software`. In der Oberfläche wählen Sie die Produktart per Ankreuzfeld auf der Startseite beim Anlegen.

Das Werkzeug legt einen Ordner mit einem Teilmodell `main` an. Er enthält:
- vier Standardzonen: geräteintern, lokal, Anlagennetz, extern. Ohne `ot` heißt die dritte Zone „Lokales Netz (LAN/WLAN)“ (Z-LAN).
- die gewählte(n) Bibliothek(en), ohne Angabe `ot`
- die Datei `method-overrides.yaml` mit allen Entscheidungspunkten zur Risikoakzeptanz

Machen Sie den Ordner am besten gleich zum Git-Repository (`git init`).

**Erst ausprobieren?** `threatwright init beispiel -l iot --example` legt ein fertiges kleines Beispielmodell der Produktart an (Elemente, Verbindungen, bewertete Bedrohungen, Maßnahmen, eine Akzeptanz). In der Oberfläche heißt das Ankreuzfeld „Mit Beispielmodell“.

## 3. Oberfläche starten

```
threatwright --project mein-produkt
```

Der Standardbrowser öffnet sich. Die Oberfläche läuft nur auf Ihrem Rechner unter `127.0.0.1` und baut keine Verbindungen ins Internet auf.

## 4. Modell aufbauen

**Mit dem Einrichtungsassistenten (empfohlen für den Einstieg):** Ein in der Oberfläche neu angelegtes Projekt öffnet direkt den Assistenten. Bei bestehenden Projekten erreichen Sie ihn über **Einrichtung** in der Navigation. Er führt in acht Schritten durch Produktbeschreibung und Einsatzzweck, eine optionale CRA-Einstufung (nur zur Orientierung, nichts wird gespeichert, nicht im Bericht), Zonen mit Schnittstelle, Zugang und Nutzer, Komponenten aus der Bibliothek, Verbindungen, Assets mit TR-Klasse, Bedrohungsvorschläge (gelten als Cyberrisiko nach Regel 3.3) und eine Abschlussübersicht. Die Leitfragen richten sich nach der Produktart; weitere Bibliotheken lassen sich im Produktschritt hinzufügen (entfernen nicht); eine hinzugefügte Bibliothek wird mit dem Projekt gespeichert (Strg+S) und lässt sich nicht mit Strg+Z rückgängig machen. Alles landet als normaler Modellinhalt im Projekt; Rückgängig und Speichern funktionieren wie überall.

**Von Hand** in den einzelnen Ansichten:

1. **Diagramm:** Bausteine aus der Liste links auf die Fläche ziehen, z. B. „Steuerungsrechner Linux“, „Antriebsregler“, „HMI“. Die typischen Assets jedes Bausteins legt das Werkzeug gleich mit an.
2. **Verbindungen:** Oben den Typ wählen, z. B. „EtherCAT“, dann von einem Anschlusspunkt eines Elements zu einem anderen ziehen.
3. **Zonen:** Ein Element anklicken und rechts die Zone setzen. Die Zone gibt die Umgebung für die Bewertung vor.
4. **STRIDE-Assistent:** Im rechten Feld „STRIDE-Assistent →“ anklicken. Je Kategorie erscheinen Vorschläge aus der Bibliothek; „Übernehmen“ legt eine vorbelegte Bedrohung mit passenden Maßnahmen an.
5. **„Ist das ein Cyberrisiko?“:** Die Frage erscheint bei jeder neuen Bedrohung. Lautet die Antwort „nein“, wird der Eintrag mit Begründung verworfen.
6. **Bewerten:** Unter „Bedrohungen“ die Bewertung prüfen, also Schnittstelle, Zugang, Nutzer und Impact. Risiko und „akzeptabel / zu behandeln“ erscheinen sofort.
7. **Abdeckung:** Die Matrix zeigt Lücken je Element und STRIDE-Kategorie. Eine Lücke schließen Sie über den Assistenten oder mit „n. r.“ (nicht relevant) und einer Begründung.
8. **Prüfung:** Offene Punkte stehen in der Liste; ein Klick springt zum betroffenen Objekt.
9. **Speichern:** Strg+S. Jedes Objekt ist eine eigene YAML-Datei; Sie committen sie mit Ihrem Git-Werkzeug.

## 5. Dokument erzeugen

```
threatwright build mein-produkt --format docx
```

Die Datei landet in `mein-produkt/build/`. Eigene Vorlagen beschreibt die [Vorlagenreferenz](vorlagenreferenz.md).

## 6. In der Pipeline prüfen

Unter **Einstellungen → CI-Pipeline** steht eine fertige GitLab-Vorlage für Ihr Projekt zum Kopieren. Alternativ gibt `threatwright ci gitlab mein-produkt` sie aus. Weiter geht es mit dem [Tutorial](tutorial.md).

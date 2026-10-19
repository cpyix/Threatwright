# Schnellstart (10 Minuten)

## 1. Installieren

Sie haben drei Möglichkeiten:

- **Portable Version (empfohlen):** ZIP für Windows bzw. `tar.gz` für Linux von der Release-Seite herunterladen, entpacken und `threatwright` starten. Sie brauchen weder Python noch Administratorrechte.
- **Mit Python:** `pipx install threatwright`
- **Für CI:** das Container-Image, siehe [ci.md](ci.md)

## 2. Projekt anlegen

```
threatwright init mein-produkt --name "Mein Produkt"
```

Das Werkzeug legt einen Ordner mit einem Teilmodell `main` an. Er enthält:
- vier Standardzonen: geräteintern, lokal, Anlagennetz, extern
- die Bibliothek `ot`
- die Datei `method-overrides.yaml` mit allen Entscheidungspunkten zur Risikoakzeptanz

Machen Sie den Ordner am besten gleich zum Git-Repository (`git init`).

## 3. Oberfläche starten

```
threatwright --project mein-produkt
```

Der Standardbrowser öffnet sich. Die Oberfläche läuft nur auf Ihrem Rechner unter `127.0.0.1` und baut keine Verbindungen ins Internet auf.

## 4. Modell aufbauen

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

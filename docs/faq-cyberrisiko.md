# FAQ: Ist das ein Cyberrisiko?

Der CRA verlangt eine Bewertung der **Cybersicherheitsrisiken**. Viele Einträge, die bei einer ersten Sammlung entstehen, gehören jedoch in die funktionale Sicherheit oder die Qualitätssicherung. Das Werkzeug stellt deshalb bei jeder selbst angelegten Bedrohung dieselbe Prüffrage. Vorschläge aus der Bibliothek beschreiben immer einen Angriff; sie gelten beim Übernehmen als Cyberrisiko und lassen sich bei Bedarf mit Begründung verwerfen.

## Die Regel

**Ein Eintrag ist ein Cyberrisiko, wenn seine Ursache ein Angriff auf das digitale Produkt ist.** Dazu zählen:

- unbefugter Zugriff
- Manipulation von Daten, Befehlen, Konfiguration oder Software
- Abfluss von Daten
- Störung der Verfügbarkeit über digitale Wege

**Die Folge bestimmt die Höhe, nicht den Bezug.** Wie schwer der Schaden ist, fließt in den Impact ein. Ob der Eintrag überhaupt ein Cyberrisiko ist, entscheidet die Ursache.

**Ein Angriffsweg ergibt eine Bedrohung.** Mehrere Folgen derselben Ursache fassen Sie in einer Bedrohung zusammen.

## Beispiele

| Eintrag | Cyberrisiko? | Warum |
|---|---|---|
| Ausschuss, weil jemand Rezeptparameter manipuliert hat | ja | Ursache ist eine Manipulation von Daten |
| Ausschuss durch Bedienfehler oder Verschleiß | nein | keine Angriffsursache; Qualitätssicherung |
| Not-Halt wirkt nicht, weil ein Kabel bricht | nein | funktionale Sicherheit |
| Freigabeausgang wird über einen Feldbus-Teilnehmer ohne Authentisierung gesetzt | ja | unbefugte Befehle über digitalen Weg; Folge betrifft die Sicherheit, deshalb hoher Impact und Sicherheitsbezug |
| Ausfall durch Netzwerküberlast eines anderen Geräts im Kundennetz | ja, wenn ein Angreifer die Last erzeugen kann | Störung der Verfügbarkeit über digitale Wege |
| Firmware-Fehler führt zum Absturz | nein, solange niemand ihn gezielt auslösen kann | sonst ja, als Denial of Service |

## Was passiert mit verworfenen Einträgen?

Verwerfen Sie Einträge, statt sie zu löschen. Die ID bleibt erhalten, und die Begründung ist Pflicht. Verworfene Einträge zählen nicht zur Risikoverteilung, stehen im Dokument aber in einem eigenen Abschnitt. So lässt sich nachvollziehen, dass der Punkt geprüft wurde.

Die vorformulierte Begründung verweist auf funktionale Sicherheit bzw. Qualitätssicherung. Passen Sie sie bei Bedarf an.

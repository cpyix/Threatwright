# Methodik: BSI TR-03183-1 im Werkzeug

Standardmethode ist `tr-03183-1` (Datei `src/threatwright/methods/tr-03183-1/method.yaml`). Alle Zahlen stehen in dieser Datei, jeweils mit Fundstelle in der TR-03183-1 v1.0.0. Der Programmcode enthält keine Methodikwerte.

## Ablauf je Bedrohung

1. **Assets** bekommen eine Klasse nach TR-Tabellen 1–3, z. B. `Functions.Safety`. Daraus ergibt sich der Basis-Impact je Vertraulichkeit (C), Integrität (I) und Verfügbarkeit (A).
   - Sicherheits-Assets (`Security.*`) erben den Impact von den Assets, die sie schützen (Feld `protects`).
   - Abweichungen über einen **Verstärker** (`amplifier`) sind nur mit Begründung zulässig.
2. **Impact 1–5** der Bedrohung: Das Werkzeug schlägt den höchsten Wert der betroffenen Assets vor, passend zu den STRIDE-Kategorien. Sie wählen den endgültigen Wert.
3. **Umgebung** über drei Auswahllisten (TR Anhang D, Tabellen 11–13):

   | Schnittstelle | Faktor | Zugang | Faktor | Nutzer | Faktor |
   |---|---|---|---|---|---|
   | physisch | 0,38 | beschränkt | 0,42 | nicht nutzerabhängig | 1,0 |
   | lokal | 0,55 | öffentlich beaufsichtigt | 0,58 | fachkundig | 0,58 |
   | dediziertes bekanntes Netz | 0,70 | beweglich | 0,81 | unterwiesen | 0,81 |
   | bekanntes Netz | 0,80 | unbeschränkt | 1,0 | Laie | 1,0 |
   | externes Netz | 1,0 | | | | |

4. **Exposition** `E = rund(1 + Schnittstelle × Zugang × Nutzer × 4)`, kaufmännisch gerundet, Ergebnis 1–5.
5. **Risiko** aus der Matrix (Anhang D.2, S. 79), Stufen 1 sehr niedrig bis 5 sehr hoch.
6. **Bewertung:** Bis „niedrig“ ist das Risiko akzeptabel, darüber muss es behandelt werden.

Exposition, Risiko und Akzeptanz werden nie gespeichert, sondern immer berechnet.

## Hinweis zur Matrix-Lesart

Die Formel ergibt **5** für die ungünstigste Umgebung (Angriff aus dem Internet, unbeschränkter Zugang). Die abgedruckte Matrix ordnet das höchste Risiko aber der Zeile **„Environment 1“** zu.

Wörtlich gelesen hätte ein Internetangriff auf eine Sicherheitsfunktion nur das Risiko „mittel“. Das Werkzeug liest die Matrix deshalb standardmäßig **umgekehrt** (`matrix_row_from_exposure: inverted`): Höchste Exposition ergibt höchstes Risiko.

Wer die wörtliche Lesart braucht, setzt in `method-overrides.yaml`:

```yaml
risk_matrix:
  matrix_row_from_exposure: literal
```

Weitere Auslegungen (Klammerfehler in der Formel, Vererbung bei Sicherheits-Assets, Rundung beim Verstärker) sind in [ADR-0010](adr/0010-tr-method-interpretation.md) und [VERIFY.md](VERIFY.md) begründet.

## Anpassen im Projekt: `method-overrides.yaml`

Die Datei wird über die Methode gelegt. Mappings werden zusammengeführt, Listen ersetzt. Entscheidungspunkte:

| Schlüssel | Bedeutung | Standard |
|---|---|---|
| `acceptance.max_acceptable_risk` | höchste akzeptable Risikostufe | 2 (niedrig) |
| `acceptance.approvers` | wer welche Stufe akzeptieren darf, z. B. `{2: [Produktverantwortung]}` | alle |
| `acceptance.rules` | Sonderregeln, siehe unten | alle aus |
| `risk_matrix.matrix_row_from_exposure` | `inverted` oder `literal` | `inverted` |

Mitgelieferte Sonderregeln (`enabled: true` schaltet sie ein):
- `post-market-moderate`: Wenn `lifecycle: post_market` in `threatwright.yaml` steht, ist „mittel“ akzeptierbar (TR D.2, Hinweis).
- `safety-stricter`: Bei Bedrohungen mit Sicherheitsbezug ist nur „sehr niedrig“ akzeptabel.
- `fleet-wide-amplifier`: Impact +1, wenn das eigene Feld `fleet_wide` gesetzt ist.

Greifen mehrere Regeln, gilt die strengste Grenze.

Eine komplett eigene Methode liegt im Projekt unter `methods/<id>/method.yaml` und wird in `threatwright.yaml` mit `method: <id>` gewählt.

## Teilmodelle und Rechtekontexte

Steuerungssoftware auf einem Industrie-PC besteht meist aus mehreren Prozessen mit unterschiedlichen Rechten. Damit das Maschinenmodell übersichtlich bleibt, beschreiben Sie die Software in einem **Teilmodell**, das ein Element des Maschinenmodells verfeinert.

**Verfeinern (`refines`).** Ein Element des Teilmodells nennt das Element, das es verfeinert, im Format `<modell>/<id>`, z. B. `refines: main/E-0019` am Steuerungsrechner im Teilmodell `software`. Ein Teilmodell gehört zu genau einem Modell. Es gibt weiterhin **eine Risikobewertung je Produkt**:
- Das Dokument des Hauptmodells enthält das Teilmodell. Elemente und Datenflüsse stehen in einem eigenen Unterabschnitt, IDs des Teilmodells erscheinen mit Modellnamen (`software/T-0003`).
- Risikoverteilung, Bedrohungen, Maßnahmen, Rückverfolgbarkeit, Freigaben und CRA-Abdeckung zählen Haupt- und Teilmodell zusammen. `threatwright build` erzeugt für das Teilmodell kein eigenes Dokument (mit `--model software` weiterhin möglich).
- Bedrohungen am verfeinernden Element und an allem, was darauf läuft, decken das verfeinerte Element ab und umgekehrt. Eine Bedrohung wird also nur in einem der beiden Modelle bewertet. Bewertet man dieselbe Bibliotheksbedrohung in beiden, meldet `validate` die Warnung `duplicate-assessment`.
- Faustregel: Im Hauptmodell bleibt, was das Gerät als Ganzes betrifft (Gehäuse, Lieferkette, physischer Zugang), ins Teilmodell gehört alles, was einzelne Prozesse betrifft.

**Läuft auf (`runs_on`).** Ein Prozess (oder ein virtuelles Gerät, z. B. eine VM) nennt das Gerät desselben Modells, auf dem er läuft. Ohne eigene `zone` übernimmt er die Zone seines Hosts und damit dessen Umgebung für die Exposition. Hat ein Gerät eine Bedrohung mit STRIDE E (Übernahme), betrifft sie alles, was darauf läuft: Die Warnung `host-takeover-understated` meldet, wenn ein dort verarbeitetes Asset einen höheren Impact hat als die Bedrohung und in ihr fehlt. Eine feste Impact-Schwelle gibt es dabei nicht. Gerade eine niedrig bewertete Übernahme eines Hosts mit einer Sicherheitsfunktion ist der Fall, den die Regel finden soll.

**Rechtekontext (`privilege`).** `level` ist `kernel`, `root`, `service` oder `user`, dazu optional `account` (z. B. `operator`) und `capabilities` (nur zur Dokumentation). Zwei Prozesse auf demselben Host mit unterschiedlichem `level` oder `account` liegen in verschiedenen Rechtekontexten. Ein Datenfluss zwischen ihnen ist ein **Grenzübergang** wie ein Fluss zwischen Zonen: Das Diagramm zeichnet ihn gepunktet, die Berichte zeigen ihn in der Spalte „Grenze“, und `privilege-boundary-gap` verlangt dort Bedrohungen mit S und E (am Fluss oder an der höher privilegierten Seite). Der Rechtekontext ändert die Exposition nicht. Er beschreibt, was ein Angreifer nach der Übernahme eines Prozesses als Nächstes erreichen kann.

**Technische Angaben.** `listens_on` (Protokoll, Port bzw. Socket-Pfad, Interfaces `all`, `loopback` oder Name), `authentication` (`none`, `password`, `shared-secret`, `key`, `certificate`, `unknown`), `memory_safe` und `sbom_ref` (purl und/oder CPE der Komponente) ergeben im Bericht die Tabelle „Technische Angriffsfläche“. Ein Dienst auf allen Interfaces ohne bekannte Authentisierung braucht eine Bedrohung mit S oder E (`exposed-service-unauthenticated`). `sbom_ref` ist nur eine Referenz. Den Abgleich mit Schwachstellen übernehmen weiterhin die SBOM-Dateien (`sbom`, siehe [SBOM und Schwachstellen](sbom.md)).

## Qualitative Kriterien der TR (§5.14.3)

Die TR nennt neben Anhang D qualitative Akzeptanzkriterien. Ein Beispiel: Ein mittleres oder höheres Risiko durch Fehlkonfiguration ist bei einem Laien als Nutzer nicht akzeptabel. Anhang D bezeichnet die TR selbst als experimentell. Das Werkzeug nutzt Anhang D, weil es sich berechnen und in der CI prüfen lässt. Die Kriterien aus §5.14.3 sollten Sie bei der Festlegung der Akzeptanzgrenzen trotzdem heranziehen.

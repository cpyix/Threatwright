# Tutorial: Teilmodell „Feldbus“ in 30 Minuten

In diesem Tutorial bauen Sie ein Teilmodell für den Feldbus eines Produkts auf. Das Produkt ist neutral und frei erfunden:

- ein Steuerungsrechner mit Linux als Feldbus-Master
- zwei Antriebsregler
- ein Remote-I/O-Modul im Maschinenbereich
- Ausgänge mit Sicherheitswirkung, die von der Software geschaltet werden

Planen Sie etwa 30 Minuten ein. Die Zeitangaben sind Richtwerte.

## Vorbereitung (2 min)

```
threatwright init feldbus-tutorial --name "Tutorial"
cd feldbus-tutorial
git init
threatwright
```

## 1. Zonen prüfen (3 min)

Öffnen Sie **Überblick** und scrollen Sie zu **Zonen und Vertrauensgrenzen**. Für das Tutorial reichen die vier Standardzonen. Ihre Bedeutung:

| Zone | Schnittstelle | Bedeutung |
|---|---|---|
| Z-INTERNAL | physisch | nur durch Öffnen des Geräts erreichbar |
| Z-LOCAL | lokal | Schnittstellen am Gerät (USB, Service-Port, Feldbusbuchse) |
| Z-PLANT | bekanntes Netz | Anlagennetz des Betreibers |
| Z-EXTERNAL | externes Netz | Internet, Fernwartung |

Setzen Sie in derselben Tabelle Zugang und Nutzer je Zone und klicken Sie auf **Übernehmen**. Für den Schaltschrank etwa gilt: Zugang „beschränkt“.

## 2. Elemente ins Diagramm ziehen (5 min)

Unter **Diagramm** ziehen Sie aus der Liste links:

1. „Steuerungsrechner Linux“, danach rechts die Zone Z-LOCAL wählen
2. zweimal „Antriebsregler / Servoverstärker“
3. „Remote-I/O / Buskoppler“
4. „Ausgänge mit Sicherheitswirkung“

Jedes Element bringt seine typischen Assets mit, zum Beispiel „Antriebsparameter“ mit der TR-Klasse `Other.Configuration`.

## 3. Feldbus verbinden (3 min)

Wählen Sie oben **Typ neuer Verbindungen: EtherCAT**. Ziehen Sie dann vom Steuerungsrechner zu jedem Antrieb und zum Remote-I/O eine Verbindung. „Automatisch anordnen“ ordnet das Diagramm.

## 4. Bedrohungen mit dem Assistenten (10 min)

Klicken Sie den ersten EtherCAT-Datenfluss an und öffnen Sie **STRIDE-Assistent →**. Übernehmen Sie für T, I und D je die passenden Vorschläge:

- fremder Master am Feldbus
- eingeschleiftes Gerät
- offener Anschluss am Linienende
- Parameterzugriff über die Mailbox
- EoE-Tunnel
- Überlast des Feldbusses

Beantworten Sie jedes Mal die Frage **„Ist die Ursache ein Angriff auf das digitale Produkt?“**. Für alle genannten Vorschläge lautet die Antwort „ja“.

Wiederholen Sie das für die Antriebsregler (Parametermanipulation, Firmware-Download über den Bus) und für die Ausgänge mit Sicherheitswirkung. Die übernommenen Maßnahmen tauchen unter **Maßnahmen** nur einmal auf, auch wenn mehrere Bedrohungen sie vorschlagen.

## 5. Bewerten (5 min)

Unter **Bedrohungen** öffnen Sie jeden Eintrag:

- Schnittstelle und Zugang sind aus Vorlage und Zone vorbelegt. Prüfen Sie, ob sie für Ihr Produkt stimmen.
- Den Impact übernehmen Sie über den Vorschlag aus den Assets oder setzen ihn bewusst anders. Schreiben Sie dann eine Begründung.
- Risiko und „akzeptabel / zu behandeln“ erscheinen sofort. Hinweis: Die Matrix wird „umgekehrt“ gelesen, siehe [Methodik](methodik.md).
- Setzen Sie den Status auf „behandelt“, wenn eine beschlossene Maßnahme das Risiko senkt. Tragen Sie im Feld **Restrisiko nach Maßnahmen** die Bewertung danach ein.

## 6. Abdeckung und Prüfung (2 min)

Unter **Abdeckung** sind Lücken gelb markiert. Schließen Sie jede Lücke, entweder mit „+“ über den Assistenten oder mit „n. r.“ und einer Begründung. Unter **Prüfung** sollten keine Fehler mehr stehen.

## 7. Speichern, committen, Dokument erzeugen

Speichern Sie mit **Strg+S** und committen Sie anschließend:

```
git add . && git commit -m "Teilmodell Feldbus"
threatwright build --format docx
```

Für eine Freigabe setzen Sie einen Tag (`git tag v1.0`). Später zeigt `threatwright diff v1.0` als Änderungsnachweis, was sich seither fachlich geändert hat; siehe [Git-Arbeitsweise](git-arbeitsweise.md).

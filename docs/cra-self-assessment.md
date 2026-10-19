# CRA-Selbsteinschätzung des Werkzeugs

Wie erfüllt Threatwright selbst die Grundanforderungen des Cyber Resilience Act (Verordnung
(EU) 2024/2847, Anhang I)? Diese Seite ist eine ehrliche Bestandsaufnahme, **keine**
Konformitätserklärung. Offene Punkte stehen ausdrücklich unten.

Einordnung: Threatwright ist freie Software (AGPL-3.0) ohne Vertrieb im Rahmen einer
Geschäftstätigkeit. Ob und in welcher Rolle (Hersteller, Open-Source-Steward) der CRA greift,
hängt davon ab, wer das Werkzeug wie bereitstellt. Wer Threatwright in eigene Produkte oder
Dienstleistungen einbaut, ist für diese selbst Hersteller und prüft eigenständig.

## Sichere Voreinstellungen (Anhang I Teil I)

| Anforderung | Umsetzung | Nachweis |
|---|---|---|
| Keine bekannten ausnutzbaren Schwachstellen bei Auslieferung | `pip-audit` und `npm audit` wöchentlich und bei jedem PR (der Release-Workflow selbst prüft das nicht erneut) | `.github/workflows/audit.yml` |
| Sichere Standardkonfiguration | GUI-Server nur auf `127.0.0.1`, zufälliger Port, Sitzungstoken, CSP `default-src 'self'` | ADR-0003, ADR-0007 |
| Schutz vor unbefugtem Zugriff | Kein Netzwerkdienst nach außen; Dateirechte des angemeldeten Benutzers; keine Admin-Rechte nötig | ADR-0007 |
| Vertraulichkeit | Keine Telemetrie, keine CDNs, keine Update-Prüfung, keine Cloud; Modelle bleiben im eigenen Repository | ADR-0007; Testsuite blockiert ausgehende Verbindungen (`tests/conftest.py`) |
| Integrität | Dokumentvorlagen laufen in der Jinja-Sandbox; Importe mit Größengrenzen, ohne XML-Entity-Auflösung, ohne Zip-Slip | ADR-0003, Tests |
| Datenminimierung | Es werden nur die Projektdateien gelesen und geschrieben, die der Benutzer öffnet | — |
| Angriffsfläche minimal | Container-Image ohne GUI-Abhängigkeiten, als Nicht-root-Benutzer; Portable-Build ohne Installer | `Dockerfile`, `packaging/` |
| Protokollierung sicherheitsrelevanter Ereignisse | Änderungshistorie liegt in git (Merge Requests); das Werkzeug selbst protokolliert nicht zentral | — |

## Schwachstellenbehandlung (Anhang I Teil II)

| Anforderung | Umsetzung |
|---|---|
| SBOM | CycloneDX für Python-Abhängigkeiten (aus `uv.lock`) und für das Frontend (npm) an jedem Release; zusätzlich SBOM-Attestierung am Container-Image |
| Schwachstellen zeitnah beheben | Prozess und Zielzeiten in `SECURITY.md` |
| Regelmäßige Tests | CI auf Windows und Linux, Typprüfung, Linting, Ende-zu-Ende-Tests; Abhängigkeits-Audit wöchentlich |
| Offenlegung behobener Schwachstellen | GitHub Security Advisories mit CVE, zusammen mit dem Fix-Release |
| Richtlinie zur koordinierten Offenlegung | `SECURITY.md`; Vorlage `docs/security.txt` (RFC 9116) |
| Kontaktstelle für Meldungen | GitHub Private Vulnerability Reporting (keine persönlichen E-Mail-Adressen) |
| Sichere Verteilung von Updates | Releases mit `SHA256SUMS`, Sigstore-Signatur (keyless) und Build-Provenienz; PyPI per Trusted Publishing; Image auf ghcr.io mit Provenienz; alle Actions per Commit-SHA gepinnt |
| Updates ohne Zusatzkosten, getrennt von Funktionsupdates | Sicherheitsfixes erscheinen als Patch-Release |

## Update-Weg

Das Werkzeug prüft bewusst **nicht** selbst auf Updates (ADR-0007). Benutzer aktualisieren
über den Kanal, über den sie installiert haben:

- `pip install -U threatwright` bzw. `uv tool upgrade threatwright`
- Portable-Build: neues Archiv entpacken, altes Verzeichnis löschen
- CI: Image-Tag in `.gitlab-ci.yml` anheben (`threatwright ci gitlab` erzeugt die Datei mit
  dem Tag der laufenden Version)

Benachrichtigung: „Watch → Custom → Releases / Security alerts“ im GitHub-Repository.

## Unterstützungszeitraum

**Offen:** `<Unterstützungszeitraum, z. B. „jede Minor-Version 12 Monate ab Erscheinen“>`.
Bis zur Version 1.0 erhält nur die jeweils neueste Minor-Version Sicherheitsfixes.

## Offene Punkte

- Kein festgelegter Unterstützungszeitraum (siehe oben).
- Keine externe Sicherheitsprüfung (Penetrationstest, Code-Audit) bisher.
- Reproduzierbare Builds sind nicht nachgewiesen; Provenienz belegt nur, *wo* gebaut wurde.
- LibreOffice (PDF-Erzeugung) wird lokal genutzt und nicht von uns aktualisiert; im
  Container-Image kommt es aus den Debian-Paketquellen zum Build-Zeitpunkt.
- Das Container-Image wird nur beim Release gebaut; Sicherheitsupdates des Basis-Images
  erfordern ein neues Release.
- Die Portable-Builds sind nicht mit einem Code-Signing-Zertifikat (Authenticode) signiert;
  Windows SmartScreen kann warnen. Integrität ist über `SHA256SUMS` und Sigstore prüfbar.
- Rolle unter dem CRA (Hersteller vs. Open-Source-Steward) ist nicht abschließend geklärt.

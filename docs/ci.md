# Threatwright in der CI (GitLab, GitHub)

Die Pipeline prüft jedes Merge Request und erzeugt die Dokumente auf dem Hauptzweig und bei
Tags – reproduzierbar, nicht auf einem Laptop (ADR-0009). Was die GUI prüft, prüft die
Pipeline identisch.

## Was die Pipeline macht

| Auslöser | Job | Ergebnis |
|---|---|---|
| Merge Request | `threatwright validate --strict --format junit` | Testbericht im MR (Fehler und Warnungen blockieren) |
| Hauptzweig, Tags | `threatwright build` für jede konfigurierte Dokumentvorlage | Dokumente als Job-Artefakt `threatwright-out/` |
| Tags | `threatwright diff <vorheriger Tag> <Tag> --format md` | Änderungsnachweis `change-evidence.md` |

Die Jobs laufen im Container-Image `ghcr.io/cpyix/threatwright:<Version>` (CLI und
LibreOffice für PDF). Außer dem Laden des Images braucht die Pipeline **keinen
Netzwerkzugriff**; es wird nichts nachinstalliert. Der Tag ist auf eine Version gepinnt, damit
Dokumente reproduzierbar bleiben.

> Ohne Zugriff auf `ghcr.io` (z. B. in abgeschotteten Netzen) spiegeln Sie das Image in Ihre
> eigene Registry und geben es an
> (`threatwright ci gitlab --image registry.example.local/threatwright:0.1.0`).
> Ohne Internetzugang: Image einmal in die interne Registry spiegeln
> (`docker pull` / `docker tag` / `docker push`) und dort referenzieren.

## Vorlage holen

**Aus der GUI:** *Einstellungen → CI* zeigt die Vorlage bereits für das geöffnete Projekt
ausgefüllt: Projektpfad im Repository, Modelle, Dokumentvorlagen und der Image-Tag der
laufenden Version. „Kopieren“ legt den Text in die Zwischenablage; „In `.gitlab-ci.yml`
schreiben“ legt die Datei im Repository-Wurzelverzeichnis an – nur auf Klick, nie
automatisch. Danach wie jede Änderung committen und per Merge Request einbringen.

**Auf der Kommandozeile:**

```
threatwright ci gitlab pfad/zum/projekt > .gitlab-ci.yml
threatwright ci github pfad/zum/projekt > .github/workflows/threatwright.yml
threatwright ci gitlab --image registry.example.local/threatwright:0.1.0
```

**Von Hand:** `ci/gitlab-ci.yml` bzw. `ci/github-actions.yml` aus diesem Repository kopieren
und `VERSION` sowie `TW_PROJECT` (Projektordner relativ zum Repository) anpassen.

## GitLab einrichten

1. `.gitlab-ci.yml` ins Repository-Wurzelverzeichnis legen (siehe oben).
2. Damit der Testbericht im Merge Request erscheint, ist nichts weiter nötig
   (`artifacts:reports:junit`).
3. Optional: *Settings → Merge requests → Pipelines must succeed* aktivieren, damit nur
   gültige Modelle in den Hauptzweig kommen.
4. Release: Tag setzen (z. B. `v1.2.0`). Die Pipeline baut die Dokumente und den
   Änderungsnachweis gegenüber dem vorherigen Tag; beides unter *Build → Artifacts*.
   Für dauerhafte Aufbewahrung `artifacts:expire_in` in der Vorlage ergänzen oder die Artefakte
   einem Release anhängen.

Hinweise:

- `GIT_DEPTH: "0"` lädt die vollständige Historie, damit der vorherige Tag gefunden wird.
- Das Image startet mit `threatwright` als Entrypoint; die Vorlage setzt deshalb
  `entrypoint: [""]`, damit GitLab Shell-Befehle ausführen kann.
- Liegt das Projekt in einem Unterordner, steht er in `TW_PROJECT`. Mehrere Projekte in einem
  Repository: Jobs pro Projekt duplizieren und `TW_PROJECT` je Job setzen.

## GitHub Actions

Gleiches Verhalten, Datei `.github/workflows/threatwright.yml`. Der JUnit-Bericht wird als
Artefakt `validation-report` hochgeladen; ein fehlgeschlagener Check blockiert den Pull
Request, wenn er als *required status check* eingetragen ist.

## Pre-commit-Hook

Fehler schon vor dem Commit finden: in `.pre-commit-config.yaml` Ihres Repositorys

```yaml
repos:
  - repo: https://github.com/cpyix/threatwright
    rev: v0.1.0            # Version wie im CI-Image
    hooks:
      - id: threatwright-validate
        args: [--strict, pfad/zum/projekt]   # ohne args: Repository-Wurzel
```

dann `pre-commit install`. Der Hook läuft, wenn YAML-Dateien geändert wurden, und installiert
Threatwright beim ersten Lauf einmalig in eine eigene Umgebung (dafür ist einmal
Netzwerkzugriff auf PyPI/GitHub nötig; danach offline).

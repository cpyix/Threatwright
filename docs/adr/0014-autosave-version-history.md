# ADR-0014: Autosave and version history

Status: accepted

## Context
Unsaved work in the GUI was lost when the browser or the server closed. Users also want to go back to an earlier state without Git. At the same time the project files must only change on an explicit save (ADR-0004: Git is the database, saving without changes produces no diff).

## Decision
- The GUI autosaves every 30 seconds while there are unsaved changes, and when the tab is hidden. An autosave is a snapshot of all models of the project, written to `<project>/.threatwright-history/` as one compressed JSON file. The project's YAML files are not touched.
- Every explicit save that writes files adds a snapshot too, so the history shows saved and autosaved states side by side.
- The folder contains a `.gitignore` with `*`: it is never committed, whatever the project's own Git settings are.
- "Restore" loads a snapshot into the editor as an ordinary, undoable change. It reaches the files only with the next save.
- When a project is opened and its newest snapshot is an autosave, the GUI offers to restore it once (crash recovery). Opening records the state on disk, so the offer does not repeat.
- At most 200 snapshots are kept; older ones are deleted.

## Consequences
- The history is per project folder and per machine; it is not shared through Git. Shared history remains Git's job (tags, merge requests).
- Snapshot ids are validated against a fixed pattern and looked up in the folder listing; client input never forms a path.
- A snapshot holds model content and is as sensitive as the project files next to it.

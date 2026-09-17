# Persistent chat history validation

Validated on 2026-09-16 against repository source and the running NORA live guest.

- All 50 non-GUI tests passed on the host, including five new storage tests for
  multi-chat round trips, active chat restoration, file permissions, deletion,
  transaction rollback on failure, invalid state, and the XDG storage path.
- All 12 GTK integration tests passed separately inside NORA (16.132 seconds on
  the final run).
  These include restoring transcripts and context after closing, preserving both
  drafts without executing them, isolating context when switching chats, deleting
  all context followed by reopening, cancelling pending autosave on deletion,
  blocking switches/deletion while busy, ignoring late results, and reporting save
  or delete failures without discarding the current chat. Existing command-pane
  execution, proposal, cancellation, and failure checks still pass.
- A real mouse test exposed a GTK crash caused by replacing the selected sidebar
  row inside its selection callback. Rows now update in place, and the tests
  assert that the selected widget stays attached to the list. Repeated actual
  mouse selection in both directions restored the correct chats without a crash.
- The host discovers 62 tests and skips the 12 GTK tests because GTK/display is
  unavailable there. Guest tests use temporary databases, not real chat history.
- In the actual application, created disk-space and RAM chats. Closed the window
  normally and reopened it: both sidebar tabs, the last active chat, and its answer
  returned. Visually checked the maximized three-column layout at 1280×800.
- Visually checked Settings and its clear-history confirmation. Actual deletion
  and reopening are covered with isolated test data by the GTK tests.
- Python syntax, Git whitespace, and Actions workflow checks passed.

Local evidence: `.build/chat/history-tests.log`, `dist/history-tests.png`,
`dist/history-startup.png`, `dist/history-reopened.png`, and
`dist/history-settings.png`, `dist/history-confirm.png`,
`dist/history-switched.png`, and `dist/history-final.png`.
Guest GUI log: `/tmp/nora-history-tests.log`.

The source and running application's temporary overlay were updated. The existing
ISO and published GitHub release were not rebuilt or changed. Full reboot
persistence was not tested; it requires installed or persistent storage. The live
guest currently loses its writable overlay at shutdown.

History is stored locally in a private SQLite file, without encryption. Clear all
removes app-managed saved state and resets the in-memory chat. It does not undo
executed commands or delete their files, filesystem snapshots, or external backups.
Recent context remains bounded for the small local model even though full display
transcripts are retained. No new model inference was required for these storage/UI
checks; model-proposal tests use controlled responses.

# NORA website reader validation

Validated on 2026-09-16 against the repository source and a live guest update.
This does not modify the existing ISO or the earlier GitHub release.

Passed:

- All 45 tests: the existing 34 tests plus 11 website-reader tests using a local
  HTTP fixture. These cover the user's natural-language request, URL validation,
  actual HTML extraction and links, redirects, HTTP errors, unsupported and empty
  content, download/text limits, bounded gzip inflation, cancellation before and
  during a read, an overall timeout, and bounded source context for the model.
- Python syntax and Git whitespace checks.
- A real host-side HTTPS request to `https://noralinux.com/` returned the title
  “NORA Linux — Talk to your operating system.” and 5,009 characters of extracted
  page text at test time.
- After updating the live NORA guest, the exact request **“Look up noralinux.com”**
  fetched the page inside the guest and displayed its title, source URL, timestamp,
  and content. The result included “Natural Operating Reasoning Assistant.”
- With the guest's network link temporarily disabled, `/web https://example.com`
  reported a DNS/network failure and returned the UI to ready state. Networking
  was restored after this check.

Evidence: `dist/web-startup.png`, `dist/web-noralinux.png`, and
`dist/web-offline.png`, plus `.build/chat/web-tests.log` (local, ignored build/test
files). Model context delivery is covered by automated tests; a complete generated
website summary in the emulated guest has not been validated in this change.

The updater transferred only application Python files through a container-loopback
HTTP endpoint into the guest's temporary overlay and restarted NORA Terminal.
It did not rebuild the ISO or replace the model. The source overlay includes the
new module automatically in future live-build/GitHub Actions builds.

The reader accepts HTML and plain text over HTTP(S); it does not render JavaScript,
reuse browser login sessions, read PDFs, or provide a general search engine.
Long pages are explicitly excerpted. Follow-up prompts receive up to 1,800 UTF-8
bytes of selected page text, with a source URL and fetch time. The tiny local model
can still misinterpret or omit facts. Network fetching and model reasoning are
separate: the former is bounded to 30 seconds, while model inference can be much
slower under this VM's amd64-on-ARM CPU emulation.

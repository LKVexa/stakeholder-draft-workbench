# Security and authorship boundaries

This library has no network, mail or publishing API. Draft generation never
authorizes sending. A human must review and take responsibility for every message.

Sensitivity screening is a small English keyword heuristic plus explicit flags,
not a reliable classifier of all sensitive, legal, personnel or relationship
content. Public/internal labels come from callers and are not access controls.
Use trusted labeling and independent authorization in an integration.

Bodies are plain text; escape HTML/Markdown and disable active links or mentions
as appropriate in any UI. Statements and trace metadata can contain confidential
or misleading material. Input truth, source rights and recipient suitability are
not verified. No general personal-data or secret redaction is provided.

SHA-256 digests detect accidental changes to artifacts, not malicious callers who
can recompute them. Unsalted hashes can reveal predictable content. Persist,
authorize and authenticate inputs and audit records outside this library.

Size limits support ordinary API use, not hostile in-process Python code or every
resource exhaustion attack. Network services need request limits and process
isolation. No third-party runtime dependencies exist; no build-tool vulnerability
scan is claimed. Report defects privately using synthetic examples.

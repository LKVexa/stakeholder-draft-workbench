# Stakeholder Draft Workbench

**0.1.2a1 — experimental partial candidate, JY-S012-P001**

A deterministic Python library for capturing communication briefs, validating
typed statements, and drafting English updates for human review. It has no
message transport. A human remains the final author and sender.

## Install and use

Python 3.10 or newer; no third-party runtime dependencies.

~~~sh
python -m pip install .
python -m unittest discover -s tests -t .
~~~

~~~python
from stakecomm.core import capture_brief, extract_facts, draft_communication

brief = capture_brief({
    "audience": "customer", "intent": "explain the deployment",
    "technical_fluency": "non-technical", "language": "en",
    "formality": "formal", "recipient_scope": "external",
})
facts = extract_facts([{
    "artifact_id": "deployment-42",
    "statements": [{"kind": "delta", "visibility": "public",
                    "text": "We completed a rollback to version 1.4.2."}],
}])
draft = draft_communication(brief, facts)
assert draft["sent"] is False
~~~

Audience accepts engineering/executive/customer/partner; fluency accepts
technical/semi-technical/non-technical; formality accepts formal/neutral/casual.
Statement kinds are fact/delta/open-risk/requirement, with public/internal visibility.
The extractor validates statements supplied by the caller; it does not discover,
verify or establish the truth of facts.

## Draft and review boundaries

English tags such as en and en-US are supported. Other valid language tags produce
HUMAN_ONLY with no body; this candidate does not translate. Technical wording
is preserved, while other fluencies add explanations alongside original terms.
Numbers and proper identifiers are checked; an adaptation that fails the check
falls back to the original statement. The checker is lexical, not semantic.

Sensitivity checks use a bounded keyword vocabulary with Unicode normalization,
word boundaries and punctuation handling. Explicit boolean sensitive or
relationship_critical flags may be set on briefs, artifacts or statements.
Artifact flags propagate and cannot be cleared by a statement. Any hit or true
flag yields HUMAN_ONLY without a body. Screening is incomplete; the human must
review context and relationship sensitivity even when the status is DRAFT.

Internal facts are withheld from external draft bodies. Exclusion entries expose
only a content digest and reason, not internal artifact names. Internal-only
sensitivity hits do not expose their keywords in external draft results. A
withholding outcome still reveals that material was withheld.

Bodies are plain text. Source statements may contain HTML, Markdown, links,
mentions or misleading claims. Escape them when displaying in a rich interface;
never treat the output as approved content or as instructions for another tool.
Fact traces are review metadata, not a recipient-ready message.

## Integrity, limits and compatibility

Captured briefs and extracted facts have canonical SHA-256 content digests.
Downstream APIs validate the digest and schema before use. Drafts carry brief,
facts and draft digests; none are signatures, authentication or proof of truth.
The raw statement digest identifies the submitted statement, including optional
metadata; the fact digest binds the projected text, visibility, flags and provenance.
Hashes do not anonymize predictable data. Re-extract after intentional changes.

Limits: 1,000 artifacts, 5,000 total statements/facts, 65,536 characters per
statement, 512 per artifact identifier, 4,096 per intent, 35 per language tag,
40 JSON nesting levels and 8 MiB per canonical input/output model. Artifact IDs
and statement provenance must be unique. Displayed text must be single-line
without control/format characters. Invalid input raises ValueError.

Version 0.1.1-partial -> 0.1.2a1 changes validation and artifact digests.
Regenerate captured briefs and extracted facts. Excluded facts now use a digest
instead of raw provenance; non-English requests abstain. Acronyms and jargon are
retained alongside glosses, and p99 is described as a percentile.

66 tests comprise 26 inherited checks and 40 new regressions. Two inherited gloss
expectations and one exclusion-metadata assertion were updated for the corrected
contract. Source and installed-wheel results: [CHECK_RUNS](docs/CHECK_RUNS.json).
See [AUDIT](docs/AUDIT.md) and [SECURITY](SECURITY.md). CI tests Linux Python
3.10/3.12/3.14 and Windows Python 3.12.

Model drafting, translation, integrations and the original phase/gate roadmap
remain outside this candidate. No production readiness is claimed.

## License

Copyright 2026 **RUSSELL PHILIP SMITHSON**.
[Apache License 2.0](LICENSE), with [NOTICE](NOTICE).
No third-party code is vendored.

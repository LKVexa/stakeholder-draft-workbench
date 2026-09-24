# Audit and hardening — 0.1.2a1

Date: 2026-09-23. Source: JY-S012-P001 / 0.1.1-partial / run-0001 / product.
Reviewed all brief, extraction, screening, drafting and nuance-check code.
Original source remains separate from the release checkout.

## Repaired findings

- Brief and fact mutations could reuse stale digests, changing recipient scope,
  statements or visibility undetected. Canonical, schema-validated digests now
  bind these values and their provenance before screening or drafting.
- Malformed collections and provenance could cause unstructured exceptions.
  Bounded JSON-only models, explicit types and unique artifact/statement identity
  now reject invalid input with ValueError.
- Sensitivity phrases with punctuation were missed, substring matches produced
  false positives, and explicit sensitive flags were ignored. Normalized word
  matching and propagated boolean flags address these cases. Screening remains
  heuristic and incomplete.
- External draft metadata exposed internal artifact names and sensitive keywords.
  Exclusion digests and filtered keyword diagnostics reduce this disclosure.
- Non-English briefs generated English text labeled as another language.
  Unsupported languages now return HUMAN_ONLY without a body.
- Jargon replacement dropped uppercase identifiers and p99 used an imprecise
  gloss. Original terms now remain alongside explanations, with a percentile
  description for p99. Failed lexical checks fall back to original statements.
- Multiline/control characters made trace line references unreliable and enabled
  misleading display. Single-line statements and control-character rejection
  preserve exact trace-to-body line references.
- Shared mutable language templates are now immutable mappings.

## Verification and compatibility

26 inherited tests passed before changes. 66 source and installed-wheel tests
pass after changes, including 40 regressions. Two old gloss expectations and one
exclusion-metadata assertion reflect the corrected contract. Historical evidence
is retained separately. CI covers Linux 3.10/3.12/3.14 and Windows 3.12.

Version 0.1.1-partial -> 0.1.2a1. Regenerate brief/fact artifacts; validation is
stricter, exclusions omit raw provenance and non-English drafting abstains.
Added packaging, pinned-action CI, README, security documentation and Apache 2.0
LICENSE/NOTICE naming RUSSELL PHILIP SMITHSON.

No third-party runtime dependencies require upgrades. No build-tool vulnerability
scan or exhaustive security review is claimed. Statements remain caller supplied,
and digests are not authenticity or truth proofs. Human authorship and the
original candidate roadmap remain mandatory boundaries.

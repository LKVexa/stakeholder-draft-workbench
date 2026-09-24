# 0.1.2a1 — 2026-09-23

- Bind briefs, facts and drafts to validated canonical content digests.
- Bound input models; reject duplicate provenance and multiline display text.
- Improve sensitivity handling and remove internal metadata from exclusions.
- Preserve original terms in explanations; abstain for unsupported languages.
- Add 40 regressions, packaging, CI, README and Apache 2.0 LICENSE/NOTICE.
- Compatibility: regenerate captured briefs and facts with the new constructors.

# Changelog — Stakeholder Communication Draft Workbench

## 0.1.1-partial (2026-09-14)

Maintenance/hardening release by JY Individual Program Audit, Upgrade &
Hardening Factory (audit A013). Repairs only; no capability changes.

Baseline fingerprint: build-0001 product.zip
sha256 4ce4b67991948e966edebd32d5e744d83844ebfdab1e9f077d2c45c4c6257055
(version 0.1.0-partial; 12/12 baseline tests passing).

All findings below were reproduced on the baseline by live probes before
fixing, and each fix is covered by new positive+negative tests.

### A013-F1 — statement `text` not validated (KeyError/TypeError leak)
- Observed: `extract_facts` with a statement missing `text` raised bare
  `KeyError: 'text'`; a non-string `text` passed validation and later
  crashed `draft_communication` with `TypeError` inside
  `sensitivity_screen`.
- Expected: documented `ValueError` at extraction time.
- Fix: `extract_facts` now requires a string `text` field.

### A013-F2 — aliasing of returned mutable objects
- Observed: mutating `fact_trace[n]["provenance"]` or
  `excluded_facts[n]["provenance"]` on a returned draft mutated the
  caller's input facts (and vice versa); `capture_brief` shared nested
  mutables with the raw input.
- Expected: returned structures are isolated from inputs.
- Fix: provenance dicts are deep-copied into trace/excluded entries;
  `capture_brief` deep-copies the raw brief.

### A013-F3 — non-strict canonicalization (NaN accepted in digests)
- Observed: `_digest` used `json.dumps` with default `allow_nan=True`,
  so briefs/statements containing NaN/Infinity got a "canonical" sha256
  digest over non-canonical JSON.
- Expected: strict canonical JSON; non-canonicalizable content rejected.
- Fix: `allow_nan=False`, with `ValueError` raised for
  non-JSON-canonicalizable content.

### A013-F4 — error-contract leaks for malformed briefs/artifacts
- Observed: `draft_communication` on an un-captured brief raised bare
  `KeyError: 'brief_digest'`; `sensitivity_screen({})` raised
  `KeyError: 'intent'`; non-string brief fields raised `TypeError`;
  `statements` as a non-list raised `AttributeError`; non-dict
  statements/artifacts raised `AttributeError`/`TypeError`.
- Expected: documented `ValueError` for invalid inputs.
- Fix: explicit type/shape validation in `capture_brief`,
  `sensitivity_screen`, `draft_communication`, `extract_facts`.

### Compatibility
- All valid-input behavior is byte-identical (draft bodies, digests,
  traces unchanged); all 12 baseline tests pass unmodified.
- Previously-crashing invalid inputs now raise `ValueError` instead of
  bare KeyError/TypeError/AttributeError; NaN-bearing content is now
  rejected instead of silently digested.

### Rollback
- Restore build-0001 product.zip
  (sha256 4ce4b67991948e966edebd32d5e744d83844ebfdab1e9f077d2c45c4c6257055).
  No data formats changed; `stakecomm/draft/v1` schema unchanged.

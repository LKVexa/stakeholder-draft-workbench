"""Bounded, deterministic communication drafting; no transport capability."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from types import MappingProxyType

VERSION = "0.1.2a1"
AUDIENCES = ("engineering", "executive", "customer", "partner")
FLUENCY = ("technical", "semi-technical", "non-technical")
FORMALITY = ("formal", "neutral", "casual")
FACT_KINDS = ("fact", "delta", "open-risk", "requirement")
MAX_BYTES = 8 * 1024 * 1024
MAX_FACTS = 5000
_SENSITIVE_MARKERS = ("layoff", "termination", "legal action", "lawsuit",
    "security breach", "compensation", "salary", "acquisition", "resignation",
    "disciplinary", "relationship critical")
_JARGON = MappingProxyType({
    "p99": "the 99th-percentile latency",
    "rollback": "reverting to the previous version",
    "regression": "a previously working behavior that broke",
    "sbom": "a full inventory of software components",
    "rca": "root-cause analysis",
})
_OPENING = MappingProxyType({"formal": "Dear stakeholders,", "neutral": "Hi all,",
                            "casual": "Hey team,"})
_KIND_LABEL = MappingProxyType({"fact": "Update", "delta": "What changed",
                               "open-risk": "Open risk", "requirement": "What we need"})


def _canonical(obj) -> str:
    def check(value, depth=0):
        if depth > 40:
            raise ValueError("JSON nesting exceeds 40 levels")
        if type(value) is dict:
            if any(type(k) is not str for k in value):
                raise ValueError("JSON object keys must be strings")
            for v in value.values():
                check(v, depth + 1)
        elif type(value) is list:
            for v in value:
                check(v, depth + 1)
        elif type(value) not in (str, int, float, bool, type(None)):
            raise ValueError("only JSON values are supported")
    try:
        check(obj)
        payload = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                             allow_nan=False, ensure_ascii=False)
        if len(payload.encode("utf-8")) > MAX_BYTES:
            raise ValueError("JSON content exceeds 8 MiB")
        return payload
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise ValueError("invalid or oversized JSON content") from exc


def _digest(obj) -> str:
    return "sha256:" + hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _text(value, field, limit):
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must be a nonempty bounded string")
    if any(unicodedata.category(c).startswith("C") or c in "\u2028\u2029"
           for c in value):
        raise ValueError(f"{field} must contain a single line without control characters")
    return value


def _flags(raw):
    for key in ("sensitive", "relationship_critical"):
        if key in raw and type(raw[key]) is not bool:
            raise ValueError(f"{key} must be boolean")


def capture_brief(raw: dict) -> dict:
    if type(raw) is not dict or "brief_digest" in raw:
        raise ValueError("brief must be a raw dictionary without a digest")
    _canonical(raw)
    for key, choices in (("audience", AUDIENCES), ("technical_fluency", FLUENCY),
                         ("formality", FORMALITY),
                         ("recipient_scope", ("internal", "external"))):
        if raw.get(key) not in choices:
            raise ValueError(f"invalid {key}")
    _text(raw.get("intent"), "intent", 4096)
    _text(raw.get("language"), "language", 35)
    if not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", raw["language"]):
        raise ValueError("language must be a language tag")
    _flags(raw)
    return dict(copy.deepcopy(raw), brief_digest=_digest(raw))


def _brief(brief):
    if type(brief) is not dict or "brief_digest" not in brief:
        raise ValueError("use capture_brief")
    raw = {k: v for k, v in brief.items() if k != "brief_digest"}
    expected = capture_brief(raw)
    if expected != brief:
        raise ValueError("brief digest mismatch; recapture the brief")
    return expected


def extract_facts(artifacts: list[dict]) -> list[dict]:
    if type(artifacts) is not list or len(artifacts) > 1000:
        raise ValueError("artifacts must be a list of at most 1000 entries")
    _canonical(artifacts)
    out, seen = [], set()
    for artifact in artifacts:
        if type(artifact) is not dict:
            raise ValueError("artifact must be a dictionary")
        identifier = _text(artifact.get("artifact_id"), "artifact_id", 512)
        if identifier in seen:
            raise ValueError("duplicate artifact_id")
        seen.add(identifier)
        _flags(artifact)
        statements = artifact.get("statements")
        if type(statements) is not list or len(out) + len(statements) > MAX_FACTS:
            raise ValueError("statements must be lists with at most 5000 total entries")
        for index, statement in enumerate(statements):
            if type(statement) is not dict or statement.get("kind") not in FACT_KINDS:
                raise ValueError("invalid statement kind")
            if statement.get("visibility") not in ("internal", "public"):
                raise ValueError("invalid statement visibility")
            _text(statement.get("text"), "statement text", 65536)
            _flags(statement)
            fact = {k: statement[k] for k in ("kind", "text", "visibility")}
            for key in ("sensitive", "relationship_critical"):
                fact[key] = artifact.get(key, False) or statement.get(key, False)
            fact["provenance"] = {"artifact_id": identifier, "index": index,
                                  "statement_digest": _digest(statement)}
            fact["fact_digest"] = _digest(fact)
            out.append(fact)
    return out


def _facts(facts):
    if type(facts) is not list or len(facts) > MAX_FACTS:
        raise ValueError("facts must be a list with at most 5000 entries")
    _canonical(facts)
    seen = set()
    for fact in facts:
        if type(fact) is not dict or set(fact) != {
                "kind", "text", "visibility", "sensitive", "relationship_critical",
                "provenance", "fact_digest"}:
            raise ValueError("use extract_facts")
        if fact["kind"] not in FACT_KINDS or fact["visibility"] not in ("internal", "public"):
            raise ValueError("invalid fact kind or visibility")
        _text(fact["text"], "fact text", 65536)
        _flags(fact)
        provenance = fact["provenance"]
        if type(provenance) is not dict or set(provenance) != {
                "artifact_id", "index", "statement_digest"}:
            raise ValueError("invalid provenance")
        _text(provenance["artifact_id"], "artifact_id", 512)
        if type(provenance["index"]) is not int or not 0 <= provenance["index"] < MAX_FACTS:
            raise ValueError("invalid statement index")
        if type(provenance["statement_digest"]) is not str or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", provenance["statement_digest"]):
            raise ValueError("invalid statement digest")
        identity = (provenance["artifact_id"], provenance["index"])
        if identity in seen:
            raise ValueError("duplicate statement provenance")
        seen.add(identity)
        if fact["fact_digest"] != _digest({k: v for k, v in fact.items() if k != "fact_digest"}):
            raise ValueError("fact digest mismatch; re-extract facts")
    return copy.deepcopy(facts)


def _screen(brief, facts):
    texts = [brief["intent"]] + [f["text"] for f in facts]
    normalized = [re.sub(r"[\W_]+", " ", unicodedata.normalize("NFKC", t).casefold())
                  for t in texts]
    hits = sorted(m for m in _SENSITIVE_MARKERS if any(re.search(
        r"\b" + r"\s+".join(map(re.escape, m.split())) + r"s?\b", t) for t in normalized))
    explicit = any(obj.get("sensitive", False) or obj.get("relationship_critical", False)
                   for obj in [brief] + facts)
    return {"sensitive": bool(hits) or explicit, "markers": hits,
            "explicit_flag": explicit}


def sensitivity_screen(brief: dict, facts: list[dict]) -> dict:
    """Advisory keyword/explicit-flag screening, not a complete safety classifier."""
    return _screen(_brief(brief), _facts(facts))


def _render_statement(text: str, fluency: str) -> str:
    if fluency == "technical":
        return text
    def replace(match):
        term = match.group()
        gloss = _JARGON[term.lower()]
        return (f"{term} ({gloss})" if fluency == "semi-technical"
                else f"{gloss} ({term})")
    # A single pass never reprocesses inserted explanations.
    return re.sub(r"(?<![\w-])(?:" + "|".join(_JARGON) + r")(?![\w-])",
                  replace, text, flags=re.I)


def _nuance_check(original: str, rendered: str) -> bool:
    tokens = re.findall(r"\b\d[\w.%+-]*|\b[A-Z][A-Za-z0-9_-]*\b", original)
    return all(re.search(r"(?<!\w)" + re.escape(token) + r"(?!\w)", rendered)
               for token in tokens)


def draft_communication(brief: dict, facts: list[dict]) -> dict:
    brief, facts = _brief(brief), _facts(facts)
    base = {"schema": "stakecomm/draft/v1", "workbench_version": VERSION,
            "brief_digest": brief["brief_digest"], "facts_digest": _digest(facts),
            "sent": False, "human_is_final_author_and_sender": True,
            "body_format": "text/plain"}
    screen = _screen(brief, facts)
    if screen["sensitive"]:
        # Do not return internal keyword hits in an external draft response.
        visible = facts if brief["recipient_scope"] == "internal" else [
            f for f in facts if f["visibility"] == "public"]
        safe_screen = _screen(brief, visible)
        result = dict(base, status="HUMAN_ONLY",
                      reason="sensitive or relationship-critical content requires human authorship (GRD-02)",
                      markers=safe_screen["markers"], body=None)
    elif brief["language"].lower().split("-")[0] != "en":
        result = dict(base, status="HUMAN_ONLY",
                      reason="this deterministic candidate supports English only",
                      markers=[], body=None)
    else:
        excluded, usable = [], []
        for fact in facts:
            if brief["recipient_scope"] == "external" and fact["visibility"] == "internal":
                excluded.append({"fact_digest": fact["fact_digest"],
                                 "reason": "internal-only fact withheld (GRD-03)"})
            else:
                usable.append(fact)
        lines, trace = [_OPENING[brief["formality"]], ""], []
        for fact in usable:
            rendered = _render_statement(fact["text"], brief["technical_fluency"])
            preserved = _nuance_check(fact["text"], rendered)
            if not preserved:
                rendered = fact["text"]
            lines.append(f"{_KIND_LABEL[fact['kind']]}: {rendered}")
            trace.append({"line": len(lines) - 1, "rendered": rendered,
                          "original": fact["text"], "nuance_preserved": True,
                          "adaptation_fallback": not preserved,
                          "fact_digest": fact["fact_digest"],
                          "provenance": copy.deepcopy(fact["provenance"])})
        lines += ["", "[DRAFT — review, edit, and send yourself; this tool cannot and will not send]"]
        result = dict(base, status="DRAFT", language=brief["language"],
                      body="\n".join(lines), fact_trace=trace, excluded_facts=excluded,
                      open_risk_count=sum(f["kind"] == "open-risk" for f in usable))
    result["draft_digest"] = _digest(result)
    return result

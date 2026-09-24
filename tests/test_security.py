import copy
import unittest
from unittest.mock import patch
from stakecomm.core import (capture_brief, extract_facts, draft_communication,
                            sensitivity_screen)
from tests.test_stakecomm import BRIEF_RAW, ARTIFACTS


class Regression(unittest.TestCase):
    def setUp(self):
        self.brief = capture_brief(BRIEF_RAW)
        self.facts = extract_facts(ARTIFACTS)

    def fact(self, text, **kwargs):
        return extract_facts([{"artifact_id": "a", "statements": [
            dict(kind="fact", text=text, visibility="public", **kwargs)]}])

    def test_brief_change_rejected(self):
        self.brief["recipient_scope"] = "internal"
        with self.assertRaises(ValueError):
            draft_communication(self.brief, self.facts)

    def test_screen_validates_brief(self):
        self.brief["intent"] = "updated"
        with self.assertRaises(ValueError):
            sensitivity_screen(self.brief, self.facts)

    def test_fact_text_change_rejected(self):
        self.facts[0]["text"] = "unfounded claim"
        with self.assertRaises(ValueError):
            draft_communication(self.brief, self.facts)

    def test_visibility_change_rejected(self):
        self.facts[-1]["visibility"] = "public"
        with self.assertRaises(ValueError):
            draft_communication(self.brief, self.facts)

    def test_provenance_change_rejected(self):
        self.facts[0]["provenance"]["index"] = 4
        with self.assertRaises(ValueError):
            sensitivity_screen(self.brief, self.facts)

    def test_duplicate_fact_rejected(self):
        with self.assertRaises(ValueError):
            draft_communication(self.brief, self.facts + [self.facts[0]])

    def test_uncaptured_facts_rejected(self):
        with self.assertRaises(ValueError):
            draft_communication(self.brief, [{"text": "hello"}])

    def test_duplicate_artifact_rejected(self):
        with self.assertRaises(ValueError):
            extract_facts(ARTIFACTS + ARTIFACTS)

    def test_invalid_artifact_collection(self):
        for raw in (None, {}, "hello", ()):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                extract_facts(raw)

    def test_invalid_fact_collection(self):
        for raw in (None, {}, "hello", [None]):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                sensitivity_screen(self.brief, raw)

    def test_invalid_artifact_identifier(self):
        for identifier in ("", [], 42, "x" * 513, "secret\ninjected"):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                extract_facts([{"artifact_id": identifier, "statements": []}])

    def test_reserved_brief_digest(self):
        with self.assertRaises(ValueError):
            capture_brief(self.brief)

    def test_blank_brief_fields(self):
        for key in ("intent", "language"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                capture_brief(dict(BRIEF_RAW, **{key: " "}))

    def test_control_and_multiline_statement_rejected(self):
        for text in ("hello\nworld", "x\ry", "a\tb", "x\u202ey", "x\u2028y", "x\u200by"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.fact(text)

    def test_empty_statement_rejected(self):
        with self.assertRaises(ValueError):
            self.fact("")

    def test_statement_size_limit(self):
        with self.assertRaises(ValueError):
            self.fact("x" * 65537)

    def test_fact_count_limit(self):
        statement = {"kind": "fact", "text": "ok", "visibility": "public"}
        with self.assertRaises(ValueError):
            extract_facts([{"artifact_id": "a", "statements": [statement] * 5001}])

    def test_artifact_count_limit(self):
        with self.assertRaises(ValueError):
            extract_facts([{}] * 1001)

    def test_json_nonstring_key_rejected(self):
        with self.assertRaises(ValueError):
            capture_brief(dict(BRIEF_RAW, extra={1: "x"}))

    def test_json_tuple_rejected(self):
        with self.assertRaises(ValueError):
            capture_brief(dict(BRIEF_RAW, extra=(1, 2)))

    def test_json_cycle_rejected(self):
        value = []
        value.append(value)
        with self.assertRaises(ValueError):
            capture_brief(dict(BRIEF_RAW, extra=value))

    def test_json_surrogate_rejected(self):
        with self.assertRaises(ValueError):
            capture_brief(dict(BRIEF_RAW, extra="\ud800"))

    def test_explicit_sensitive_brief(self):
        brief = capture_brief(dict(BRIEF_RAW, sensitive=True))
        self.assertIsNone(draft_communication(brief, [])["body"])

    def test_explicit_relationship_statement(self):
        facts = self.fact("We need a conversation.", relationship_critical=True)
        self.assertEqual(draft_communication(self.brief, facts)["status"], "HUMAN_ONLY")

    def test_artifact_flag_cannot_be_cleared(self):
        facts = extract_facts([{"artifact_id": "a", "sensitive": True, "statements": [
            {"kind": "fact", "text": "hello", "visibility": "public", "sensitive": False}]}])
        self.assertIsNone(draft_communication(self.brief, facts)["body"])

    def test_flags_must_be_boolean(self):
        for value in (0, "false", [], None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                capture_brief(dict(BRIEF_RAW, sensitive=value))

    def test_punctuated_sensitive_phrases(self):
        for text in ("security-breach", "LEGAL_ACTION", "relationship—critical",
                     "ＳＥＣＵＲＩＴＹ ＢＲＥＡＣＨ", "layoffs"):
            with self.subTest(text=text):
                self.assertTrue(sensitivity_screen(self.brief, self.fact(text))["sensitive"])

    def test_keywords_use_boundaries(self):
        self.assertFalse(sensitivity_screen(self.brief, self.fact("The determination is final."))["sensitive"])

    def test_internal_sensitive_hit_not_disclosed(self):
        facts = extract_facts([{"artifact_id": "private", "statements": [
            {"kind": "fact", "text": "salary", "visibility": "internal"}]}])
        result = draft_communication(self.brief, facts)
        self.assertIsNone(result["body"])
        self.assertEqual(result["markers"], [])

    def test_excluded_identifiers_not_disclosed(self):
        result = draft_communication(self.brief, self.facts)
        self.assertNotIn("provenance", result["excluded_facts"][0])
        self.assertIn("fact_digest", result["excluded_facts"][0])

    def test_unsupported_language_abstains(self):
        brief = capture_brief(dict(BRIEF_RAW, language="fr-FR"))
        self.assertIsNone(draft_communication(brief, self.facts)["body"])

    def test_english_region_tag_supported(self):
        brief = capture_brief(dict(BRIEF_RAW, language="en-US"))
        self.assertEqual(draft_communication(brief, [])["status"], "DRAFT")

    def test_original_acronyms_preserved(self):
        result = draft_communication(self.brief, self.fact("RCA and SBOM track Service-A v1.2.3 at 99.9%."))
        for token in ("RCA", "SBOM", "Service-A", "v1.2.3", "99.9%"):
            self.assertIn(token, result["body"])
        self.assertTrue(result["fact_trace"][0]["nuance_preserved"])

    def test_trace_exact_body_line(self):
        result = draft_communication(self.brief, self.facts)
        for trace in result["fact_trace"]:
            self.assertTrue(result["body"].splitlines()[trace["line"]].endswith(trace["rendered"]))

    def test_adaptation_failure_falls_back_to_original(self):
        facts = self.fact("Service-A runs at 99.9%.")
        with patch("stakecomm.core._render_statement", return_value="all fine"):
            result = draft_communication(self.brief, facts)
        self.assertEqual(result["fact_trace"][0]["rendered"], facts[0]["text"])
        self.assertTrue(result["fact_trace"][0]["adaptation_fallback"])

    def test_content_digests_bound_and_stable(self):
        result = draft_communication(self.brief, self.facts)
        again = draft_communication(capture_brief(dict(reversed(list(BRIEF_RAW.items())))), self.facts)
        self.assertEqual(result, again)
        shorter = draft_communication(self.brief, self.facts[:-1])
        self.assertNotEqual(result["facts_digest"], shorter["facts_digest"])
        self.assertNotEqual(result["draft_digest"], shorter["draft_digest"])

    def test_templates_are_immutable(self):
        from stakecomm.core import _JARGON
        with self.assertRaises(TypeError):
            _JARGON["p99"] = "wrong"

    def test_fact_output_does_not_alias_source(self):
        artifacts = copy.deepcopy(ARTIFACTS)
        facts = extract_facts(artifacts)
        artifacts[0]["statements"][0]["text"] = "changed"
        self.assertNotEqual(facts[0]["text"], "changed")

    def test_hyphenated_identifier_not_rewritten(self):
        facts = self.fact("Use api-rollback and sbom-tool.")
        result = draft_communication(self.brief, facts)
        self.assertEqual(result["fact_trace"][0]["rendered"], facts[0]["text"])

    def test_marker_cannot_span_statements(self):
        brief = capture_brief(dict(BRIEF_RAW, intent="review security"))
        facts = self.fact("breach of the old formatting convention")
        self.assertFalse(sensitivity_screen(brief, facts)["sensitive"])

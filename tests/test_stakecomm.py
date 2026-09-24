import unittest

from stakecomm.core import (capture_brief, draft_communication, extract_facts,
                            sensitivity_screen)

BRIEF_RAW = {"audience": "customer", "intent": "explain the outage fix",
             "technical_fluency": "non-technical", "language": "en",
             "formality": "formal", "recipient_scope": "external"}

ARTIFACTS = [{
    "artifact_id": "postmortem-42",
    "statements": [
        {"kind": "fact", "text": "The p99 latency rose to 2.1s during the incident.",
         "visibility": "public"},
        {"kind": "delta", "text": "We completed a rollback to version 1.4.2.",
         "visibility": "public"},
        {"kind": "open-risk", "text": "A regression in the cache layer is still "
                                      "under investigation.", "visibility": "public"},
        {"kind": "requirement", "text": "Internal RCA doc must be finished by Friday.",
         "visibility": "internal"},
    ],
}]


class Brief(unittest.TestCase):
    def test_capture_ok(self):
        b = capture_brief(BRIEF_RAW)
        self.assertTrue(b["brief_digest"].startswith("sha256:"))

    def test_validation(self):
        for bad in ({**BRIEF_RAW, "audience": "aliens"},
                    {**BRIEF_RAW, "technical_fluency": "psychic"},
                    {**BRIEF_RAW, "recipient_scope": "everyone"}):
            with self.assertRaises(ValueError):
                capture_brief(bad)


class Facts(unittest.TestCase):
    def test_extract_with_provenance(self):
        facts = extract_facts(ARTIFACTS)
        self.assertEqual(len(facts), 4)
        self.assertEqual(facts[0]["provenance"]["artifact_id"], "postmortem-42")
        self.assertTrue(facts[0]["provenance"]["statement_digest"].startswith("sha256:"))

    def test_invalid_kind_or_visibility_rejected(self):
        with self.assertRaises(ValueError):
            extract_facts([{"artifact_id": "x",
                            "statements": [{"kind": "vibe", "text": "t",
                                            "visibility": "public"}]}])
        with self.assertRaises(ValueError):
            extract_facts([{"artifact_id": "x",
                            "statements": [{"kind": "fact", "text": "t",
                                            "visibility": "secretish"}]}])


class Drafting(unittest.TestCase):
    def setUp(self):
        self.brief = capture_brief(BRIEF_RAW)
        self.facts = extract_facts(ARTIFACTS)
        self.draft = draft_communication(self.brief, self.facts)

    def test_grd01_grd04_structural(self):
        self.assertFalse(self.draft["sent"])
        self.assertTrue(self.draft["human_is_final_author_and_sender"])
        self.assertIn("cannot and will not send", self.draft["body"])
        import stakecomm.core as m
        for name in dir(m):
            for bad in ("send", "post_", "email", "publish", "deliver"):
                self.assertNotIn(bad, name.lower())

    def test_grd03_internal_facts_withheld_externally(self):
        self.assertNotIn("RCA doc", self.draft["body"])
        self.assertEqual(len(self.draft["excluded_facts"]), 1)
        self.assertIn("GRD-03", self.draft["excluded_facts"][0]["reason"])
        internal = draft_communication(
            capture_brief({**BRIEF_RAW, "recipient_scope": "internal",
                           "technical_fluency": "technical"}), self.facts)
        self.assertIn("RCA doc", internal["body"])
        self.assertEqual(internal["excluded_facts"], [])

    def test_depth_adaptation(self):
        # non-technical: jargon replaced by gloss
        self.assertIn("the 99th-percentile latency (p99)", self.draft["body"])
        self.assertIn("reverting to the previous version", self.draft["body"])
        semi = draft_communication(
            capture_brief({**BRIEF_RAW, "technical_fluency": "semi-technical"}),
            self.facts)
        self.assertIn("p99 (the 99th-percentile latency)", semi["body"])
        tech = draft_communication(
            capture_brief({**BRIEF_RAW, "technical_fluency": "technical"}),
            self.facts)
        self.assertIn("p99 latency rose to 2.1s", tech["body"])

    def test_cap04_nuance_preserved(self):
        for t in self.draft["fact_trace"]:
            self.assertTrue(t["nuance_preserved"], t)
        self.assertIn("2.1s", self.draft["body"])       # numbers survive
        self.assertIn("1.4.2", self.draft["body"])      # versions survive

    def test_formality_and_trace(self):
        self.assertTrue(self.draft["body"].startswith("Dear stakeholders,"))
        self.assertEqual(len(self.draft["fact_trace"]), 3)
        self.assertEqual(self.draft["open_risk_count"], 1)
        casual = draft_communication(
            capture_brief({**BRIEF_RAW, "formality": "casual"}), self.facts)
        self.assertTrue(casual["body"].startswith("Hey team,"))

    def test_deterministic(self):
        again = draft_communication(self.brief, self.facts)
        self.assertEqual(self.draft, again)


class Sensitivity(unittest.TestCase):
    def test_grd02_sensitive_gets_no_draft(self):
        brief = capture_brief({**BRIEF_RAW,
                               "intent": "announce the layoff decision"})
        d = draft_communication(brief, extract_facts(ARTIFACTS))
        self.assertEqual(d["status"], "HUMAN_ONLY")
        self.assertIsNone(d["body"])
        self.assertIn("layoff", d["markers"])

    def test_sensitive_fact_content_also_screens(self):
        facts = extract_facts([{"artifact_id": "a", "statements": [
            {"kind": "fact", "text": "the security breach affected 12 accounts",
             "visibility": "public"}]}])
        s = sensitivity_screen(capture_brief(BRIEF_RAW), facts)
        self.assertTrue(s["sensitive"])


if __name__ == "__main__":
    unittest.main()


class HardeningV011(unittest.TestCase):
    """New tests for 0.1.1-partial fixes (findings A013-F1..F4)."""

    def setUp(self):
        self.brief = capture_brief(BRIEF_RAW)
        self.facts = extract_facts(ARTIFACTS)

    # A013-F1: statement text validation
    def test_missing_text_raises_valueerror(self):
        with self.assertRaises(ValueError):
            extract_facts([{"artifact_id": "a", "statements": [
                {"kind": "fact", "visibility": "public"}]}])

    def test_non_string_text_raises_valueerror(self):
        with self.assertRaises(ValueError):
            extract_facts([{"artifact_id": "a", "statements": [
                {"kind": "fact", "text": 123, "visibility": "public"}]}])

    def test_valid_text_still_accepted(self):
        facts = extract_facts([{"artifact_id": "a", "statements": [
            {"kind": "fact", "text": "ok", "visibility": "public"}]}])
        self.assertEqual(facts[0]["text"], "ok")

    # A013-F2: aliasing/isolation
    def test_trace_provenance_isolated_from_input(self):
        d = draft_communication(self.brief, self.facts)
        d["fact_trace"][0]["provenance"]["artifact_id"] = "TAMPERED"
        self.assertEqual(self.facts[0]["provenance"]["artifact_id"],
                         "postmortem-42")

    def test_excluded_provenance_isolated_from_input(self):
        d = draft_communication(self.brief, self.facts)
        d["excluded_facts"][0]["fact_digest"] = "changed"
        self.assertNotEqual(self.facts[3]["fact_digest"], "changed")

    def test_capture_brief_isolates_nested_values(self):
        raw = dict(BRIEF_RAW, tags=["x"])
        b = capture_brief(raw)
        b["tags"].append("y")
        self.assertEqual(raw["tags"], ["x"])

    # A013-F3: strict canonicalization (NaN rejected)
    def test_nan_in_brief_rejected(self):
        with self.assertRaises(ValueError):
            capture_brief(dict(BRIEF_RAW, extra=float("nan")))

    def test_nan_in_statement_rejected(self):
        with self.assertRaises(ValueError):
            extract_facts([{"artifact_id": "a", "statements": [
                {"kind": "fact", "text": "t", "visibility": "public",
                 "metric": float("nan")}]}])

    # A013-F4: error contract — ValueError, not bare KeyError/TypeError/
    # AttributeError, for malformed inputs
    def test_uncaptured_brief_raises_valueerror(self):
        with self.assertRaises(ValueError):
            draft_communication(dict(BRIEF_RAW), [])

    def test_screen_missing_intent_raises_valueerror(self):
        with self.assertRaises(ValueError):
            sensitivity_screen({}, [])

    def test_non_string_brief_field_raises_valueerror(self):
        with self.assertRaises(ValueError):
            capture_brief(dict(BRIEF_RAW, intent=42))

    def test_non_dict_brief_raises_valueerror(self):
        with self.assertRaises(ValueError):
            capture_brief("hello")

    def test_statements_non_list_raises_valueerror(self):
        with self.assertRaises(ValueError):
            extract_facts([{"artifact_id": "a", "statements": "nope"}])

    def test_statement_non_dict_raises_valueerror(self):
        with self.assertRaises(ValueError):
            extract_facts([{"artifact_id": "a", "statements": ["nope"]}])

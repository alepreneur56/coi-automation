"""
zip_review.py
-------------
Unit tests for ziplookup.py and its integration into pipeline.decide_action.
All HTTP calls are mocked — no live network, no live Anthropic calls.

Covers:
  - unique-ZIP city -> lookup_zip_for_city returns "unique"
  - multi-ZIP city (e.g. Miami) -> returns "multiple", NEVER autofills
  - API failure (timeout / exception / non-200) -> degrades to "unknown",
    never raises
  - validate_city_state_zip: valid / mismatch / unknown
  - pipeline integration: coi_request_incomplete + missing-ZIP reply_text +
    ZIP_LOOKUP=True + unique hit -> reply_text rewritten, action stays
    "send_reply" (never send_pdf — see pipeline.py comment for why),
    'zip_autofilled' logged
  - pipeline integration: multi-ZIP city -> reply_text unchanged
  - pipeline integration: ZIP_LOOKUP=False (default) -> lookup never
    attempted, reply_text unchanged regardless of mock
  - not-quite-missing cases: no city/state present in reply_text -> no
    lookup attempted at all (e.g. "no holder name" template, generic
    incomplete text)

Usage:
    .venv/bin/python tests/zip_review.py
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import ziplookup
import pipeline


def _fake_response(status_code=200, json_data=None, raise_exc=None):
    resp = mock.Mock()
    resp.status_code = status_code
    if raise_exc:
        def _raise(*a, **kw):
            raise raise_exc
        resp.json = _raise
    else:
        resp.json = lambda: json_data or {}
    return resp


MIAMI_PLACES = [
    {"place name": "Miami", "post code": "33125", "state abbreviation": "FL"},
    {"place name": "Miami", "post code": "33126", "state abbreviation": "FL"},
    {"place name": "Miami", "post code": "33127", "state abbreviation": "FL"},
]

HOLLYWOOD_PLACES = [
    {"place name": "Hollywood", "post code": "33020", "state abbreviation": "FL"},
]


class ZipLookupUnitTests(unittest.TestCase):
    def setUp(self):
        ziplookup._cache.clear()

    def test_unique_zip_city(self):
        with mock.patch.object(
            ziplookup.requests, "get",
            return_value=_fake_response(200, {"places": HOLLYWOOD_PLACES}),
        ) as m:
            result = ziplookup.lookup_zip_for_city("Hollywood", "FL")
        self.assertEqual(result, {"status": "unique", "zip": "33020"})
        m.assert_called_once()

    def test_multi_zip_city_never_autofills(self):
        with mock.patch.object(
            ziplookup.requests, "get",
            return_value=_fake_response(200, {"places": MIAMI_PLACES}),
        ):
            result = ziplookup.lookup_zip_for_city("Miami", "FL")
        self.assertEqual(result["status"], "multiple")
        self.assertEqual(set(result["zips"]), {"33125", "33126", "33127"})

    def test_not_found_city(self):
        with mock.patch.object(
            ziplookup.requests, "get", return_value=_fake_response(404),
        ):
            result = ziplookup.lookup_zip_for_city("Nowhereville", "FL")
        self.assertEqual(result, {"status": "not_found"})

    def test_api_failure_timeout_degrades_to_unknown(self):
        with mock.patch.object(
            ziplookup.requests, "get",
            side_effect=ziplookup.requests.exceptions.Timeout("timed out"),
        ):
            result = ziplookup.lookup_zip_for_city("Hollywood", "FL")
        self.assertEqual(result, {"status": "unknown"})

    def test_api_failure_connection_error_degrades_to_unknown(self):
        with mock.patch.object(
            ziplookup.requests, "get",
            side_effect=ziplookup.requests.exceptions.ConnectionError("boom"),
        ):
            result = ziplookup.lookup_zip_for_city("Hollywood", "FL")
        self.assertEqual(result, {"status": "unknown"})

    def test_api_failure_bad_json_degrades_to_unknown(self):
        with mock.patch.object(
            ziplookup.requests, "get",
            return_value=_fake_response(200, raise_exc=ValueError("bad json")),
        ):
            result = ziplookup.lookup_zip_for_city("Hollywood", "FL")
        self.assertEqual(result, {"status": "unknown"})

    def test_missing_city_or_state_no_call_made(self):
        with mock.patch.object(ziplookup.requests, "get") as m:
            self.assertEqual(ziplookup.lookup_zip_for_city("", "FL"), {"status": "unknown"})
            self.assertEqual(ziplookup.lookup_zip_for_city("Miami", ""), {"status": "unknown"})
        m.assert_not_called()

    def test_result_is_cached_in_process(self):
        with mock.patch.object(
            ziplookup.requests, "get",
            return_value=_fake_response(200, {"places": HOLLYWOOD_PLACES}),
        ) as m:
            ziplookup.lookup_zip_for_city("Hollywood", "FL")
            ziplookup.lookup_zip_for_city("hollywood", "fl")  # case-insensitive cache hit
            ziplookup.lookup_zip_for_city("Hollywood", "FL")
        self.assertEqual(m.call_count, 1)

    def test_validate_valid(self):
        with mock.patch.object(
            ziplookup.requests, "get",
            return_value=_fake_response(200, {"places": HOLLYWOOD_PLACES}),
        ):
            self.assertEqual(
                ziplookup.validate_city_state_zip("Hollywood", "FL", "33020"), "valid"
            )

    def test_validate_mismatch(self):
        with mock.patch.object(
            ziplookup.requests, "get",
            return_value=_fake_response(200, {"places": HOLLYWOOD_PLACES}),
        ):
            self.assertEqual(
                ziplookup.validate_city_state_zip("Hollywood", "FL", "99999"), "mismatch"
            )

    def test_validate_unknown_on_failure(self):
        with mock.patch.object(
            ziplookup.requests, "get", side_effect=Exception("network down"),
        ):
            self.assertEqual(
                ziplookup.validate_city_state_zip("Hollywood", "FL", "33020"), "unknown"
            )

    def test_validate_zip_plus_four_tolerated(self):
        with mock.patch.object(
            ziplookup.requests, "get",
            return_value=_fake_response(200, {"places": HOLLYWOOD_PLACES}),
        ):
            self.assertEqual(
                ziplookup.validate_city_state_zip("Hollywood", "FL", "33020-1234"), "valid"
            )


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------

MISSING_ZIP_REPLY = (
    "Rolando,\n\nHappy to put this together for you. I just need the ZIP "
    "code for Bengoa Construction Inc at 2200 N Dixie Hwy, Hollywood, FL "
    "and I'll get the COI right out to you.\n\nRegards,"
)

MISSING_ZIP_REPLY_MIAMI = (
    "Rolando,\n\nHappy to put this together for you. I just need the ZIP "
    "code for ABC Condo Assoc at 1234 SW 54th St, Miami, FL and I'll get "
    "the COI right out to you.\n\nRegards,"
)

NO_HOLDER_NAME_REPLY = (
    "Rolando,\n\nHappy to help. Could you send over the certificate "
    "holder's name and address?\n\nRegards,"
)

NO_ADDRESS_REPLY = (
    "Rolando,\n\nHappy to put this together. Please send the certificate "
    "holder's full address so I can get started.\n\nRegards,"
)


def _ai_result(reply_text, classification="coi_request_incomplete"):
    return {
        "success": True,
        "sender": "client@example.com",
        "parsed": {
            "classification": classification,
            "reply_text": reply_text,
            "original_request_summary": "test",
        },
    }


class PipelineZipIntegrationTests(unittest.TestCase):
    def setUp(self):
        ziplookup._cache.clear()
        self._orig_flag = config.ZIP_LOOKUP

    def tearDown(self):
        config.ZIP_LOOKUP = self._orig_flag

    def test_flag_off_never_attempts_lookup(self):
        config.ZIP_LOOKUP = False
        with mock.patch.object(ziplookup, "lookup_zip_for_city") as m:
            decision = pipeline.decide_action(_ai_result(MISSING_ZIP_REPLY))
        m.assert_not_called()
        self.assertEqual(decision["action"], "send_reply")
        self.assertEqual(decision["reply_text"], MISSING_ZIP_REPLY)

    def test_flag_on_unique_zip_rewrites_reply_stays_send_reply(self):
        config.ZIP_LOOKUP = True
        with mock.patch.object(
            ziplookup, "lookup_zip_for_city",
            return_value={"status": "unique", "zip": "33020"},
        ):
            decision = pipeline.decide_action(_ai_result(MISSING_ZIP_REPLY))
        # Deliberately NOT send_pdf: the incomplete-request payload never
        # carries client_id/template_filename, so there is nothing safe to
        # build a PDF from. See pipeline._try_zip_autofill docstring.
        self.assertEqual(decision["action"], "send_reply")
        self.assertIn("33020", decision["reply_text"])
        self.assertNotEqual(decision["reply_text"], MISSING_ZIP_REPLY)

    def test_flag_on_multi_zip_city_leaves_reply_unchanged(self):
        config.ZIP_LOOKUP = True
        with mock.patch.object(
            ziplookup, "lookup_zip_for_city",
            return_value={"status": "multiple", "zips": ["33125", "33126"]},
        ):
            decision = pipeline.decide_action(_ai_result(MISSING_ZIP_REPLY_MIAMI))
        self.assertEqual(decision["action"], "send_reply")
        self.assertEqual(decision["reply_text"], MISSING_ZIP_REPLY_MIAMI)

    def test_flag_on_lookup_failure_leaves_reply_unchanged(self):
        config.ZIP_LOOKUP = True
        with mock.patch.object(
            ziplookup, "lookup_zip_for_city", side_effect=Exception("network down"),
        ):
            decision = pipeline.decide_action(_ai_result(MISSING_ZIP_REPLY))
        self.assertEqual(decision["action"], "send_reply")
        self.assertEqual(decision["reply_text"], MISSING_ZIP_REPLY)

    def test_flag_on_not_found_leaves_reply_unchanged(self):
        config.ZIP_LOOKUP = True
        with mock.patch.object(
            ziplookup, "lookup_zip_for_city",
            return_value={"status": "not_found"},
        ):
            decision = pipeline.decide_action(_ai_result(MISSING_ZIP_REPLY))
        self.assertEqual(decision["action"], "send_reply")
        self.assertEqual(decision["reply_text"], MISSING_ZIP_REPLY)

    def test_no_city_state_present_no_lookup_attempted(self):
        """Reply asking for holder name entirely (no city/state to look up
        at all) must never trigger a lookup call."""
        config.ZIP_LOOKUP = True
        with mock.patch.object(ziplookup, "lookup_zip_for_city") as m:
            decision = pipeline.decide_action(_ai_result(NO_HOLDER_NAME_REPLY))
        m.assert_not_called()
        self.assertEqual(decision["reply_text"], NO_HOLDER_NAME_REPLY)

    def test_no_address_at_all_no_lookup_attempted(self):
        config.ZIP_LOOKUP = True
        with mock.patch.object(ziplookup, "lookup_zip_for_city") as m:
            decision = pipeline.decide_action(_ai_result(NO_ADDRESS_REPLY))
        m.assert_not_called()
        self.assertEqual(decision["reply_text"], NO_ADDRESS_REPLY)

    def test_non_incomplete_classification_never_triggers_lookup(self):
        """Sanity: the 'question' classification also uses send_reply but
        must never run ZIP autofill logic."""
        config.ZIP_LOOKUP = True
        with mock.patch.object(ziplookup, "lookup_zip_for_city") as m:
            decision = pipeline.decide_action(
                _ai_result("Rolando,\n\nYour GL limit is $1M/$2M.\n\nRegards,", classification="question")
            )
        m.assert_not_called()
        self.assertEqual(decision["action"], "send_reply")

    def test_null_reply_text_no_lookup_attempted(self):
        """'client said they'll send info later' case: reply_text is None,
        must short-circuit before any lookup."""
        config.ZIP_LOOKUP = True
        with mock.patch.object(ziplookup, "lookup_zip_for_city") as m:
            decision = pipeline.decide_action(_ai_result(None))
        m.assert_not_called()
        self.assertEqual(decision["action"], "do_nothing")


if __name__ == "__main__":
    unittest.main(verbosity=2)

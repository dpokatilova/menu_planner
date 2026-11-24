import os
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from ai.client import AIError, call_ai_json

BOTH_KEYS = {"GEMINI_API_KEY": "g-key", "GROQ_API_KEY": "q-key"}
GEMINI_ONLY = {"GEMINI_API_KEY": "g-key"}
GROQ_ONLY = {"GROQ_API_KEY": "q-key"}
SECRET = "secret information"


def fake_response(status=200, body=None):
    response = Mock()
    response.status_code = status
    response.json.return_value = body
    return response


def gemini_body(text='{"ok": true}'):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def groq_body(text='{"ok": true}'):
    return {"choices": [{"message": {"content": text}}]}


@patch("ai.client.requests.post")
class CallAiJsonTests(SimpleTestCase):
    @patch.dict(os.environ, BOTH_KEYS, clear=True)
    def test_gemini_success(self, post):
        post.return_value = fake_response(body=gemini_body('{"a": 1}'))

        result = call_ai_json("system", "user")

        self.assertEqual(result, {"a": 1})
        self.assertEqual(post.call_count, 1)

    @patch.dict(os.environ, BOTH_KEYS, clear=True)
    def test_timeout_is_passed_to_requests(self, post):
        post.return_value = fake_response(body=gemini_body())

        call_ai_json("system", "user", timeout=7)

        self.assertEqual(post.call_args.kwargs["timeout"], 7)

    @patch.dict(os.environ, {**BOTH_KEYS, "AI_TIMEOUT": "9"}, clear=True)
    def test_default_timeout_comes_from_env(self, post):
        post.return_value = fake_response(body=gemini_body())

        call_ai_json("system", "user")

        self.assertEqual(post.call_args.kwargs["timeout"], 9)

    @patch.dict(os.environ, BOTH_KEYS, clear=True)
    def test_falls_back_to_groq_on_timeout(self, post):
        post.side_effect = [requests.Timeout(), fake_response(body=groq_body('{"b": 2}'))]

        result = call_ai_json("system", "user")

        self.assertEqual(result, {"b": 2})
        self.assertEqual(post.call_count, 2)

    @patch.dict(os.environ, BOTH_KEYS, clear=True)
    def test_falls_back_to_groq_on_http_error(self, post):
        post.side_effect = [fake_response(status=429), fake_response(body=groq_body())]

        self.assertEqual(call_ai_json("system", "user"), {"ok": True})

    @patch.dict(os.environ, BOTH_KEYS, clear=True)
    def test_falls_back_to_groq_on_invalid_json(self, post):
        post.side_effect = [
            fake_response(body=gemini_body("не json")),
            fake_response(body=groq_body()),
        ]

        self.assertEqual(call_ai_json("system", "user"), {"ok": True})

    @patch.dict(os.environ, BOTH_KEYS, clear=True)
    def test_raises_when_both_providers_fail(self, post):
        post.side_effect = [requests.Timeout(), fake_response(status=500)]

        with self.assertRaises(AIError):
            call_ai_json("system", "user")

        self.assertEqual(post.call_count, 2)

    @patch.dict(os.environ, GROQ_ONLY, clear=True)
    def test_works_with_only_groq_configured(self, post):
        post.return_value = fake_response(body=groq_body())

        self.assertEqual(call_ai_json("system", "user"), {"ok": True})
        self.assertEqual(post.call_count, 1)

    @patch.dict(os.environ, {}, clear=True)
    def test_no_keys_raises_without_requests(self, post):
        with self.assertRaises(AIError):
            call_ai_json("system", "user")

        post.assert_not_called()

    @patch.dict(os.environ, GEMINI_ONLY, clear=True)
    def test_network_error_becomes_ai_error(self, post):
        post.side_effect = requests.ConnectionError("boom")

        with self.assertRaises(AIError):
            call_ai_json("system", "user")

    @patch.dict(os.environ, GEMINI_ONLY, clear=True)
    def test_response_body_not_json_raises(self, post):
        response = fake_response()
        response.json.side_effect = ValueError
        post.return_value = response

        with self.assertRaises(AIError):
            call_ai_json("system", "user")

    @patch.dict(os.environ, GEMINI_ONLY, clear=True)
    def test_unexpected_response_structure_raises(self, post):
        post.return_value = fake_response(body={"candidates": []})

        with self.assertRaises(AIError):
            call_ai_json("system", "user")

    @patch.dict(os.environ, GEMINI_ONLY, clear=True)
    def test_json_array_instead_of_object_raises(self, post):
        post.return_value = fake_response(body=gemini_body("[1, 2, 3]"))

        with self.assertRaises(AIError):
            call_ai_json("system", "user")

    @patch.dict(os.environ, GEMINI_ONLY, clear=True)
    def test_markdown_fences_are_stripped(self, post):
        post.return_value = fake_response(body=gemini_body('```json\n{"a": 1}\n```'))

        self.assertEqual(call_ai_json("system", "user"), {"a": 1})

    @patch.dict(os.environ, GEMINI_ONLY, clear=True)
    def test_prompt_text_is_not_logged(self, post):
        post.side_effect = requests.ConnectionError(SECRET)

        with self.assertLogs("ai.client", level="WARNING") as logs:
            with self.assertRaises(AIError) as error:
                call_ai_json("system", SECRET)

        self.assertNotIn(SECRET, "\n".join(logs.output))
        self.assertNotIn(SECRET, str(error.exception.__cause__))

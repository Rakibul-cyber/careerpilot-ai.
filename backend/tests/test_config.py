import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings


class SettingsTests(unittest.TestCase):
    def test_missing_secret_key_fails_fast(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None)

    def test_debug_false_is_default_and_ai_keys_are_optional(self):
        settings = Settings(_env_file=None, SECRET_KEY="dev-secret")

        self.assertFalse(settings.DEBUG)
        self.assertIsNone(settings.ANTHROPIC_API_KEY)
        self.assertIsNone(settings.OPENAI_API_KEY)

    def test_testing_environment_is_valid(self):
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="testing",
            DEBUG=False,
            SECRET_KEY="dev-secret",
        )

        self.assertEqual(settings.ENVIRONMENT, "testing")

    def test_comma_separated_cors_values_parse_to_lists(self):
        settings = Settings(
            _env_file=None,
            SECRET_KEY="dev-secret",
            CORS_ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173",
            CORS_ALLOWED_METHODS="GET,POST",
            CORS_ALLOWED_HEADERS="Authorization,Content-Type",
        )

        self.assertEqual(
            settings.CORS_ALLOWED_ORIGINS,
            ["http://localhost:3000", "http://localhost:5173"],
        )
        self.assertEqual(settings.CORS_ALLOWED_METHODS, ["GET", "POST"])
        self.assertEqual(
            settings.CORS_ALLOWED_HEADERS,
            ["Authorization", "Content-Type"],
        )

    def test_env_cors_values_parse_to_lists(self):
        with patch.dict(
            os.environ,
            {
                "SECRET_KEY": "dev-secret",
                "DEBUG": "false",
                "CORS_ALLOWED_ORIGINS": ("http://localhost:3000,http://localhost:5173"),
            },
            clear=True,
        ):
            settings = Settings(_env_file=None)

        self.assertEqual(
            settings.CORS_ALLOWED_ORIGINS,
            ["http://localhost:3000", "http://localhost:5173"],
        )

    def test_production_rejects_debug_true(self):
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                DEBUG=True,
                SECRET_KEY="x" * 40,
            )

    def test_production_rejects_wildcard_cors(self):
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                SECRET_KEY="x" * 40,
                CORS_ALLOWED_ORIGINS=["*"],
            )

    def test_production_rejects_placeholder_secret(self):
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                SECRET_KEY="change-this-secret-key-in-production",
            )

    def test_production_valid_env_loads(self):
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="x" * 40,
            CORS_ALLOWED_ORIGINS=["https://app.careerpilot.example"],
        )

        self.assertTrue(settings.is_production)
        self.assertFalse(settings.DEBUG)


if __name__ == "__main__":
    unittest.main()

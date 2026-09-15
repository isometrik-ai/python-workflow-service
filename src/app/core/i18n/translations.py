"""Translation loader and lookup for localized API messages."""

import json
from pathlib import Path
from typing import Any


class Translator:
    """Handles translation of messages based on language code."""

    def __init__(self, default_language: str = "en"):
        """Load locale files and set the fallback language."""
        self.default_language = default_language
        self.translations: dict[str, dict[str, Any]] = {}
        self._load_translations()

    def _load_translations(self) -> None:
        """Load all translation files from the locales directory."""
        locales_dir = Path(__file__).parent / "locales"

        for file_path in locales_dir.glob("*.json"):
            language_code = file_path.stem
            try:
                with open(file_path, encoding="utf-8") as f:
                    self.translations[language_code] = json.load(f)
            except Exception:
                pass

    def get(self, key: str, language: str | None = None, **params) -> str:
        """Get a translated string for the given key and language.

        Args:
        ----
            key: The translation key (can be dot-separated for nested access)
            language: The language code
            **params: Parameters to format into the translated string

        Returns:
        -------
            The translated string or the key itself if not found

        """
        language = language or self.default_language

        # Fall back to default language if requested language not available
        if language not in self.translations:
            language = self.default_language

        # Navigate nested keys (e.g., "errors.not_found")
        value = self.translations.get(language, {})
        parts = key.split(".")

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                # Key not found, return the original key
                return key

        # If we got a string, format it with the provided parameters
        if isinstance(value, str):
            try:
                return value.format(**params)
            except KeyError:
                # If formatting fails, return the unformatted string
                return value

        # If the value is not a string, return the key
        return key


# Create a global translator instance
translator = Translator()

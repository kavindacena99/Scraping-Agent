from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from research.agent.prompts import get_prompt
from research.agent.prompts.loader import PromptTemplateError, load_prompt
from research.agent.providers.embedding_factory import get_embedding_model
from research.agent.providers.llm_factory import get_llm
from research.config import ProviderSettings
from research.exceptions import ProviderConfigurationError


class PromptTests(TestCase):
    def test_all_registered_prompts_load_and_render(self):
        prompt = get_prompt("intent_analysis")
        rendered = prompt.render(website_url="https://example.com", user_query="Find products")
        self.assertEqual(rendered[0][0], "system")
        self.assertIn("Find products", rendered[1][1])

    def test_missing_template_variable_has_clear_error(self):
        with self.assertRaisesRegex(PromptTemplateError, "user_query"):
            get_prompt("intent_analysis").render(website_url="https://example.com")

    def test_missing_prompt_is_rejected(self):
        with self.assertRaisesRegex(PromptTemplateError, "Unknown prompt"):
            get_prompt("does_not_exist")

    def test_invalid_template_fields_are_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.yaml"
            path.write_text("name: bad\nversion: '1'", encoding="utf-8")
            with self.assertRaises(PromptTemplateError):
                load_prompt(path)


class ProviderFactoryTests(TestCase):
    def test_selected_llm_requires_only_its_own_key(self):
        config = ProviderSettings("openai", "test-model", {"openai": "", "gemini": "unused"})
        with self.assertRaisesRegex(ProviderConfigurationError, "openai"):
            get_llm(config)

    def test_selected_embedding_provider_requires_key(self):
        config = ProviderSettings("gemini", "test-model", {"openai": "unused", "gemini": ""})
        with self.assertRaisesRegex(ProviderConfigurationError, "gemini"):
            get_embedding_model(config)

    def test_unknown_provider_fails_clearly(self):
        config = ProviderSettings("unknown", "test-model", {"unknown": "key"})
        with self.assertRaisesRegex(ProviderConfigurationError, "Unsupported LLM"):
            get_llm(config)


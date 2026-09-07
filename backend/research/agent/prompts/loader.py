from __future__ import annotations

import string
from dataclasses import dataclass
from pathlib import Path

import yaml


class PromptTemplateError(ValueError):
    pass


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    version: str
    description: str
    system_template: str
    user_template: str

    def variables(self) -> set[str]:
        formatter = string.Formatter()
        values: set[str] = set()
        for template in (self.system_template, self.user_template):
            for _, field_name, _, _ in formatter.parse(template):
                if field_name:
                    values.add(field_name)
        return values

    def render(self, **variables: object) -> list[tuple[str, str]]:
        missing = self.variables() - variables.keys()
        if missing:
            names = ", ".join(sorted(missing))
            raise PromptTemplateError(f"Prompt '{self.name}' is missing template variables: {names}.")
        try:
            return [
                ("system", self.system_template.format_map(variables)),
                ("human", self.user_template.format_map(variables)),
            ]
        except (KeyError, ValueError) as exc:
            raise PromptTemplateError(f"Prompt '{self.name}' could not be rendered: {exc}") from exc


def load_prompt(path: Path) -> PromptTemplate:
    if not path.exists():
        raise PromptTemplateError(f"Prompt template was not found: {path.name}.")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PromptTemplateError(f"Prompt template could not be loaded: {path.name}.") from exc
    required = {"name", "version", "description", "system_template", "user_template"}
    if not isinstance(payload, dict) or not required.issubset(payload):
        missing = required - set(payload or {})
        raise PromptTemplateError(f"Prompt template '{path.name}' is missing fields: {', '.join(sorted(missing))}.")
    return PromptTemplate(**{key: str(payload[key]) for key in required})


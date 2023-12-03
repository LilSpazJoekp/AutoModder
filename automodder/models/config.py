"""Provide the Config class."""
import json
from pathlib import Path
from typing import TypeVar

import click
from pydantic import BaseModel, Field

T = TypeVar("T")


def prompt_fields(model: type[BaseModel]) -> dict:
    """Prompt the user for the fields of a model.

    :param model: The model to prompt for.

    :returns: A dictionary of the fields and their values.

    """
    data = {}
    for field_name, field in model.model_fields.items():
        if issubclass(field.annotation, BaseModel):
            data[field_name] = field.annotation(**prompt_fields(field.annotation))
        elif field_name == "min_age":
            data[field_name] = (
                click.prompt("Enter the minimum item age in hours", type=int) * 3600
            )
        else:
            data[field_name] = click.prompt(f"Enter the {field_name}")
    return data


class Config(BaseModel):
    """A configuration class for AutoModder.

    :ivar min_age int: The minimum age of a post to be considered by the bot.
    :ivar min_score int: The minimum score of a post to be considered by the bot.
    :ivar min_subscriber_count int: The minimum subscriber count of a subreddit for the
        bot to consider.
    :ivar username str: The username for the bot.

    """

    min_age: int = Field(
        description="The minimum age of a post to be considered by the bot.",
        unit="hours",
        from_user=lambda x: x * 3600,
        from_config=lambda x: x // 3600,
    )
    min_score: int = Field(
        description="The minimum score of a post to be considered by the bot."
    )
    min_subscriber_count: int = Field(
        description="The minimum subscriber count of a subreddit for the bot to consider.",
        test_extra=True,
    )
    username: str = Field(description="The default username.")

    @staticmethod
    def get_field_attr(field: Field, attr: str, default: T = None) -> T:
        """Return the extra value for the field."""
        if hasattr(field, attr):
            return getattr(field, attr)
        if field.json_schema_extra:
            return field.json_schema_extra.get(attr, default)
        return default

    @classmethod
    def load(cls, path: Path) -> "Config":
        """Load a configuration from a JSON file, or creates one if it doesn't exist.

        :param path: The file path to load the configuration from.

        :returns: An instance of the Config class with the loaded options.

        """
        if not path.exists():
            temp = cls(**prompt_fields(cls))
            temp.save(path)
            return temp
        if path.exists():
            with path.open() as json_file:
                data = json.load(json_file)
            return cls.model_validate(data)
        return None

    def save(self, path: Path):
        """Save the current configuration to a JSON file.

        :param path: The path to the file where the configuration should be saved.

        """
        with path.open("w") as json_file:
            json.dump(self.model_dump(), json_file, indent=4)

    def to_cli_description(self, field_name: str) -> str:
        """Return a description of the field for the CLI."""
        field = self.model_fields.get(field_name)
        description = field.description
        unit = self.get_field_attr(field, "unit")
        if unit:
            description = description.strip(".")
            description += f". (in {unit})."
        return description

    def to_prompt(self, field_name: str) -> str:
        """Return a prompt for the field."""
        field = self.model_fields.get(field_name)
        prompt = f"Enter the {field_name}"
        unit = self.get_field_attr(field, "unit")
        if unit:
            prompt += f" (in {unit})."
        if field.description:
            prompt = prompt.strip(".")
            prompt += f". {field.description}"
        return prompt

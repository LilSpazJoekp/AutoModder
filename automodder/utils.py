"""Provide utility functions for AutoModder."""
from datetime import UTC, datetime
from typing import TypeVar

import click
from dateutil.relativedelta import relativedelta

T: TypeVar = TypeVar("T")


def help_from_config(param_name: str) -> str | None:
    """Return a help message from the specified config model field."""
    from . import config

    return config.to_cli_description(param_name)


def human_timedelta(
    epoch_timestamp: int,
    *,
    accuracy: int | None = 5,
    suffix: bool = True,
) -> str:
    """Humanize a timedelta.

    :param epoch_timestamp: The timestamp to humanize.
    :param accuracy: The number of units to include in the output.
    :param suffix: Whether to include the suffix.

    :returns: A humanized timedelta.

    """
    now = datetime.now(UTC)
    dt = datetime.fromtimestamp(epoch_timestamp, UTC)

    # Microsecond free zone
    now = now.replace(microsecond=0)
    dt = dt.replace(microsecond=0)

    # This implementation uses relativedelta instead of the much more obvious
    # divmod approach with seconds because the seconds approach is not entirely
    # accurate once you go over 1 week in terms of accuracy since you have to
    # hardcode a month as 30 or 31 days.
    # A query like "11 months" can be interpreted as "11 months and 6 days"
    output_suffix = ""
    if dt > now:
        delta = relativedelta(dt, now)
    else:
        delta = relativedelta(now, dt)
        if suffix:
            output_suffix = " ago"

    attrs = [
        ("year", "y"),
        ("month", "mo"),
        ("day", "d"),
        ("hour", "h"),
        ("minute", "m"),
        ("second", "s"),
    ]

    output = []
    for attr, brief_attr in attrs:
        elem = getattr(delta, attr + "s")
        if not elem:
            continue

        if attr == "day":
            weeks = delta.weeks
            if weeks:
                elem -= weeks * 7
                output.append(f"{weeks}w")

        if elem <= 0:
            continue

        output.append(f"{elem}{brief_attr}")

    if accuracy is not None:
        output = output[:accuracy]

    if len(output) == 0:
        return "now"
    return " ".join(output) + output_suffix


class plural:  # noqa: N801
    """A class to format a number with a singular or plural form."""

    def __format__(self, format_spec: str) -> str:
        """Format the number with a singular or plural form.

        :param format_spec: The format specifier.

        :returns: The formatted number.

        """
        v = self.value
        singular_form, _, plural_form = format_spec.partition("|")
        plural_form = plural_form or f"{singular_form}s"
        if abs(v) != 1:
            return f"{v} {plural_form}"
        return f"{v} {singular_form}"

    def __init__(self, value: int):
        """Initialize the class with a number.

        :param value: The number to format.

        """
        self.value: int = value


def prompt_then_fallback_to_config(
    context: click.Context,  # noqa: ARG001
    param: click.Parameter,
    value: T | None,
) -> T | None:
    """Return a callback that falls back to the config file.

    :param context: The click context.
    :param param: The click parameter.
    :param value: The value the user provided.

    """
    from . import config

    field = config.model_fields.get(param.name)
    from_user = config.get_field_attr(field, "from_user", lambda val: val)
    if value:
        return from_user(value)
    from_config = config.get_field_attr(field, "from_config", lambda val: val)
    value = click.prompt(
        config.to_prompt(param.name), default=from_config(getattr(config, param.name))
    )
    return from_user(value)

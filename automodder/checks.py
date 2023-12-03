"""Provide check functions for AutoModder."""
import time
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from typing import Generic, TypeVar

import click
from praw.models import Comment, ModmailConversation, Submission

from .utils import human_timedelta

T = TypeVar("T")


class ActionQualifier(Enum):
    """Enumeration of action qualifiers."""

    ANY = "any"
    ALL = "all"


class Check(Generic[T]):
    """A check function.

    This is a generic class that represents a check function. It can be used to create
    check functions for different types of items.

    """

    def __call__(self, item: T) -> tuple[bool, str]:
        """Call the check function.

        :param item: The item to check.

        :returns: A tuple containing a boolean indicating whether the item passed the
            check, and a message explaining the result if the first item is `True`.

        """
        return self.func(item)

    def __init__(
        self,
        func: Callable[[T], tuple[bool, str]],
        qualifier: ActionQualifier = ActionQualifier.ALL,
    ) -> None:
        """Initialize a new check function.

        :param func: The function to use for the check.
        :param qualifier: The qualifier to use for the check. This can be either
            `ActionQualifier.ANY` or `ActionQualifier.ALL`. If `ActionQualifier.ANY` is
            used, the check will override other checks. If `ActionQualifier.ALL` is
            used, the check will pass if all the other checks pass.

        """
        self.func = func
        self.qualifier = qualifier

    def __repr__(self) -> str:
        """Return a string representation of the check function."""
        return f"Check({getattr(self.func, '__check_name__', self.func.__name__)}, {self.qualifier})"


def check_age(min_age: int) -> Check[Comment | Submission]:
    """Check the age of an item against a minimum age.

    :param min_age: The minimum age, in seconds, that an item should be in order to pass
        the age check.

    :returns: A function that returns a tuple containing a boolean indicating whether
        the item's age is greater than or equal to the minimum age, and a message
        indicating the age comparison result.

    """

    def check(item: Comment | Submission) -> tuple[bool, str]:
        """Check the age of an item against a minimum age.

        :param item: The item to check the age for. This can be a `Comment` or
            `Submission` object.

        :returns: A tuple containing a boolean value (`True` if the age is greater than
            or equal to the minimum age, `False` otherwise) and a message explaining the
            result if the first item is `True`.

        """
        result = datetime.now(tz=UTC).timestamp() - item.created_utc >= min_age
        message = ""
        if result:
            message = f"{click.style(human_timedelta(item.created_utc, suffix=False), fg='red')} {click.style('>=', fg='yellow')} {click.style(human_timedelta(int(time.time() - min_age), suffix=False), fg='cyan')}"
        return result, message

    check.__check_name__ = "check_age"

    return Check(check)


def check_pending_response(ignore_pending_response: bool) -> Check[ModmailConversation]:
    """Check whether a modmail conversation might need a mod response.

    :param ignore_pending_response: Whether to ignore conversations that might need a
        mod response.

    :returns: A function that returns a tuple containing a boolean indicating whether
        the conversation needs a mod response, and a message indicating the result.

    """

    def check(item: ModmailConversation) -> tuple[bool, str]:
        """Check whether a modmail conversation might need a mod response.

        :param item: The conversation to check.

        :returns: A tuple containing a boolean value (`True` if the conversation is
            unanswered, `False` otherwise) and a message explaining the result if the
            first item is `True`.

        """
        message = ""
        if ignore_pending_response or item.last_user_update is None:
            return False, message
        result = datetime.fromisoformat(item.last_mod_update) < datetime.fromisoformat(
            item.last_user_update
        )
        if result:
            message = click.style("needs mod response", fg="red")
        return result, message

    check.__check_name__ = "check_pending_response"

    return Check(check)


def check_removed_by_automated_spam() -> Check[Comment | Submission]:
    """Check whether an item has been removed by the automated spam filter."""

    def check(item: Comment | Submission) -> tuple[bool, str]:
        """Check the score of an item against a minimum score..

        :param item: The item to check the score for. This can be a `Comment` or
            `Submission` object.

        :returns: A tuple containing a boolean value (`True` if the score is below the
            minimum, `False` otherwise) and a message explaining the result if the first
            item is `True`.

        """
        results = []
        results.append(getattr(item, "removed_by_category", None) == "reddit")
        if item.banned_by is True:
            results.append(item.ban_note == "spam")
        message = ""
        result = any(results)
        if result:
            message = f"{click.style('automated system marked it as spam', fg='red')}"
        return result, message

    check.__check_name__ = "check_removed_by_automated_spam"

    return Check(check, ActionQualifier.ANY)


def check_score(min_score: int) -> Check[Comment | Submission]:
    """Check the score of an item against a minimum score.

    :param min_score: The minimum score that an item should have in order to pass the
        score check.

    :returns: A function that returns a tuple containing a boolean indicating whether
        the item's score is less than the minimum score, and a message indicating the
        score comparison result.

    """

    def check(item: Comment | Submission) -> tuple[bool, str]:
        """Check the score of an item against a minimum score..

        :param item: The item to check the score for. This can be a `Comment` or
            `Submission` object.

        :returns: A tuple containing a boolean value (`True` if the score is below the
            minimum, `False` otherwise) and a message explaining the result if the first
            item is `True`.

        """
        result = item.score < min_score
        message = ""
        if result:
            message = f"{click.style(str(item.score), fg='red')} {click.style('<', fg='yellow')} {click.style(str(min_score), fg='cyan')}"
        return result, message

    check.__check_name__ = "check_score"

    return Check(check)


def check_unanswered(ignore_unanswered: bool) -> Check[ModmailConversation]:
    """Check whether a modmail conversation has been answered.

    :param ignore_unanswered: Whether to ignore unanswered conversations.

    :returns: A function that returns a tuple containing a boolean indicating whether
        the conversation has been answered, and a message indicating the result.

    """

    def check(item: ModmailConversation) -> tuple[bool, str]:
        """Check whether a modmail conversation has been answered.

        :param item: The conversation to check.

        :returns: A tuple containing a boolean value (`True` if the conversation is
            unanswered, `False` otherwise) and a message explaining the result if the
            first item is `True`.

        """
        message = ""
        if ignore_unanswered:
            return False, message
        result = item.last_mod_update is None
        if result:
            message = click.style("unanswered", fg="red")
        return result, message

    check.__check_name__ = "check_unanswered"

    return Check(check)

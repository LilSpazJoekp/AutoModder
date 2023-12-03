"""Provides the SubredditBucket class."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from praw.models import Redditor, Subreddit


class SubredditBucket:
    """Manages groups subreddits together."""

    def __call__(self, sub: Subreddit, mods: Iterable[Redditor]):
        """Add a subreddit and its mods to the bucket.

        :param sub: The subreddit to add.
        :param mods: The mods of the subreddit to add.

        """
        self.bucket.append((sub, mods))

    def __init__(self, pretty_name: str):
        """Initialize a new SubredditBucket.

        :param pretty_name: The pretty name of the bucket.

        """
        self.name = pretty_name
        self.bucket = []

    def __iter__(self):  # noqa: ANN204
        """Return an iterator for the bucket."""
        return iter(self.bucket)

    def __len__(self) -> int:
        """Return the number of items in the bucket."""
        return len(self.bucket)

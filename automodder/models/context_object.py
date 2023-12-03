"""Provide the InvokeContext class."""
from dataclasses import dataclass
from functools import cached_property

from praw import Reddit
from praw.models import Subreddit

from . import Config


class LazySubreddits:
    """A lazy list of subreddit objects.

    This class is used to delay the creation of subreddit objects until they are
    actually needed.

    """

    def __getitem__(self, index: int) -> Subreddit:
        """Get a subreddit object from the list.

        :param index: The index of the subreddit to get.

        :returns: The subreddit object.

        """
        return self.subreddits[index]

    def __init__(
        self,
        *,
        min_subscriber_count: int,
        reddit: Reddit,
        subreddits: list[str],
    ) -> None:
        """Initialize a new LazySubreddits object.

        :param reddit: The Reddit instance to use.
        :param min_subscriber_count: The minimum subscriber count for a subreddit to be
            considered. This is only used if `subreddits` is empty.
        :param subreddits: The list of subreddit names to use. If this is empty,
            subreddits will be fetched from authenticated user's moderated subreddits
            and filtered by the minimum subscriber count.

        """
        self.reddit = reddit
        self.min_subscriber_count = min_subscriber_count
        self._subreddits = subreddits

    def __len__(self) -> int:
        """Get the length of the list.

        :returns: The length of the list.

        """
        return len(self.subreddits)

    def __repr__(self) -> str:
        """Return a string representation of the list.

        :returns: The string representation of the list.

        """
        return f"LazySubreddits({self.subreddits})"

    @cached_property
    def subreddits(self) -> list[Subreddit]:
        """Get the list of subreddit objects.

        :returns: The list of subreddit objects.

        """
        return [self.reddit.subreddit(subreddit) for subreddit in self._subreddits] or [
            subreddit
            for subreddit in self.reddit.user.me().moderated()
            if subreddit.subscribers >= self.min_subscriber_count
        ]


@dataclass
class InvokeContext:
    """Represents a context object that holds configuration, Reddit instance, and subreddit information.

    :ivar config Config: The configuration object.
    :ivar dry_run bool: Whether to perform a dry run.
    :ivar reddit praw.Reddit: The Reddit instance.
    :ivar subreddits LazySubreddit: A lazy list of subreddit objects.

    """

    config: Config
    dry_run: bool
    reddit: Reddit
    subreddits: LazySubreddits

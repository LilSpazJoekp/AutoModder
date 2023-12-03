"""Collect information about subreddits' moderator activity statuses."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from praw.models import ListingGenerator, Redditor

from ..logger import PrefixLogger
from ..models import BaseWriter, ConsoleWriter, SubredditBucket

if TYPE_CHECKING:
    from collections.abc import Iterable

    import praw

    from ..models.context_object import LazySubreddits

log = logging.getLogger(__name__)

Item = Redditor


class InactivityManager:
    """Class assessing your activity status."""

    all_subreddits = SubredditBucket("All Subreddits")  # All subs
    inactive = SubredditBucket("Inactive")  # Subs where I'm inactive
    active_top_mod = SubredditBucket(
        "Top Mod and Active"
    )  # Subs where I'm the active top mod
    top_active_mod = SubredditBucket(
        "Highest Active Mod"
    )  # Subs where I'm the top active mod
    no_active_mods = SubredditBucket(
        "Subreddits Where Nobody Is Active"
    )  # Subs with no active mods
    inactive_top_mod = SubredditBucket(
        "Inactive and Top Mod"
    )  # Subs where I'm inactive and I'm the top mod
    inactive_top_2 = SubredditBucket(
        "Inactive and In The Top 2"
    )  # Subs where I'm inactive and I'm in the top 2
    inactive_top_3 = SubredditBucket(
        "Inactive and In The Top 3"
    )  # Subs where I'm inactive and I'm in the top 3
    inactive_top_5 = SubredditBucket(
        "Inactive and In The Top 5"
    )  # Subs where I'm inactive and I'm in the top 5
    inactive_top_10 = SubredditBucket(
        "Inactive and In The Top 10"
    )  # Subs where I'm inactive and I'm in the top 10
    active_inactive_above = SubredditBucket(
        "Active with Inactive Above"
    )  # Subs where I'm active and there are inactive mods above me
    inactive_active_below = SubredditBucket(
        "Inactive with Active Below"
    )  # Subs where I'm inactive and there are active mods below me
    only_one_active = SubredditBucket(
        "Only One Active"
    )  # Subs where I'm inactive and there are active mods below me

    lists = [
        all_subreddits,
        inactive,
        active_top_mod,
        only_one_active,
        no_active_mods,
        inactive_top_mod,
        inactive_top_2,
        inactive_top_3,
        inactive_top_5,
        inactive_top_10,
        active_inactive_above,
        inactive_active_below,
    ]

    @staticmethod
    def contain_active(moderators: Iterable[Redditor]) -> bool:
        """Check if any of the moderators are active.

        :param moderators: The moderators to check.

        :returns: True if any moderators are active, False otherwise.

        """
        return any(mod.is_active for mod in moderators)

    @staticmethod
    def contain_all_inactive(moderators: Iterable[Redditor]) -> bool:
        """Check if all of the moderators are inactive.

        :param moderators: The moderators to check.

        :returns: True if all moderators are inactive, False otherwise.

        """
        return all(not mod.is_active for mod in moderators)

    @staticmethod
    def contain_inactive(moderators: Iterable[Redditor]) -> bool:
        """Check if any of the moderators are inactive.

        :param moderators: The moderators to check.

        :returns: True if any moderators are inactive, False otherwise.

        """
        return any(not mod.is_active for mod in moderators)

    def __init__(
            self,
            subreddits: LazySubreddits,
            reddit: praw.Reddit,
            redditor: Redditor | None = None,
            writer: type[BaseWriter] = ConsoleWriter,
    ):
        """Initialize a new InactivityChecker instance.

        :param subreddits: The subreddits to scan.
        :param reddit: The Reddit instance to use.
        :param redditor: The Redditor to use.
        :param writer: The writer to use.

        """
        self.me = redditor or reddit.user.me()
        self.log: PrefixLogger[Item] = PrefixLogger(log, self._log_prefix)
        self.reddit = reddit
        self.subreddits = subreddits
        self._current_subreddit = None
        self._writer = writer

    def _log_prefix(self, item: Redditor) -> str:
        """Generate a log prefix for an item.

        :param item: The item to generate the prefix for.

        :returns: The generated prefix as a string.

        """
        return f"Inactivity Checker | r/{self._current_subreddit.display_name:<21} | u/{item} | is_active: {item.is_active}"

    def print_results(self):
        """Print the results of the scan."""
        self._writer(self.lists, self.me).write()

    def scan(self):  # noqa: PLR0912
        """Scan the mod list of each subreddit."""
        for subreddit in self.subreddits:
            self._current_subreddit = subreddit
            entire_sub_inactive = True
            above_me = []
            below_me = []
            my_position = None
            im_active = False
            generator = ListingGenerator(
                self.reddit, url=f"api/v1/{subreddit}/moderators", limit=None
            )
            try:
                for position, moderator in enumerate(generator, 1):
                    entire_sub_inactive &= not moderator.is_active
                    moderator.position = position

                    # check my status
                    if moderator.name == self.me.name:
                        self.log.info("", moderator)
                        my_position = position
                        im_active = moderator.is_active
                        subreddit.position = my_position
                        subreddit.is_active = im_active
                    # handle mods above and below me
                    if my_position is None:
                        above_me.append(moderator)
                    else:
                        below_me.append(moderator)
            except Exception:  # noqa: BLE001
                self.log.warning(f"Error getting moderators for r/{subreddit}", None)
                continue

            self.all_subreddits(subreddit, [])

            if entire_sub_inactive:
                self.no_active_mods(subreddit, [])

            match my_position, im_active:
                case 1, True:
                    self.active_top_mod(subreddit, [])
                case 1, False:
                    self.inactive_top_mod(
                        subreddit, filter(lambda mod: not mod.is_active, above_me)
                    )
                case 2, False:
                    self.inactive_top_2(
                        subreddit, filter(lambda mod: not mod.is_active, above_me)
                    )
                case 3, False:
                    self.inactive_top_3(
                        subreddit, filter(lambda mod: not mod.is_active, above_me)
                    )
                case (4, False) | (5, False):
                    self.inactive_top_5(
                        subreddit, filter(lambda mod: not mod.is_active, above_me)
                    )
                case (6, False) | (7, False) | (8, False) | (9, False) | (10, False):
                    self.inactive_top_10(
                        subreddit, filter(lambda mod: not mod.is_active, above_me)
                    )
            if not im_active:
                self.inactive(subreddit, [])
            if im_active and self.contain_inactive(above_me):
                self.active_inactive_above(
                    subreddit, filter(lambda mod: not mod.is_active, above_me)
                )
            if im_active and self.contain_all_inactive(above_me):
                self.top_active_mod(
                    subreddit, filter(lambda mod: not mod.is_active, above_me)
                )
            if (
                    im_active
                    and self.contain_all_inactive(above_me)
                    and self.contain_all_inactive(below_me)
            ):
                self.only_one_active(
                    subreddit,
                    filter(lambda mod: not mod.is_active, above_me + below_me),
                )
            if not im_active and self.contain_active(below_me):
                self.inactive_active_below(
                    subreddit, filter(lambda mod: mod.is_active, below_me)
                )

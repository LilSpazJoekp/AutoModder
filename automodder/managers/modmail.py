"""Provide the Modmail class."""
import logging
from collections import defaultdict
from collections.abc import Callable, Iterable

from praw.models import (
    Comment,
    ListingGenerator,
    ModmailConversation,
    Redditor,
    Submission,
)

from ..logger import PrefixLogger
from ..utils import plural

log = logging.getLogger(__name__)


Item = Comment | Submission


class Modmail:
    """Class for scanning and archiving modmail conversations.

    This is used to perform certain checks on items and stores the ones that have passed
    the checks for possible archival.

    """

    @staticmethod
    def _log_prefix(item: ModmailConversation) -> str:
        """Generate a log prefix for an item.

        :param item: The item to generate the prefix for.

        :returns: The generated prefix as a string.

        """
        prefix = f"Modmail | r/{item.owner} | {item.id}"
        if item.participant:
            prefix += f" | {'u' if isinstance(item.participant, Redditor) else 'r'}/{item.participant}"
        else:
            prefix += " | u/[deleted]"
        return prefix

    def __init__(
        self,
        listing: Callable[[ListingGenerator], Iterable[ModmailConversation]],
        checks: Iterable[Callable[[ModmailConversation], bool]],
        states: list[str],
    ):
        """Initialize a new Modqueue.

        :param listing: The listing generator to scan.
        :param checks: The checks to perform on each item. If all the checks return
            `False`, the item will be added to the `items_to_archive` list.
        :param states: The modmail states to scan.

        """
        self.checks = checks
        self.items_to_archive = set()
        self.listing = listing
        self.log: PrefixLogger[ModmailConversation] = PrefixLogger(
            log, self._log_prefix
        )
        self.states = states

    def archive_found(self):
        """Remove items that have been found and meets the checks criteria.

        This method logs, removes and locks each item stored in items_to_archive list.

        """
        for item in self.items_to_archive:
            self.log.info("Archiving", item)
            try:
                if item.is_internal:
                    self.log.info("Skipping internal conversation", item)
                    continue
                item.archive()
            except Exception as e:
                self.log.exception(f"Error archiving: {e}", item)
            self.log.info("Archived", item)

    def scan(self) -> int:
        """Perform a scan over the items from the provided listing.

        For each item, if the item was previously approved and re-approval is allowed,
        it gets added to items_to_reapprove. Otherwise, it checks whether the item
        passes the provided checks and if it does, the item gets added to
        items_to_archive.

        :returns: The count of items to be removed and the items to be re-approved as a
            tuple.

        """
        aggregated = defaultdict(lambda: defaultdict(int))
        for state in self.states:
            for conversation in self.listing(state=state):
                for check in self.checks:
                    result, message = check(conversation)
                    if result:
                        self.log.info(message, conversation)
                        break
                else:
                    self.items_to_archive.add(conversation)

                aggregated[conversation.owner.display_name][state] += 1
        log.info(f"Found {plural(len(self.items_to_archive)):conversation} to archive")
        for subreddit, counts in aggregated.items():
            log.info("r/%s:", subreddit)
            for state, count in counts.items():
                log.info("    %s: %d", state, count)
        return len(self.items_to_archive)

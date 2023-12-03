"""Provide the Modqueue class."""
import logging
from collections.abc import Iterable

from praw.models import Comment, ListingGenerator, Submission, Subreddit
from prawcore import Forbidden

from ..checks import ActionQualifier, Check
from ..logger import PrefixLogger
from ..utils import human_timedelta, plural

log = logging.getLogger(__name__)


Item = Comment | Submission


class Modqueue:
    """Class for scanning items such as Comment and Submission objects.

    This is used to perform certain checks on items and stores the ones that have passed
    the checks for possible re-approval or removal.

    """

    @staticmethod
    def _log_prefix(item: Item) -> str:
        """Generate a log prefix for an item.

        :param item: The item to generate the prefix for.

        :returns: The generated prefix as a string.

        """
        prefix = f"r/{item.subreddit}"
        if item.author:
            prefix += f" | u/{item.author}"
        else:
            prefix += " | u/[deleted]"
        if isinstance(item, Comment):
            prefix += f" | s: {item.submission.id} c: {item.id}"
        else:
            prefix += f" | {item.id}"
        prefix += f" | {human_timedelta(item.created_utc)}"
        return prefix

    def __init__(
        self,
        subreddit: Subreddit,
        listing: ListingGenerator,
        checks: Iterable[Check],
        reapprove_previously_approved: bool,
    ):
        """Initialize a new Modqueue.

        :param listing: The listing generator to scan.
        :param checks: The checks to perform on each item.
        :param reapprove_previously_approved: Whether to re-approve previously approved
            items.
        :param subreddit: The subreddit to scan.

        """
        self.checks = checks
        self.items_to_reapprove = []
        self.items_to_remove = []
        self.listing = listing
        self.log: PrefixLogger[Item] = PrefixLogger(log, self._log_prefix)
        self.reapprove = reapprove_previously_approved
        self.subreddit = subreddit

    def reapprove_found(self):
        """Re-approves items that have been found and meets the checks criteria.

        This method logs and re-approves each item stored in items_to_reapprove list.

        """
        for item in self.items_to_reapprove:
            item.mod.approve()
            self.log.info("Re-approved", item)

    def remove_found(self):
        """Remove items that have been found and meets the checks criteria.

        This method logs, removes and locks each item stored in items_to_remove list.

        """
        for item in self.items_to_remove:
            item.mod.remove()
            self.log.info("Removed", item)
            try:
                item.mod.lock()
            except Exception as e:
                log.exception("Failed to lock", e)
                self.log.error("Failed to lock", item)
                continue
            self.log.info("Locked", item)

    def scan(self) -> tuple[int, int]:
        """Perform a scan over the items from the provided listing.

        For each item, if the item was previously approved and re-approval is allowed,
        it gets added to items_to_reapprove. Otherwise, it checks whether the item
        passes the provided checks and if it does, the item gets added to
        items_to_remove.

        :returns: The count of items to be removed and the items to be re-approved as a
            tuple.

        """
        try:
            for item in self.listing:
                remove = True
                messages = []
                for check in self.checks:
                    if self.reapprove and item.approved_by:
                        self.log.info(
                            f"Previously approved by u/{item.approved_by}",
                            item,
                        )
                        self.items_to_reapprove.append(item)
                        remove = False
                        break
                    result, message = check(item)
                    if result:
                        messages.append(message)
                    if check.qualifier == ActionQualifier.ALL:
                        remove &= result
                    if result and check.qualifier == ActionQualifier.ANY:
                        remove = result
                        break
                if remove:
                    self.log.info(" | ".join(messages), item)
                    self.items_to_remove.append(item)
            log.info(
                f"r/{self.subreddit} | Found {plural(len(self.items_to_remove)):item} to remove"
            )
            log.info(
                f"r/{self.subreddit} | Found {plural(len(self.items_to_reapprove)):item} to re-approve"
            )
            return len(self.items_to_remove), len(self.items_to_reapprove)
        except Forbidden:
            log.error(f"r/{self.subreddit} | Forbidden to scan modqueue")
            return 0, 0
        except Exception as e:
            log.exception(f"r/{self.subreddit} | Error scanning modqueue", exc_info=e)
            return 0, 0

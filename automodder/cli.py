"""Provide the CLI."""
import logging
import sys
from functools import partial

import click
import praw

from . import InvokeContext, set_verbose
from .checks import (
    check_age,
    check_pending_response,
    check_removed_by_automated_spam,
    check_score,
    check_unanswered,
)
from .managers import InactivityManager, Modmail, Modqueue
from .models import ConsoleWriter, GoogleSheetsWriter
from .models.context_object import LazySubreddits
from .utils import help_from_config, prompt_then_fallback_to_config

log = logging.getLogger(__name__)

state_mapping = {
    0: "new",
    1: "inprogress",
    2: "archived",
    3: "appeal",
    4: "join requests",
    5: "filtered",
}


@click.group()
@click.pass_context
@click.option(
    "subreddits",
    "-S",
    "--subreddits",
    callback=lambda _, __, value: value.split(",") if value else [],
    help="The subreddits to scan. Can be provided as a comma-separated list or as a single subreddit argument.",
    type=str,
)
@click.option(
    "min_subscriber_count",
    "-c",
    default=None,
    callback=prompt_then_fallback_to_config,
    help=help_from_config("min_subscriber_count"),
    type=int,
)
@click.option(
    "--dry-run",
    "-d",
    default=False,
    help="Don't action anything. Just scan.",
    is_flag=True,
)
@click.option("--verbose", "-v", default=False, help="Enable verbose logging.")
def main(
    context: click.Context,
    subreddits: list[str],
    min_subscriber_count: int,
    dry_run: bool,
    verbose: bool,
):
    """AutoModder is a tool to perform moderator actions in the specified subreddits.

    Subreddits can be provided as a comma-separated list or as a single subreddit
    argument.

    """
    from . import config

    try:
        reddit = praw.Reddit("AutoModder")
    except Exception:  # noqa: BLE001
        log.error("Reddit credentials not found. Please fill in the praw.ini file.")
        sys.exit(1)
    context.obj = InvokeContext(
        config,
        dry_run,
        reddit,
        LazySubreddits(
            min_subscriber_count=min_subscriber_count,
            reddit=reddit,
            subreddits=subreddits,
        ),
    )
    if verbose:
        set_verbose()


@main.command()
@click.pass_obj
@click.option(
    "--redditor",
    "-r",
    default=None,
    help="The redditor to check for inactivity. Defaults to the current user.",
)
@click.option(
    "--output",
    "-o",
    default="console",
    help="The output format.",
    type=click.Choice(["console", "sheets"]),
)
def inactive(context: InvokeContext, redditor: str | None, output: str):
    """Check for inactive moderators in the provided subreddit(s)."""
    subreddits = context.subreddits
    if output == "console":
        writer = ConsoleWriter
    elif output == "sheets":
        writer = GoogleSheetsWriter
    else:
        msg = f"Unknown output format: {output}"
        raise ValueError(msg)
    scanner = InactivityManager(subreddits, context.reddit, redditor, writer)
    scanner.scan()
    scanner.print_results()


@main.command()
@click.pass_obj
@click.option(
    "states",
    "--state",
    "-s",
    multiple=True,
    type=str,
    default=["all"],
    help="The state(s) of the modmail to archive. Can be provided multiple times for multiple states.",
)
@click.option(
    "--ignore-unanswered",
    "-a",
    is_flag=True,
    default=False,
    help="Only archive answered modmail conversations.",
)
@click.option(
    "--ignore-pending-response",
    "-r",
    is_flag=True,
    default=False,
    help="Only archive modmail conversations that is not pending a mod response. The difference between 'only answered' is this checks if a mod replied and then a user later replied again.",
)
def modmail(
    context: InvokeContext,
    states: list[str],
    ignore_unanswered: bool,
    ignore_pending_response: bool,
):
    """Archive modmail conversations for the provided subreddit(s)."""
    subreddits = context.subreddits
    if len(subreddits) == 1:
        subreddit = subreddits[0]
        conversations = partial(subreddit.modmail.conversations, limit=None)
    else:
        subreddit = subreddits[0]
        conversations = partial(
            subreddit.modmail.conversations, other_subreddits=subreddits[1:], limit=None
        )

    scanner = Modmail(
        conversations,
        [
            check_unanswered(ignore_unanswered),
            check_pending_response(ignore_pending_response),
        ],
        states,
    )
    archive_count = scanner.scan()
    if (
        archive_count
        and click.confirm(
            "Are you sure you want to archive these conversations?", abort=True
        )
        and not context.dry_run
    ):
        scanner.archive_found()


@main.command()
@click.pass_obj
@click.option(
    "--min-score",
    "-s",
    callback=prompt_then_fallback_to_config,
    default=None,
    help=help_from_config("min_score"),
    type=int,
)
@click.option(
    "--min-age",
    "-a",
    callback=prompt_then_fallback_to_config,
    default=None,
    help=help_from_config("min_age"),
    type=int,
)
@click.option(
    "--only",
    "-o",
    default=None,
    help="The kind of items to remove.",
    type=click.Choice(["comments", "links"]),
)
@click.option(
    "--reapprove/--no-reapprove",
    default=True,
    help="Reapprove previously approved items.",
)
def modqueue(
    context: InvokeContext,
    min_score: int,
    min_age: int,
    only: str,
    reapprove: bool,
):
    """Process the modqueue for the provided subreddit(s)."""
    subreddits = context.subreddits
    for subreddit in subreddits:
        scanner = Modqueue(
            subreddit,
            subreddit.mod.modqueue(only=only, limit=None),
            [
                check_score(min_score),
                check_age(min_age),
                check_removed_by_automated_spam(),
            ],
            reapprove,
        )
        remove_count, approve_count = scanner.scan()
        if not context.dry_run:
            if remove_count:
                scanner.remove_found()
            if approve_count:
                scanner.reapprove_found()

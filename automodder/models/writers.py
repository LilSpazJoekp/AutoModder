"""Models for writing SubredditBuckets to various outputs."""
from abc import ABC, abstractmethod
from collections.abc import Iterable

import click
from praw.models import Redditor

from . import GoogleSheets, SubredditBucket


class BaseWriter(ABC):
    """Base class for writers."""

    @abstractmethod
    def write(self):
        """Write the buckets to the output."""

    def __init__(self, buckets: Iterable[SubredditBucket], me: Redditor):
        """Initialize a new BaseWriter instance."""
        self.buckets = buckets
        self.me = me


class ConsoleWriter(BaseWriter):
    """Writes the buckets to the console."""

    def __init__(self, buckets: Iterable[SubredditBucket], me: Redditor):
        """Initialize a new ConsoleWriter instance."""
        super().__init__(buckets, me)
        self.google_sheets = GoogleSheets(me)

    def write(self):
        """Write the buckets to the console."""
        for bucket in self.buckets:
            click.secho(bucket.name, fg="blue")
            click.secho("-" * len(bucket.name), fg="green")
            for item, other_mods in bucket.bucket:
                subreddit_str = click.style(f"r/{item}", fg="yellow")

                # subscriber count but with a spectrum of colors
                if item.subscribers <= 5000:
                    subscriber_count_color = "white"
                elif item.subscribers <= 10000:
                    subscriber_count_color = "blue"
                elif item.subscribers <= 100000:
                    subscriber_count_color = "green"
                elif item.subscribers <= 1000000:
                    subscriber_count_color = "yellow"
                elif item.subscribers <= 10000000:
                    subscriber_count_color = "red"
                else:
                    subscriber_count_color = "magenta"

                subreddit_count_str = click.style(
                    f"{item.subscribers:,}", fg=subscriber_count_color
                )
                position_str = click.style(
                    str(item.position), fg="red" if item.position <= 10 else "green"
                )
                active_str = click.style(
                    str(item.is_active), fg="green" if item.is_active else "red"
                )
                click.echo(
                    f"{subreddit_str:<31} | subscribers: {subreddit_count_str:<20} | position: {position_str:12} | active: {active_str}"
                )
                for mod in other_mods:
                    mod_str = click.style(f"u/{mod}", fg="blue")
                    position_str = click.style(
                        str(mod.position), fg="red" if mod.position <= 10 else "green"
                    )
                    active_str = click.style(
                        str(mod.is_active), fg="green" if mod.is_active else "red"
                    )
                    click.echo(
                        f"    {mod_str:<31} | position: {position_str:12} | active: {active_str}"
                    )
            click.echo()


class GoogleSheetsWriter(BaseWriter):
    """Writes the buckets to a Google Sheet."""

    def __init__(self, buckets: Iterable[SubredditBucket], me: Redditor):
        """Initialize a new GoogleSheetsWriter instance."""
        super().__init__(buckets, me)
        self.google_sheets = GoogleSheets(me)

    def write(self):
        """Write the buckets to a Google Sheet."""
        spreadsheet = self.google_sheets.generate_sheets(self.buckets)
        click.echo(
            f"Spreadsheet created: {spreadsheet.share(None, perm_type='anyone', role='reader', with_link=True)}"
        )

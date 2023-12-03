"""Provide the GoogleSheets class."""
from __future__ import annotations

from typing import TYPE_CHECKING

import gspread
from gspread import Spreadsheet, Worksheet
from gspread_formatting import (
    BooleanCondition,
    BooleanRule,
    CellFormat,
    Color,
    ConditionalFormatRule,
    GridRange,
    get_conditional_format_rules,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from praw.models import Redditor

    from ..managers.inactivity import SubredditBucket

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.metadata",
]
WHITE = Color.fromHex("#ffffff")
GREEN = Color.fromHex("#57bb8a")
RED = Color.fromHex("#e67c73")
YELLOW = Color.fromHex("#ffd666")
BLUE = Color.fromHex("#73a4ff")
MAGENTA = Color.fromHex("#ff73ff")

COLUMN_LETTERS = ["A", "B", "C", "D", "E"]
HEADER = ["Subreddit", "Subscribers", "Redditor", "Position", "Active"]


def column_range(name: str) -> str:
    """Return the column range for the given header name.

    :param name: The name of the header.

    :returns: The column range for the given header name.

    """
    return f"{header_letter(name)}:{header_letter(name)}"


def header_letter(name: str) -> str:
    """Return the letter for the given header name.

    :param name: The name of the header.

    :returns: The letter for the given header name.

    """
    return COLUMN_LETTERS[HEADER.index(name)]


class GoogleSheets:
    """Manages the Google Sheets API."""

    @staticmethod
    def _create_rule(
        worksheet: Worksheet,
        column: str,
        color: Color,
        value: int,
        qualifier: str | None = None,
    ) -> ConditionalFormatRule:
        if qualifier == "min":
            condition = BooleanCondition("NUMBER_GREATER_THAN_EQ", [str(value)])
        elif qualifier == "eq":
            condition = BooleanCondition("NUMBER_EQ", [str(value)])
        else:
            condition = BooleanCondition("NUMBER_LESS", [str(value)])
        return ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(column_range(column), worksheet)],
            booleanRule=BooleanRule(
                condition=condition, format=CellFormat(backgroundColor=color)
            ),
        )

    def __init__(self, me: Redditor):
        """Initialize a new GoogleSheets instance.

        :param me: The authenticated Redditor instance.

        """
        self._client = gspread.oauth()
        self.me = me

    def generate_sheets(self, sheets: Iterable[SubredditBucket]) -> Spreadsheet:
        """Generate the Google Sheets spreadsheet.

        :param sheets: The list of subreddit buckets to generate from.

        :returns: The generated spreadsheet.

        """
        spreadsheet = self._client.create(f"Inactivity Information for u/{self.me}")
        for bucket in sheets:
            rows = [HEADER]
            worksheet = spreadsheet.add_worksheet(
                title=bucket.name,
                rows=str(
                    sum([len(list(other_mods)) + 1 for _, other_mods in bucket]) + 1
                ),
                cols=len(HEADER),
            )
            for item, other_mods in bucket:
                subreddit_str = item.display_name
                rows.append(
                    [
                        subreddit_str,
                        item.subscribers,
                        self.me.name,
                        item.position,
                        item.is_active,
                    ]
                )
                for mod in other_mods:
                    rows.append(
                        [
                            item.display_name,
                            item.subscribers,
                            mod.name,
                            mod.position,
                            mod.is_active,
                        ]
                    )
            worksheet.append_rows(rows)
            worksheet.freeze(rows=1)
            rules = [
                self._create_rule(
                    worksheet, "Position", MAGENTA, 1, "eq"
                ),  # White for <5000
                self._create_rule(worksheet, "Position", RED, 5),
                self._create_rule(worksheet, "Position", YELLOW, 10),
                self._create_rule(
                    worksheet, "Subscribers", WHITE, 5000
                ),  # White for <5000
                self._create_rule(
                    worksheet, "Subscribers", BLUE, 10000
                ),  # Blue for 5000-10000
                self._create_rule(
                    worksheet, "Subscribers", GREEN, 100000
                ),  # Green for 10000-100000
                self._create_rule(
                    worksheet, "Subscribers", YELLOW, 1000000
                ),  # Yellow for 100000-1000000
                self._create_rule(
                    worksheet, "Subscribers", RED, 10000000
                ),  # Red for 1000000-10000000
                self._create_rule(
                    worksheet, "Subscribers", MAGENTA, 10000000, "min"
                ),  # Magenta for >= 10000000
                (
                    ConditionalFormatRule(
                        ranges=[
                            GridRange.from_a1_range(column_range("Active"), worksheet)
                        ],
                        booleanRule=BooleanRule(
                            condition=BooleanCondition("TEXT_EQ", ["TRUE"]),
                            format=CellFormat(backgroundColor=GREEN),
                        ),
                    )
                ),
                (
                    ConditionalFormatRule(
                        ranges=[
                            GridRange.from_a1_range(column_range("Active"), worksheet)
                        ],
                        booleanRule=BooleanRule(
                            condition=BooleanCondition("TEXT_EQ", ["FALSE"]),
                            format=CellFormat(backgroundColor=RED),
                        ),
                    )
                ),
            ]
            existing_rules = get_conditional_format_rules(worksheet)
            existing_rules.extend(rules)
            existing_rules.save()
            worksheet.format(
                column_range("Subscribers"),
                {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}},
            )
            worksheet.set_basic_filter()
        spreadsheet.del_worksheet(spreadsheet.sheet1)
        return spreadsheet

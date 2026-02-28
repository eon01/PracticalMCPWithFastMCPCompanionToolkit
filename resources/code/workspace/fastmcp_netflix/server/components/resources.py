"""
MCP Resources for the Netflix server.

This module contains all resource implementations that can be read by MCP clients.
Each resource is a plain Python function decorated with @mcp.resource().

Resources are defined here and registered by calling register_resources(mcp)
from main.py. This avoids circular import issues and keeps the codebase organized.
"""

import json

from fastmcp import FastMCP


def register_resources(mcp: FastMCP):
    """Register all resources with the FastMCP instance.

    This function is called from main.py after the mcp instance is created.
    It avoids circular import issues by receiving the mcp instance as a parameter.
    """

    @mcp.resource("netflix://guide")
    def get_data_guide() -> str:
        """Netflix data guide with important notes and usage information.

        Provides context about the dataset, time coverage, data quality notes,
        and guidance on using the available tools effectively.
        """
        guide_data = {
            "about": "Netflix viewing data for movies from June 2021 to December 2024",
            "important_notes": [
                "All tools return WEEKLY viewing data only (7-day periods)",
                "Weekly rankings show top 10 positions only (rank 1-10)",
                "Use 'hours_viewed' as primary metric - it's more reliable than 'views'",
                "Movie title searches are partial match and case-insensitive",
                "The 'views' metric can be NULL for some periods",
                "Cumulative weeks in top 10 tracks how many total weeks a title ranked",
            ],
            "data_characteristics": {
                "content_type": "Movies only",
                "time_range": "June 2021 - December 2024",
                "granularity": "Weekly snapshots (7-day periods)",
                "geographic_scope": "Global Netflix viewing data",
            },
            "available_metrics": {
                "hours_viewed": "Total viewing hours in the period (most reliable metric)",
                "views": "Number of views (may be NULL for some periods)",
                "view_rank": "Position in weekly top 10 (1-10, or NULL if outside top 10)",
                "cumulative_weeks_in_top10": "Total weeks the title has appeared in top 10",
            },
            "usage_tips": [
                "For most analyses, prefer 'hours_viewed' over 'views'",
                "Title searches are flexible - partial matches work well",
                "Date ranges span multiple years - check available periods first",
                "Weekly data allows trend analysis over time",
            ],
        }

        return json.dumps(guide_data, indent=2)

    @mcp.resource("netflix://stats/movies")
    def get_movie_statistics() -> str:
        """Movie database statistics including counts and date coverage.

        Provides a high-level overview of the movie dataset: total number of
        movies, earliest and latest viewing data available, and total weekly
        snapshots. This helps LLMs understand the scope and boundaries of
        available data.

        This is a static resource since the database does not evolve.
        """
        # Static statistics - database does not change
        stats = {
            "movies": {
                "total": 11960,
                "with_viewing_data": 3959,
            },
            "viewing_data": {
                "earliest_week": "2021-06-20",
                "latest_week": "2024-12-08",
                "total_weekly_snapshots": 26908,
                "granularity": "WEEKLY",
            },
            "note": "These statistics cover movie content only. "
            "TV show data exists but the server does not expose them",
        }

        return json.dumps(stats, indent=2)

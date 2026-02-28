"""
MCP Prompts for the Netflix server.

This module contains all prompt implementations that can be requested by MCP clients.
Each prompt is a plain Python function decorated with @mcp.prompt().

Prompts are defined here and registered by calling register_prompts(mcp)
from main.py. This avoids circular import issues and keeps the codebase organized.

Key Concepts:
• Prompts generate message templates for LLMs to provide structured analysis
• Unlike tools (which execute queries), prompts ASK the LLM to analyze data
• Prompts are user-initiated (e.g., via slash commands like /analyze-trend)
• The server generates the prompt, but the LLM response goes to the client
"""

from sqlalchemy.orm import Session

from fastmcp import FastMCP
from fastmcp.dependencies import Depends
from fastmcp.exceptions import PromptError

# Import database models and dependencies
from database import Movie
from database import ViewSummary
from database import get_db_session


def register_prompts(mcp: FastMCP):
    """Register all prompts with the FastMCP instance.

    This function is called from main.py after the mcp instance is created.
    It decorates each prompt function and registers it with the server.

    Args:
      mcp: The FastMCP server instance to register prompts with.
    """

    @mcp.prompt()
    def analyze_movie_performance(
        movie_id: str,
        db: Session = Depends(get_db_session),
    ) -> str:
        """Analyze viewing performance trends for a movie.

        Fetches weekly viewing statistics and generates a prompt for the LLM
        to analyze trends and provide insights.

        Use this tool when you want to analyze how a movie is performing over time,
        identify trends, peak performance periods, and gain insights into viewer engagement.

        Args:
          movie_id: The unique movie ID from the database (as string).
        """

        # Parse movie_id to integer
        # MCP spec requires prompt arguments to be strings, so we convert here
        try:
            movie_id_int = int(movie_id)
        except ValueError:
            raise PromptError(f"Invalid movie_id: '{movie_id}' is not a valid integer")

        # Query for movie and its viewing stats by ID
        results = (
            db.query(Movie.title, ViewSummary)
            .join(ViewSummary, ViewSummary.movie_id == Movie.id)
            .filter(Movie.id == movie_id_int)
            .filter(ViewSummary.duration == "WEEKLY")
            .order_by(ViewSummary.start_date)
            .all()
        )

        if not results:
            raise PromptError(
                f"No viewing data found for movie ID {movie_id}. "
                f"Movie may not exist or has no weekly viewing stats."
            )

        # Extract movie title from first result
        movie_title = results[0][0]

        # Format viewing data concisely
        data_lines = []
        for _, view_summary in results:
            rank = view_summary.view_rank or "N/A"
            hours = (
                f"{view_summary.hours_viewed:,.0f}"  # Format with commas and no decimals
                if view_summary.hours_viewed
                else "N/A"
            )
            data_lines.append(
                f"• {view_summary.start_date}: Rank #{rank}, {hours} hours"
            )

        viewing_data = "\n".join(data_lines)

        # expected response format:
        #  • 2022-12-18: Rank #1, 82,190,000 hours
        #  • 2022-12-25: Rank #1, 127,600,000 hours
        #  • 2023-01-01: Rank #2, 92,300,000 hours

        # Generate simplified prompt
        return (
            f"Analyze viewing trends for '{movie_title}' ({len(results)} weeks of data): "
            f"{viewing_data}"
            "\n\n"
            "Provide a brief analysis of trends, peak performance, and key insights."
        )

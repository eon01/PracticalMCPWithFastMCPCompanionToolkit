"""
MCP Tools for the Netflix server.

This module contains all tool implementations that can be called by MCP clients.
Each tool is a plain Python function decorated with @mcp.tool().

Tools are defined here and registered by calling register_tools(mcp)
from main.py. This avoids circular import issues.
"""

import os
from typing import Annotated
from typing import Literal

import httpx
from pydantic import Field
from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy.orm import Session

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentContext
from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from fastmcp.server.context import Context

# Import database models and dependencies
from database import Movie
from database import ViewSummary
from database import get_db_session


def register_tools(mcp: FastMCP):
    """Register all tools with the FastMCP instance.

    This function is called from main.py after the mcp instance is created.
    It avoids circular import issues by receiving the mcp instance as a parameter.
    """

    @mcp.tool(timeout=60.0)
    async def search_movies(
        title: str,
        db: Session = Depends(get_db_session),
        ctx: Context = CurrentContext(),
    ) -> dict:
        """Find a movie by title when you don't already have its ID.

        ONLY use this when:
        - User asks to find a specific movie by name
        - You want to get the movie ID for a title you don't have
        - You want to show the user multiple matches and ask them to choose

        DO NOT use this if you have movie IDs from get_top_movies - use those IDs directly.

        Args:
          title: Partial or full movie title to search for.
        """
        # Step 1: Try exact match first (case-insensitive)
        results = db.query(Movie).filter(Movie.title.ilike(title)).limit(5).all()

        # Step 2: If no exact match, try partial match
        if not results:
            results = (
                db.query(Movie).filter(Movie.title.ilike(f"%{title}%")).limit(5).all()
            )

        if not results:
            raise ToolError(f"No movies found matching '{title}'.")

        # Exactly one match - confirm with user via elicitation
        if len(results) == 1:
            movie = results[0]
            year = movie.release_date.year if movie.release_date else "Unknown year"

            # Ask user to confirm this is the right movie
            # response_type=bool means the user answers yes/no
            confirm = await ctx.elicit(
                message=f"I found '{movie.title}' ({year}). Is this the movie you were looking for?\n"
                "Type 'yes' to confirm, 'no' to try a different search, or press Enter to cancel.",
                response_type=bool,
            )

            # confirm.action is "accept", "decline", or "cancel"
            # confirm.data is True (yes) or False (no) when action is "accept"
            # If user declined (Enter), cancelled, or said "no" → stop
            if confirm.action != "accept" or not confirm.data:
                raise ToolError("User cancelled the search. Do not retry.")
        # Multiple matches - ask user to choose
        else:
            # Build options with distinguishing info (year + ID)
            options = []
            for i, movie in enumerate(results):
                year = movie.release_date.year if movie.release_date else "Unknown year"
                options.append(f"{i + 1}. {movie.title} ({year}) [ID: {movie.id}]")
            options_text = "\n".join(options)

            elicit_result = await ctx.elicit(
                message=f"While searching for a movie matching '{title}', "
                "I found multiple matches. "
                "Please select the correct one by entering the number:\n"
                f"{options_text}\n"
                "Press Enter without typing a number to cancel.",
                response_type=int,
            )

            if elicit_result.action == "accept":
                choice = elicit_result.data
                if 1 <= choice <= len(results):
                    movie = results[choice - 1]
                else:
                    raise ToolError(f"Invalid choice. Enter 1-{len(results)}.")
            else:
                raise ToolError("User cancelled the search. Do not retry.")

        # Return complete, structured information
        result = {
            "id": movie.id,
            "title": movie.title,
            "release_date": movie.release_date.isoformat()
            if movie.release_date
            else None,
            "runtime": movie.runtime,
        }
        return result

    @mcp.tool(timeout=20.0)
    async def get_top_movies(
        metric: Literal["hours_viewed", "views"] = "hours_viewed",
        n: Annotated[
            int, Field(description="Number of top movies to return", ge=1)
        ] = 10,
        db: Session = Depends(get_db_session),
        ctx: Context = CurrentContext(),
    ) -> list:
        """Get top N movies ranked by total views or hours watched.

        Returns movie data including 'id' field.

        Args:
          metric: 'hours_viewed' or 'views'. Defaults to 'hours_viewed'.
          n: Number of top movies to return (must be >= 1). Defaults to 10.
        """
        await ctx.report_progress(0, n, message=f"Fetching top {n} by {metric}...")

        metric_col = (
            func.sum(ViewSummary.hours_viewed)
            if metric == "hours_viewed"
            else func.sum(ViewSummary.views)
        )

        # Fetch all results (single query for efficiency)
        all_results = (
            db.query(
                Movie.id, Movie.title, Movie.release_date, metric_col.label("total")
            )
            .join(ViewSummary, ViewSummary.movie_id == Movie.id)
            .group_by(Movie.id, Movie.title, Movie.release_date)
            .order_by(desc("total"))
            .limit(n)
            .all()
        )

        # Process results one-by-one to demonstrate incremental progress
        # Note: This is intentionally inefficient for educational purposes to show progress reporting.
        # In production, you'd return all results immediately
        results = []
        for i, r in enumerate(all_results, start=1):
            # Report progress after each movie processed
            await ctx.report_progress(i, n, message=f"Processing movie {i}/{n}")

            results.append(
                {
                    "id": r.id,
                    "title": r.title,
                    "release_date": (
                        r.release_date.isoformat() if r.release_date else None
                    ),
                    metric: r.total,
                }
            )

        return results

    @mcp.tool()
    async def add_to_favorites(
        title: str | None = None,
        movie_id: int | None = None,
        db: Session = Depends(get_db_session),
        ctx: Context = CurrentContext(),
    ) -> str:
        """Add a movie to your personal favorites list.

        Always use movie_id when you have it from other tools.
        Only use title when the user specifically asks to add a movie by name and you don't have the ID.

        Args:
          movie_id: Movie ID (PREFERRED). Use this when available from get_top_movies.
          title: Movie title (exact match only). Only use if you don't have movie_id.
        """
        if not title and not movie_id:
            raise ToolError("Must provide either 'title' or 'movie_id'")

        # Lookup movie by ID or exact title
        if movie_id:
            movie = db.query(Movie).filter(Movie.id == movie_id).first()
        else:
            movie = db.query(Movie).filter(Movie.title.ilike(title)).first()

        if not movie:
            raise ToolError("Movie not found. Use search_movies to find it first.")

        # Get favorites and add
        favorites = await ctx.get_state("favorites") or []

        if any(fav.get("id") == movie.id for fav in favorites):
            return f"'{movie.title}' is already in your favorites"

        favorites.append({"id": movie.id, "title": movie.title})
        await ctx.set_state("favorites", favorites)

        return f"Added '{movie.title}' to favorites. You now have {len(favorites)} favorite(s)."

    @mcp.tool()
    async def get_favorites(
        ctx: Context = CurrentContext(),
    ) -> dict:
        """Get your current favorites list.

        Demonstrates reading session state with ctx.get_state().

        Returns:
          A dict with 'count' and 'favorites' keys.
        """
        favorites = await ctx.get_state("favorites") or []
        return {"count": len(favorites), "favorites": favorites}

    @mcp.tool(timeout=40.0)
    async def summarize_movie(
        title: str,
        ctx: Context = CurrentContext(),
    ) -> str:
        """Fetch movie data from OMDB and generate an AI summary.

        Demonstrates using ctx.sample() to generate LLM text.

        Args:
          title: The movie title to look up and summarize.
        """
        # Get API key
        api_key = os.getenv("OMDB_API_KEY")
        if not api_key:
            raise ToolError(
                "OMDB_API_KEY not configured. Get a free key at https://www.omdbapi.com/apikey.aspx"
            )

        # Fetch movie data from OMDB
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    "https://www.omdbapi.com/",
                    params={"t": title, "apikey": api_key},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException:
            raise ToolError(f"OMDB API request timed out for '{title}'.")
        except httpx.HTTPError as e:
            raise ToolError(f"Failed to connect to OMDB API: {e}")

        # Check if movie was found
        if data.get("Response") == "False":
            raise ToolError(f"Could not find '{title}' in OMDB database.")

        # Extract key movie info
        movie_info = {
            "Title": data.get("Title"),
            "Year": data.get("Year"),
            "Genre": data.get("Genre"),
            "Director": data.get("Director"),
            "Actors": data.get("Actors"),
            "Plot": data.get("Plot"),
            "IMDb Rating": data.get("imdbRating"),
            "Rotten Tomatoes": next(
                (
                    r["Value"]
                    for r in data.get("Ratings", [])
                    if r["Source"] == "Rotten Tomatoes"
                ),
                "N/A",
            ),
        }

        movie_data_text = "\n".join(
            f"{key}: {value}" for key, value in movie_info.items() if value
        )

        # Generate summary using LLM sampling
        result = await ctx.sample(
            messages=f"Create a concise, engaging summary of this movie:\n\n{movie_data_text}",
            system_prompt="You are a film critic. Write a 2-3 sentence summary that captures the essence of the movie.",
            max_tokens=800,
        )

        return result.text or "Summary could not be generated."

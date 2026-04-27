"""LLM integration for FinAlly chat assistant."""

from __future__ import annotations

import json
import logging
import os

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Trade(BaseModel):
    """Trade instruction from LLM."""

    ticker: str = Field(..., description="Stock ticker symbol")
    side: str = Field(..., description="'buy' or 'sell'")
    quantity: float = Field(..., description="Number of shares")


class WatchlistChange(BaseModel):
    """Watchlist change instruction from LLM."""

    ticker: str = Field(..., description="Stock ticker symbol")
    action: str = Field(..., description="'add' or 'remove'")


class ChatResponse(BaseModel):
    """Structured response from LLM."""

    message: str = Field(..., description="Conversational response to the user")
    trades: list[Trade] = Field(default_factory=list, description="Trades to execute")
    watchlist_changes: list[WatchlistChange] = Field(
        default_factory=list, description="Watchlist changes to apply"
    )


def _get_llm_system_prompt(portfolio_context: str) -> str:
    """Build the system prompt for the LLM.

    Args:
        portfolio_context: Current portfolio state as a string.

    Returns:
        System prompt string.
    """
    return f"""You are FinAlly, an AI trading assistant for a simulated trading platform. Your role is to help the user manage their investment portfolio, analyze market positions, and execute trades.

CURRENT PORTFOLIO STATE:
{portfolio_context}

YOUR RESPONSIBILITIES:
- Analyze portfolio composition and identify concentration risks
- Suggest trades based on portfolio analysis and market conditions
- Execute trades when the user asks or agrees to recommendations
- Manage the user's watchlist proactively (add promising tickers, remove uninteresting ones)
- Provide concise, data-driven responses with reasoning
- Be conversational but professional

TRADE EXECUTION:
- You can propose trades with specific tickers, quantities, and sides (buy/sell)
- Trades execute immediately at current market prices with no confirmation
- Always ensure the user has sufficient cash for buys and shares for sells
- Explain the rationale for any trades you recommend

RESPONSE FORMAT:
Always respond with valid JSON structured as:
{{
  "message": "Your conversational response to the user",
  "trades": [
    {{"ticker": "AAPL", "side": "buy", "quantity": 10}}
  ],
  "watchlist_changes": [
    {{"ticker": "PYPL", "action": "add"}}
  ]
}}

The "message" field is required. "trades" and "watchlist_changes" are optional arrays - omit them if not applicable.
"""


def _get_mock_response() -> ChatResponse:
    """Return a deterministic mock response for testing.

    Returns:
        Mock ChatResponse.
    """
    return ChatResponse(
        message="Mock response: This is a simulated trading assistant. Your portfolio is doing well! Consider diversifying into tech stocks.",
        trades=[],
        watchlist_changes=[],
    )


async def call_llm(
    user_message: str,
    portfolio_context: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> ChatResponse:
    """Call OpenAI LLM with structured output.

    Args:
        user_message: The user's chat message.
        portfolio_context: Current portfolio state formatted as string.
        conversation_history: Recent chat history (list of {"role": "...", "content": "..."}).

    Returns:
        Parsed ChatResponse.

    Raises:
        ValueError: If LLM response is invalid or API fails.
    """
    if os.getenv("LLM_MOCK") == "true":
        logger.info("Using mock LLM response")
        return _get_mock_response()

    try:
        import litellm
    except ImportError as e:
        raise ValueError("litellm not installed. Install with: uv add litellm") from e

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    system_prompt = _get_llm_system_prompt(portfolio_context)

    # Build message history
    messages = []
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    logger.info("Calling OpenAI with gpt-4o for structured output")

    try:
        # Use OpenAI with structured output
        response = litellm.completion(
            model="openai/gpt-4o",
            messages=messages,
            system=system_prompt,
            response_format={"type": "json_schema", "json_schema": {
                "name": "ChatResponse",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "trades": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "ticker": {"type": "string"},
                                    "side": {"type": "string"},
                                    "quantity": {"type": "number"},
                                },
                                "required": ["ticker", "side", "quantity"],
                            },
                        },
                        "watchlist_changes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "ticker": {"type": "string"},
                                    "action": {"type": "string"},
                                },
                                "required": ["ticker", "action"],
                            },
                        },
                    },
                    "required": ["message"],
                },
            }},
        )

        # Parse response
        response_text = response.choices[0].message.content
        logger.debug("LLM response: %s", response_text)

        response_json = json.loads(response_text)
        parsed = ChatResponse(**response_json)

        logger.info("LLM response parsed successfully")
        return parsed

    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM response as JSON: %s", response_text)
        raise ValueError(f"LLM response was not valid JSON: {e}") from e
    except Exception as e:
        logger.error("LLM API call failed: %s", e)
        raise ValueError(f"LLM API call failed: {e}") from e

"""Tests for SSE streaming endpoint."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.market.cache import PriceCache
from app.market.stream import _generate_events, create_stream_router


class TestSSEStream:
    """Tests for SSE streaming functionality."""

    def test_create_stream_router_returns_router(self):
        """Test that create_stream_router returns a FastAPI APIRouter."""
        cache = PriceCache()
        router = create_stream_router(cache)

        assert router is not None
        assert hasattr(router, "routes")

    @pytest.mark.asyncio
    async def test_generate_events_yields_retry_directive(self):
        """Test that the event generator yields the retry directive."""
        cache = PriceCache()
        request = AsyncMock()
        request.is_disconnected = AsyncMock(return_value=True)
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        gen = _generate_events(cache, request, interval=0.01)
        first_event = await gen.__anext__()

        assert "retry:" in first_event

    @pytest.mark.asyncio
    async def test_generate_events_stops_on_disconnect(self):
        """Test that the event generator stops when client disconnects."""
        cache = PriceCache()
        request = AsyncMock()
        request.is_disconnected = AsyncMock(return_value=True)
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        gen = _generate_events(cache, request, interval=0.01)

        # Consume the retry directive
        await gen.__anext__()

        # Next call should stop (StopAsyncIteration)
        with pytest.raises(StopAsyncIteration):
            await asyncio.wait_for(gen.__anext__(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_generate_events_with_prices(self):
        """Test that the event generator sends price data."""
        cache = PriceCache()
        cache.update("AAPL", 190.50)
        cache.update("GOOGL", 175.25)

        # Simulate a client that disconnects after first data event
        call_count = [0]

        async def mock_is_disconnected():
            call_count[0] += 1
            # Allow one data event, then disconnect
            return call_count[0] > 1

        request = AsyncMock()
        request.is_disconnected = mock_is_disconnected
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        gen = _generate_events(cache, request, interval=0.001)

        # Skip retry directive
        await gen.__anext__()

        # Get the data event
        event = await asyncio.wait_for(gen.__anext__(), timeout=0.5)

        assert "data:" in event
        data_str = event.replace("data: ", "").strip()
        data = json.loads(data_str)

        assert "AAPL" in data
        assert "GOOGL" in data
        assert data["AAPL"]["price"] == 190.50
        assert data["GOOGL"]["price"] == 175.25

    @pytest.mark.asyncio
    async def test_generate_events_respects_version_counter(self):
        """Test that events are only sent when cache version changes."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)

        event_count = [0]

        async def mock_is_disconnected():
            # Disconnect after a few checks
            return event_count[0] > 3

        request = AsyncMock()
        request.is_disconnected = mock_is_disconnected
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        gen = _generate_events(cache, request, interval=0.001)

        # Skip retry directive
        await gen.__anext__()
        event_count[0] += 1

        # Get first data event
        event1 = await asyncio.wait_for(gen.__anext__(), timeout=0.5)
        event_count[0] += 1
        assert "data:" in event1

        # No change to cache, no new event should be generated
        # (the generator sleeps and checks again)
        # Update cache to trigger new event
        cache.update("AAPL", 191.00)

        event2 = await asyncio.wait_for(gen.__anext__(), timeout=0.5)
        event_count[0] += 1
        assert "data:" in event2

        data1 = json.loads(event1.replace("data: ", "").strip())
        data2 = json.loads(event2.replace("data: ", "").strip())

        # Second event should have updated price
        assert data1["AAPL"]["price"] == 190.00
        assert data2["AAPL"]["price"] == 191.00

    @pytest.mark.asyncio
    async def test_generate_events_empty_cache(self):
        """Test that the generator handles an empty cache gracefully."""
        cache = PriceCache()

        call_count = [0]

        async def mock_is_disconnected():
            call_count[0] += 1
            return call_count[0] > 1

        request = AsyncMock()
        request.is_disconnected = mock_is_disconnected
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        gen = _generate_events(cache, request, interval=0.001)

        # Skip retry directive
        await gen.__anext__()

        # With empty cache, no data event should be sent, generator should loop
        # and then disconnect
        with pytest.raises(StopAsyncIteration):
            await asyncio.wait_for(gen.__anext__(), timeout=0.2)

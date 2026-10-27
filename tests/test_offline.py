"""Offline tests with stubbed API responses."""

from __future__ import annotations

from typing import Any

import pytest

from mvg import MvgApi

DEPARTURE = {
    "realtimeDepartureTime": 1668524580000,
    "plannedDepartureTime": 1668524460000,
    "realtime": True,
    "label": "X1",
    "destination": "Somewhere",
    "transportType": "HOVERCRAFT",
    "cancelled": False,
    "messages": [],
}
LOCATION = {"globalId": "de:09162:70", "name": "Universität", "place": "München", "latitude": 48.1, "longitude": 11.5}


def stub_api(monkeypatch: pytest.MonkeyPatch, response: Any) -> list[Any]:  # noqa: ANN401
    """Replace the API call with a stub returning `response` and recording its args."""
    calls: list[Any] = []

    async def fake(*args: Any, **_: Any) -> Any:  # noqa: ANN401
        calls.append(args)
        return response

    monkeypatch.setattr(MvgApi, "_MvgApi__api", staticmethod(fake))
    return calls


def test_station_id_must_match_fully() -> None:
    """Test: trailing characters make a station id invalid."""
    assert MvgApi.valid_station_id("de:09162:70")
    assert not MvgApi.valid_station_id("de:09162:70garbage")


@pytest.mark.asyncio
async def test_departures_strip_id_and_tolerate_unknown_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test: station id is stripped and unknown transport types don't break parsing."""
    calls = stub_api(monkeypatch, [DEPARTURE])
    departures = await MvgApi.departures_async(" de:09162:70 ")
    assert calls[0][2]["globalId"] == "de:09162:70"
    assert departures[0]["type"] == "HOVERCRAFT"
    assert departures[0]["icon"] == "mdi:help-circle"


@pytest.mark.asyncio
async def test_nearby_async_defaults_to_single_station(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test: nearby_async returns a single station by default, like nearby."""
    stub_api(monkeypatch, [LOCATION, LOCATION])
    station = await MvgApi.nearby_async(48.1, 11.5)
    assert isinstance(station, dict)


def test_run_propagates_runtime_error() -> None:
    """Test: a RuntimeError raised by the coroutine itself is not swallowed by the loop fallback."""

    async def fail() -> None:
        msg = "boom"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="boom"):
        MvgApi._run(fail())  # noqa: SLF001

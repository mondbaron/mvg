"""Demonstration tests (see README.md)."""

import pytest

from mvg import MvgApi, TransportType


def test_basic() -> None:
    """Test: basic usage."""
    station = MvgApi.station("Universität, München")
    assert station["id"] == "de:09162:70"
    if station:
        mvgapi = MvgApi(station["id"])
        departures = mvgapi.departures()
        assert len(departures) > 0
        print("BASIC: ", station, departures, end="\n\n")


def test_faraway() -> None:
    """Test: usage with distant station."""
    station = MvgApi.station("Ebersberg, Ebersberg (Obb.)")
    assert station["id"] == "de:09175:4070"
    if station:
        mvgapi = MvgApi(station["id"])
        departures = mvgapi.departures()
        assert len(departures) > 0
        print("BASIC: ", station, departures, end="\n\n")


def test_village() -> None:
    """Test: usage with village station."""
    station = MvgApi.station("Egmating, Schule")
    assert station["id"] == "de:09175:4212"
    if station:
        mvgapi = MvgApi(station["id"])
        departures = mvgapi.departures()
        assert len(departures) > 0
        print("BASIC: ", station, departures, end="\n\n")


def test_nearby() -> None:
    """Test: station by coordinates."""
    station = MvgApi.nearby(48.1, 11.5)
    assert station["id"] == "de:09162:1480"
    print("NEARBY: ", station, end="\n\n")


def test_nearby_list() -> None:
    """Test: station list by coordinates."""
    stations = MvgApi.nearby(48.1, 11.5, True)
    assert isinstance(stations, list)
    assert len(stations) > 0
    assert stations[0]["id"] == "de:09162:1480"
    print("NEARBY: ", stations, end="\n\n")


def test_filter() -> None:
    """Test: filters."""
    station = MvgApi.station("Universität, München")
    assert station["id"] == "de:09162:70"
    if station:
        mvgapi = MvgApi(station["id"])
        departures = mvgapi.departures(
            limit=3,
            offset=5,
            transport_types=[TransportType.UBAHN],
        )
        assert len(departures) > 0
        print("FILTER: ", station, departures, end="\n\n")


@pytest.mark.asyncio
async def test_async() -> None:
    """Test: advanced usage with asynchronous methods."""
    station = await MvgApi.station_async("Universität, München")
    assert station["id"] == "de:09162:70"
    if station:
        departures = await MvgApi.departures_async(station["id"])
        assert len(departures) > 0
        print("ASYNC: ", station, departures, end="\n\n")


@pytest.mark.asyncio
async def test_station_sync_in_running_loop_real_query() -> None:
    """Call the synchronous `station()` from an active event loop.

    This reproduces the Jupyter/notebook scenario where `asyncio.run` would
    fail and verifies the library's fallback runs the query using the
    background loop.
    """
    station = MvgApi.station("Universität, München")
    assert station is not None
    assert station["id"] == "de:09162:70"

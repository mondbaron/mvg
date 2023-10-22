"""Demonstration tests (see README.md)"""

import pytest

from mvg import MvgApi, TransportType


def test_basic() -> None:
    """Test: basic usage"""
    station = MvgApi.station("Universität, München")
    assert station["id"] == "de:09162:70"
    if station:
        mvgapi = MvgApi(station["id"])
        departures = mvgapi.departures()
        assert len(departures) > 0
        print("BASIC: ", station, departures, end="\n\n")


def test_faraway() -> None:
    """Test: basic usage"""
    station = MvgApi.station("Ebersberg, Ebersberg (Obb.)")
    assert station["id"] == "de:09175:4070"
    if station:
        mvgapi = MvgApi(station["id"])
        departures = mvgapi.departures()
        assert len(departures) > 0
        print("BASIC: ", station, departures, end="\n\n")


def test_village() -> None:
    """Test: basic usage"""
    station = MvgApi.station("Egmating, Schule")
    assert station["id"] == "de:09175:4212"
    if station:
        mvgapi = MvgApi(station["id"])
        departures = mvgapi.departures()
        assert len(departures) > 0
        print("BASIC: ", station, departures, end="\n\n")


def test_nearby() -> None:
    """Test: station by coordinates"""
    station = MvgApi.nearby(48.1, 11.5)
    assert station["id"] == "de:09162:1480"
    print("NEARBY: ", station, end="\n\n")


def test_nearby_multi() -> None:
    """Test: stations list by coordinates"""
    stations = MvgApi.nearby_multi(48.1, 11.5)
    assert stations[0]["id"] == "de:09162:1480"
    assert isinstance(stations, list)
    assert len(stations) > 1
    print("NEARBY MULTI: ", stations, end="\n\n")


def test_nearby_multi_limit() -> None:
    """Test: stations list by coordinates with limit"""
    stations = MvgApi.nearby_multi(48.1, 11.5, limit=3)
    assert stations[0]["id"] == "de:09162:1480"
    assert isinstance(stations, list)
    assert len(stations) == 3
    print("NEARBY MULTI: ", stations, end="\n\n")


def test_nearby_multi_limit_negative() -> None:
    """Test: stations list by coordinates with limit infinite"""
    stations = MvgApi.nearby_multi(48.1, 11.5, limit=-1)
    assert stations[0]["id"] == "de:09162:1480"
    assert isinstance(stations, list)
    assert len(stations) > 0
    print("NEARBY MULTI: ", stations, end="\n\n")


def test_nearby_by_type_default_all() -> None:
    """Test: station by coordinates and transport types (all)."""
    lat = 48.137
    lon = 11.575
    station_types_none = MvgApi.nearby(lat, lon)
    station_types_all = MvgApi.nearby(lat, lon, TransportType.all())
    assert station_types_none["id"] == "de:09162:2"
    assert station_types_none["id"] == station_types_all["id"]
    print("NEARBY: ", station_types_none, end="\n\n")


def test_nearby_by_type_() -> None:
    """Test: station by coordinates and transport types (leading to returning non-first entry in stations)."""
    station = MvgApi.nearby(48.137, 11.575, [TransportType.TRAM])
    assert station["id"] == "de:09162:20"
    print("NEARBY: ", station, end="\n\n")


def test_filter() -> None:
    """Test: filters"""
    station = MvgApi.station("Universität, München")
    assert station["id"] == "de:09162:70"
    if station:
        mvgapi = MvgApi(station["id"])
        departures = mvgapi.departures(limit=3, offset=5, transport_types=[TransportType.UBAHN])
        assert len(departures) > 0
        print("FILTER: ", station, departures, end="\n\n")


@pytest.mark.asyncio
async def test_async() -> None:
    """Test: advanced usage with asynchronous methods"""
    station = await MvgApi.station_async("Universität, München")
    assert station["id"] == "de:09162:70"
    if station:
        departures = await MvgApi.departures_async(station["id"])
        assert len(departures) > 0
        print("ASYNC: ", station, departures, end="\n\n")

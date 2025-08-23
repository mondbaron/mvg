"""Provides the class MvgApi."""

from __future__ import annotations

import asyncio
import re
import threading
from enum import Enum
from http import HTTPStatus
from typing import Any, Coroutine, TypeVar

import aiohttp
from furl import furl

MVGAPI_DEFAULT_LIMIT = 10  # API defaults to 10, limits to 100

# Generic result type for _run
T = TypeVar("T")


class Base(Enum):
    """MVG APIs base URLs."""

    FIB = "https://www.mvg.de/api/bgw-pt/v3"
    ZDM = "https://www.mvg.de/.rest/zdm"


class Endpoint(Enum):
    """MVG API endpoints with URLs and arguments."""

    FIB_LOCATION = ("/locations", ["query"])
    FIB_NEARBY = ("/stations/nearby", ["latitude", "longitude"])
    FIB_DEPARTURE = ("/departures", ["globalId", "limit", "offsetInMinutes"])
    ZDM_STATION_IDS = ("/mvgStationGlobalIds", ...)
    ZDM_STATIONS = ("/stations", ...)
    ZDM_LINES = ("/lines", ...)


class TransportType(Enum):
    """MVG products defined by the API with name and icon."""

    BAHN = ("Bahn", "mdi:train")
    SBAHN = ("S-Bahn", "mdi:subway-variant")
    UBAHN = ("U-Bahn", "mdi:subway")
    TRAM = ("Tram", "mdi:tram")
    BUS = ("Bus", "mdi:bus")
    REGIONAL_BUS = ("Regionalbus", "mdi:bus")
    SEV = ("SEV", "mdi:taxi")
    SCHIFF = ("Schiff", "mdi:ferry")

    @classmethod
    def all(cls) -> list[TransportType]:
        """Return a list of all products."""
        return [getattr(TransportType, c.name) for c in cls if c.name != "SEV"]


class MvgApiError(Exception):
    """Failed communication with MVG API."""


class MvgApi:
    """A class interface to retrieve stations, lines and departures from the MVG.

    The implementation uses the Münchner Verkehrsgesellschaft (MVG) API at https://www.mvg.de.
    It can be instanciated by station name and place or global station id.

    :param station: global station id (e.g. 'de:09162:70')
    :raises MvgApiError: raised on communication failure or unexpected result
    :raises ValueError: raised on bad station id format
    """

    def __init__(self, station: str) -> None:
        """Initialize the MVG interface."""
        station = station.strip()
        if not self.valid_station_id(station):
            msg = "Invalid station."
            raise ValueError(msg)

        station_details = self.station(station)
        if station_details:
            self.station_id = station_details["id"]

    @staticmethod
    def valid_station_id(station_id: str, validate_existance: bool = False) -> bool:
        """Check if the station id is a global station ID according to VDV Recommendation 432.

        :param station_id: a global station id (e.g. 'de:09162:70')
        :param validate_existance: validate the existence in a list from the API
        :return: True if valid, False if Invalid
        """
        valid_format = bool(re.match("de:[0-9]{2,5}:[0-9]+", station_id))
        if not valid_format:
            return False

        if validate_existance:
            try:
                result = MvgApi._run(MvgApi.__api(Base.ZDM, Endpoint.ZDM_STATION_IDS))
                if not isinstance(result, list):
                    msg = f"Bad API call: Expected a list, but got {type(result)}."
                    raise MvgApiError(msg)
            except (AssertionError, KeyError) as exc:
                msg = "Bad API call: Could not parse station data."
                raise MvgApiError(msg) from exc
            else:
                return station_id in result

        return True

    @staticmethod
    async def __api(base: Base, endpoint: Endpoint | tuple[str, list[str]], args: dict[str, Any] | None = None) -> Any:  # noqa: ANN401
        """Call the API endpoint with the given arguments.

        :param base: the API base
        :param endpoint: the endpoint
        :param args: a dictionary containing arguments
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the response as JSON object
        """
        url = furl(base.value)
        url /= endpoint.value[0] if isinstance(endpoint, Endpoint) else endpoint[0]
        url.set(query_params=args)

        try:
            async with aiohttp.ClientSession(trust_env=True) as session, session.get(
                url.url,
            ) as resp:
                if resp.status != HTTPStatus.OK:
                    msg = f"Bad API call: Got response ({resp.status}) from {url.url}."
                    raise MvgApiError(msg)
                if resp.content_type != "application/json":
                    msg = f"Bad API call: Got content type {resp.content_type} from {url.url}."
                    raise MvgApiError(msg)
                return await resp.json()

        except aiohttp.ClientError as exc:
            msg = f"Bad API call: Got {type(exc)!s} from {url.url}"
            raise MvgApiError from exc

    @staticmethod
    async def station_ids_async() -> list[str]:
        """Retrieve a list of all valid station ids.

        :raises MvgApiError: raised on communication failure or unexpected result
        :return: station ids as a list
        """
        try:
            result = await MvgApi.__api(Base.ZDM, Endpoint.ZDM_STATION_IDS)
            if not isinstance(result, list):
                msg = f"Bad API call: Expected a list, but got {type(result)}."
                raise MvgApiError(msg)
            return sorted(result)
        except (AssertionError, KeyError) as exc:
            msg = "Bad API call: Could not parse station data."
            raise MvgApiError(msg) from exc

    @staticmethod
    async def stations_async() -> list[dict[str, Any]]:
        """Retrieve a list of all stations.

        :raises MvgApiError: raised on communication failure or unexpected result
        :return: a list of stations as dictionary
        """
        try:
            result = await MvgApi.__api(Base.ZDM, Endpoint.ZDM_STATIONS)
            if not isinstance(result, list):
                msg = f"Bad API call: Expected a list, but got {type(result)}."
                raise MvgApiError(msg)
        except (AssertionError, KeyError) as exc:
            msg = "Bad API call: Could not parse station data."
            raise MvgApiError(msg) from exc
        else:
            return result

    @staticmethod
    def stations() -> list[dict[str, Any]]:
        """Retrieve a list of all stations.

        :raises MvgApiError: raised on communication failure or unexpected result
        :return: a list of stations as dictionary
        """
        return MvgApi._run(MvgApi.stations_async())

    @staticmethod
    async def lines_async() -> list[dict[str, Any]]:
        """Retrieve a list of all lines.

        :raises MvgApiError: raised on communication failure or unexpected result
        :return: a list of lines as dictionary
        """
        try:
            result = await MvgApi.__api(Base.ZDM, Endpoint.ZDM_LINES)
            if not isinstance(result, list):
                msg = f"Bad API call: Expected a list, but got {type(result)}."
                raise MvgApiError(msg)
        except (AssertionError, KeyError) as exc:
            msg = "Bad API call: Could not parse station data."
            raise MvgApiError(msg) from exc
        else:
            return result

    @staticmethod
    def lines() -> list[dict[str, Any]]:
        """Retrieve a list of all lines.

        :raises MvgApiError: raised on communication failure or unexpected result
        :return: a list of lines as dictionary
        """
        return MvgApi._run(MvgApi.lines_async())

    @staticmethod
    async def station_async(query: str) -> dict[str, str] | None:
        """Find a station by station name and place or global station id.

        :param query: name, place ('Universität, München') or global station id (e.g. 'de:09162:70')
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the first matching station as dictionary with keys 'id', 'name', 'place', 'latitude', 'longitude'

        Example result::

            {
                "id": "de:09162:6",
                "name": "Hauptbahnhof",
                "place": "München",
                "latitude": 48.14003,
                "longitude": 11.56107,
            }
        """
        query = query.strip()
        try:
            # return details from ZDM if query is a station id
            if MvgApi.valid_station_id(query):
                stations_endpoint = Endpoint.ZDM_STATIONS.value[0]
                station_endpoint = f"{stations_endpoint}/{query}"
                result = await MvgApi.__api(Base.ZDM, (station_endpoint, []))
                if not isinstance(result, dict):
                    msg = f"Bad API call: Expected a dict, but got {type(result)}."
                    raise MvgApiError(msg)

                return {
                    "id": result["id"],
                    "name": result["name"],
                    "place": result["place"],
                    "latitude": result["latitude"],
                    "longitude": result["longitude"],
                }

            # use open search if query is not a station id
            args = dict.fromkeys(Endpoint.FIB_LOCATION.value[1])
            args.update({"query": query.strip(), "locationTypes": "STATION"})
            result = await MvgApi.__api(Base.FIB, Endpoint.FIB_LOCATION, args)
            if not isinstance(result, list):
                msg = f"Bad API call: Expected a list, but got {type(result)}."
                raise MvgApiError(msg)

            # return first location if lis is not empty
            if len(result) > 0:
                return {
                    "id": result[0]["globalId"],
                    "name": result[0]["name"],
                    "place": result[0]["place"],
                    "latitude": result[0]["latitude"],
                    "longitude": result[0]["longitude"],
                }

        except (AssertionError, KeyError) as exc:
            msg = "Bad API call: Could not parse station data."
            raise MvgApiError(msg) from exc
        else:
            # return None if no station was found
            return None

    @staticmethod
    def station(query: str) -> dict[str, str] | None:
        """Find a station by station name and place or global station id.

        :param query: name, place ('Universität, München') or global station id (e.g. 'de:09162:70')
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the fist matching station as dictionary with keys 'id', 'name', 'place', 'latitude', 'longitude'

        Example result::

            {
                "id": "de:09162:6",
                "name": "Hauptbahnhof",
                "place": "München",
                "latitude": 48.14003,
                "longitude": 11.56107,
            }
        """
        return MvgApi._run(MvgApi.station_async(query))

    @staticmethod
    async def nearby_async(
        latitude: float,
        longitude: float,
        full_list: bool = True,
    ) -> dict[str, str] | list[dict[str, str]] | None:
        """Find the nearest station by coordinates.

        :param latitude: coordinate in decimal degrees
        :param longitude: coordinate in decimal degrees
        :param full_list: return full list of stations instead of a single location
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the fist matching station as dictionary with keys 'id', 'name', 'place', 'latitude', 'longitude'
            or a list of such station dictionaries, if requested by `full_list` argument

        Example result::

            {"id": "de:09162:70", "name": "Universität", "place": "München", "latitude": 48.15007, "longitude": 11.581}
        """
        try:
            args = dict.fromkeys(Endpoint.FIB_NEARBY.value[1])
            args.update({"latitude": latitude, "longitude": longitude})
            result = await MvgApi.__api(Base.FIB, Endpoint.FIB_NEARBY, args)
            if not isinstance(result, list):
                msg = f"Bad API call: Expected a list, but got {type(result)}."
                raise MvgApiError(msg)

            if len(result) > 0:
                locations = [
                    {
                        "id": location["globalId"],
                        "name": location["name"],
                        "place": location["place"],
                        "latitude": location["latitude"],
                        "longitude": location["longitude"],
                    }
                    for location in result
                ]
                # return full list or only nearest location
                return locations if full_list else locations[0]

        except (AssertionError, KeyError) as exc:
            msg = "Bad API call: Could not parse station data."
            raise MvgApiError(msg) from exc
        else:
            # return None if no station was found
            return None

    @staticmethod
    def nearby(
        latitude: float,
        longitude: float,
        full_list: bool = False,
    ) -> dict[str, str] | list[dict[str, str]] | None:
        """Find the nearest station by coordinates.

        :param latitude: coordinate in decimal degrees
        :param longitude: coordinate in decimal degrees
        :param full_list: return full list of stations instead of a single location
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the fist matching station as dictionary with keys 'id', 'name', 'place', 'latitude', 'longitude'
            or a list of such station dictionaries, if requested by `full_list` argument

        Example result::

            {"id": "de:09162:70", "name": "Universität", "place": "München", "latitude": 48.15007, "longitude": 11.581}
        """
        return MvgApi._run(MvgApi.nearby_async(latitude, longitude, full_list))

    @staticmethod
    async def departures_async(
        station_id: str,
        limit: int = MVGAPI_DEFAULT_LIMIT,
        offset: int = 0,
        transport_types: list[TransportType] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve the next departures for a station by station id.

        :param station_id: the global station id ('de:09162:70')
        :param limit: limit of departures, defaults to 10
        :param offset: offset (e.g. walking distance to the station) in minutes, defaults to 0
        :param transport_types: filter by transport type, defaults to None
        :raises MvgApiError: raised on communication failure or unexpected result
        :raises ValueError: raised on bad station id format
        :return: a list of departures as dictionary

        Example result::

            [
                {
                    "time": 1668524580,
                    "planned": 1668524460,
                    "line": "U3",
                    "destination": "Fürstenried West",
                    "type": "U-Bahn",
                    "icon": "mdi:subway",
                    "cancelled": False,
                    "messages": [],
                },
                ...,
            ]
        """
        station_id.strip()
        if not MvgApi.valid_station_id(station_id):
            msg = "Invalid format of global station ID."
            raise ValueError(msg)

        try:
            args = dict.fromkeys(Endpoint.FIB_DEPARTURE.value[1])
            args.update({"globalId": station_id, "offsetInMinutes": offset, "limit": limit})
            if transport_types is None:
                transport_types = TransportType.all()
            args.update({"transportTypes": ",".join([product.name for product in transport_types])})
            result = await MvgApi.__api(Base.FIB, Endpoint.FIB_DEPARTURE, args)
            if not isinstance(result, list):
                msg = f"Bad API call: Expected a list, but got {type(result)}."
                raise MvgApiError(msg)

            departures = [
                {
                    "time": int(departure["realtimeDepartureTime"] / 1000),
                    "planned": int(departure["plannedDepartureTime"] / 1000),
                    "line": departure["label"],
                    "destination": departure["destination"],
                    "type": TransportType[departure["transportType"]].value[0],
                    "icon": TransportType[departure["transportType"]].value[1],
                    "cancelled": departure["cancelled"],
                    "messages": departure["messages"],
                }
                for departure in result
            ]

        except (AssertionError, KeyError) as exc:
            msg = "Bad MVG API call: Invalid departure data."
            raise MvgApiError(msg) from exc
        else:
            return departures

    def departures(
        self,
        limit: int = MVGAPI_DEFAULT_LIMIT,
        offset: int = 0,
        transport_types: list[TransportType] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve the next departures.

        :param limit: limit of departures, defaults to 10
        :param offset: offset (e.g. walking distance to the station) in minutes, defaults to 0
        :param transport_types: filter by transport type, defaults to None
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: a list of departures as dictionary

        Example result::

            [
                {
                    "time": 1668524580,
                    "planned": 1668524460,
                    "line": "U3",
                    "destination": "Fürstenried West",
                    "type": "U-Bahn",
                    "icon": "mdi:subway",
                    "cancelled": False,
                    "messages": [],
                },
                ...,
            ]

        """
        return MvgApi._run(self.departures_async(self.station_id, limit, offset, transport_types))

    # Single background loop/thread used when a running loop exists in this
    # thread (e.g. Jupyter). Created lazily on first use.
    _bg_lock = threading.Lock()
    _bg_loop: asyncio.AbstractEventLoop | None = None
    _bg_thread: threading.Thread | None = None

    @staticmethod
    def _run(coro: Coroutine[Any, Any, T]) -> T:
        """Execute a coroutine from synchronous code.

        - If no event loop is running in the current thread, this uses
          `asyncio.run(coro)` (the normal, fast path).
        - If an event loop is already running (e.g. inside Jupyter), it
          submits the coroutine to a single background event loop that is
          created once and reused for subsequent calls.

        The background loop approach avoids calling `asyncio.run()` from a
        running loop which raises RuntimeError.
        """
        try:
            return asyncio.run(coro)
        except RuntimeError:
            # Running inside an existing loop in this thread; fall back to
            # the background loop approach.
            if not asyncio.iscoroutine(coro):
                msg = "_run expects a coroutine object"
                raise TypeError(msg) from None

            with MvgApi._bg_lock:
                if MvgApi._bg_loop is None:
                    loop = asyncio.new_event_loop()

                    def _start_bg_loop() -> None:
                        asyncio.set_event_loop(loop)
                        loop.run_forever()

                    thread = threading.Thread(target=_start_bg_loop, daemon=True)
                    thread.start()
                    MvgApi._bg_loop = loop
                    MvgApi._bg_thread = thread

            if MvgApi._bg_loop is None:
                msg = "Failed to create background event loop"
                raise RuntimeError(msg) from None

            future = asyncio.run_coroutine_threadsafe(coro, MvgApi._bg_loop)
            return future.result()

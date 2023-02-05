"""
Provides the class MvgApi
"""

from __future__ import annotations

import asyncio
import re
from enum import Enum
from typing import Any

import aiohttp
from furl import furl

MVGAPI_DEFAULT_LIMIT = 10  # API defaults to 10, limits to 100


class Base(Enum):
    """MVG APIs base URLs"""
    FIB = "https://www.mvg.de/api/fib/v2"
    ZDM = "https://www.mvg.de/.rest/zdm"


class Endpoint(Enum):
    """MVG API endpoints with URLs and arguments"""
    FIB_LOCATION: tuple[str, list[str]] = ("/location", ["query"])
    FIB_NEARBY: tuple[str, list[str]] = ("/station/nearby", ["latitude", "longitude"])
    FIB_DEPARTURE: tuple[str, list[str]] = ("/departure", ["globalId", "limit", "offsetInMinutes"])
    ZDM_STATION_IDS: tuple[str, list[str]] = ("/mvgStationGlobalIds", [])
    ZDM_STATIONS: tuple[str, list[str]] = ("/stations", [])
    ZDM_LINES: tuple[str, list[str]] = ("/lines", [])


class TransportType(Enum):
    """MVG products defined by the API with name and icon."""
    BAHN: tuple[str, str] = ("Bahn", "mdi:train")
    SBAHN: tuple[str, str] = ("S-Bahn", "mdi:subway-variant")
    UBAHN: tuple[str, str] = ("U-Bahn", "mdi:subway")
    TRAM: tuple[str, str] = ("Tram", "mdi:tram")
    BUS: tuple[str, str] = ("Bus", "mdi:bus")
    REGIONAL_BUS: tuple[str, str] = ("Regionalbus", "mdi:bus")
    SEV: tuple[str, str] = ("SEV", "mdi:taxi")
    SHIFF: tuple[str, str] = ("Schiff", "mdi:ferry")


class MvgApiError(Exception):
    """Failed communication with MVG API."""


class MvgApi:
    """
    A class interface to retrieve stations, lines and departures
    from the Münchner Verkehrsgesellschaft (MVG) API at https://www.mvg.de.
    Can be instanciated by station name and place or global station id.

    :param name: name, place ('Universität, München') or global station id (e.g. 'de:09162:70')
    :raises MvgApiError: raised on communication failure or unexpected result
    :raises ValueError: raised on bad station id format
    """

    def __init__(self,
                 station: str
                 ) -> None:
        station = station.strip()
        if not self.valid_station_id(station, True):
            raise ValueError("Invalid station.")

        station_details = self.station(station)
        if station_details:
            self.station_id = station_details["id"]

    @staticmethod
    def valid_station_id(station_id: str, validate_existance: bool = False) -> bool:
        """
        Check if the station id is a global station ID according to VDV Recommendation 432.

        :param station_id: a global station id (e.g. 'de:09162:70')
        :param validate_existance: validate the existance in a list from the API
        :return: True if valid, False if Invalid
        """
        valid_format = bool(re.match("de:[0-9]{2,5}:[0-9]+", station_id))
        if not valid_format:
            return False

        if validate_existance:
            try:
                result = asyncio.run(MvgApi.__api(Base.ZDM, Endpoint.ZDM_STATION_IDS))
                assert isinstance(result, list)
                return station_id in result
            except (AssertionError, KeyError) as exc:
                raise MvgApiError("Bad API call: Could not parse station data") from exc

        return True

    @staticmethod
    async def __api(base: Base, endpoint: Endpoint, args: dict[str, Any] | None = None) -> Any:
        """
        Call the API endpoint with the given arguments.

        :param base: the API base
        :param endpoint: the endpoint
        :param args: a dictionary containing arguments
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the response as JSON object
        """
        url = furl(base.value)
        url /= endpoint.value[0]
        url.set(query_params=args)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url.url, ) as resp:
                    if resp.status != 200:
                        raise MvgApiError(
                            f"Bad API call: Got response ({resp.status}) from {url.url}")
                    if resp.content_type != "application/json":
                        raise MvgApiError(
                            f"Bad API call: Got content type {resp.content_type} from {url.url}")
                    return await resp.json()

        except aiohttp.ClientError as exc:
            raise MvgApiError(f"Bad API call: Got {str(type(exc))} from {url.url}") from exc

    @staticmethod
    async def station_ids_async() -> list[str]:
        """
        Retrieve a list of all valid station ids.

        :raises MvgApiError: raised on communication failure or unexpected result
        :return: station ids as a list
        """
        try:
            result = await MvgApi.__api(Base.ZDM, Endpoint.ZDM_STATION_IDS)
            assert isinstance(result, list)
            return sorted(result)
        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad API call: Could not parse station data") from exc

    @staticmethod
    async def stations_async() -> list[dict[str, Any]]:
        """
        Retrieve a list of all stations.

        :raises MvgApiError: raised on communication failure or unexpected result
        :return: a list of stations as dictionary
        """
        try:
            result = await MvgApi.__api(Base.ZDM, Endpoint.ZDM_STATIONS)
            assert isinstance(result, list)
            return result
        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad API call: Could not parse station data") from exc

    @staticmethod
    def stations() -> list[dict[str, Any]]:
        """
        Retrieve a list of all stations.

        :raises MvgApiError: raised on communication failure or unexpected result
        :return: a list of stations as dictionary
        """
        return asyncio.run(MvgApi.stations_async())

    @staticmethod
    async def lines_async() -> list[dict[str, Any]]:
        """
        Retrieve a list of all lines.

        :raises MvgApiError: raised on communication failure or unexpected result
        :return: a list of lines as dictionary
        """
        try:
            result = await MvgApi.__api(Base.ZDM, Endpoint.ZDM_LINES)
            assert isinstance(result, list)
            return result
        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad API call: Could not parse station data") from exc

    @staticmethod
    def lines() -> list[dict[str, Any]]:
        """
        Retrieve a list of all lines.

        :raises MvgApiError: raised on communication failure or unexpected result
        :return: a list of lines as dictionary
        """
        return asyncio.run(MvgApi.stations_async())

    @staticmethod
    async def station_async(query: str) -> dict[str, str] | None:
        """
        Find a station by station name and place or global station id.

        :param name: name, place ('Universität, München') or global station id (e.g. 'de:09162:70')
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the fist matching station as dictionary with keys 'id', 'name', 'place'

        Example result::

            { "id": "de:09162:70", "name": "Hauptbahnhof", "place": "München" }
        """
        query = query.strip()
        try:
            args = dict.fromkeys(Endpoint.FIB_LOCATION.value[1])
            args.update({"query": query.strip()})
            result = await MvgApi.__api(Base.FIB, Endpoint.FIB_LOCATION, args)
            assert isinstance(result, list)

            # return None if result is empty
            if len(result) == 0:
                return None

            # return name and place from first result if station id was provided
            if MvgApi.valid_station_id(query):
                station = {
                    "id": query.strip(),
                    "name": result[0]["name"],
                    "place": result[0]["place"],
                }
                return station

            # return first location of type "STATION" if name was provided
            for location in result:
                if location["type"] == "STATION":
                    station = {
                        "id": location["globalId"],
                        "name": location["name"],
                        "place": location["place"],
                    }
                    return station

            # return None if no station was found
            return None

        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad API call: Could not parse station data") from exc

    @staticmethod
    def station(query: str) -> dict[str, str] | None:
        """
        Find a station by station name and place or global station id.

        :param name: name, place ('Universität, München') or global station id (e.g. 'de:09162:70')
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the fist matching station as dictionary with keys 'id', 'name', 'place'

        Example result::

            { 'id': 'de:09162:70', 'name': 'Universität', 'place': 'München' }
        """
        return asyncio.run(MvgApi.station_async(query))

    @staticmethod
    async def nearby_async(latitude: float, longitude: float) -> dict[str, str] | None:
        """
        Find the nearest station by coordinates.

        :param latitude: coordinate in decimal degrees
        :param longitude: coordinate in decimal degrees
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the fist matching station as dictionary with keys 'id', 'name', 'place'

        Example result::

            { 'id': 'de:09162:70', 'name': 'Universität', 'place': 'München' }
        """
        try:
            args = dict.fromkeys(Endpoint.FIB_NEARBY.value[1])
            args.update({"latitude": latitude, "longitude": longitude})
            result = await MvgApi.__api(Base.FIB, Endpoint.FIB_NEARBY, args)
            assert isinstance(result, list)

            # return first location of type "STATION"
            for location in result:
                station = {
                    "id": location["globalId"],
                    "name": location["name"],
                    "place": location["place"],
                }
                return station

            # return None if no station was found
            return None

        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad API call: Could not parse station data") from exc

    @staticmethod
    def nearby(latitude: float, longitude: float) -> dict[str, str] | None:
        """
        Find the nearest station by coordinates.

        :param latitude: coordinate in decimal degrees
        :param longitude: coordinate in decimal degrees
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the fist matching station as dictionary with keys 'id', 'name', 'place'

        Example result::

            { 'id': 'de:09162:70', 'name': 'Universität', 'place': 'München' }
        """
        return asyncio.run(MvgApi.nearby_async(latitude, longitude))

    @staticmethod
    async def departures_async(station_id: str,
                               limit: int = MVGAPI_DEFAULT_LIMIT, offset: int = 0,
                               transport_types: list[TransportType] | None = None
                               ) -> list[dict[str, Any]]:
        """
        Retreive the next departures for a station by station id.

        :param station_id: the global station id ('de:09162:70')
        :param limit: limit of departures, defaults to 10
        :param offset: offset (e.g. walking distance to the station) in minutes, defaults to 0
        :param transport_types: filter by transport type, defaults to None
        :raises MvgApiError: raised on communication failure or unexpected result
        :raises ValueError: raised on bad station id format
        :return: a list of departures as dictionary

        Example result::

            [{
                'time': 1668524580,
                'planned': 1668524460,
                'line': 'U3',
                'destination': 'Fürstenried West',
                'type': 'U-Bahn',
                'icon': 'mdi:subway',
                'cancelled': False,
                'messages': []
            }, ... ]
        """
        station_id.strip()
        if not MvgApi.valid_station_id(station_id):
            raise ValueError("Invalid format of global staton id.")

        try:
            args = dict.fromkeys(Endpoint.FIB_LOCATION.value[1])
            args.update({"globalId": station_id,
                         "offsetInMinutes": offset,
                         "limit": limit})
            if transport_types:
                args.update({
                    "transportTypes": ",".join([product.name for product in transport_types])})
            result = await MvgApi.__api(Base.FIB, Endpoint.FIB_DEPARTURE, args)
            assert isinstance(result, list)

            departures: list[dict[str, Any]] = []
            for departure in result:
                departures.append(
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
                )
            return departures

        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad MVG API call: Invalid departure data") from exc

    def departures(self,
                   limit: int = MVGAPI_DEFAULT_LIMIT,
                   offset: int = 0,
                   transport_types: list[TransportType] | None = None) -> list[dict[str, Any]]:
        """
        Retreive the next departures.

        :param limit: limit of departures, defaults to 10
        :param offset: offset (e.g. walking distance to the station) in minutes, defaults to 0
        :param transport_types: filter by transport type, defaults to None
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: a list of departures as dictionary

        Example result::
            
            [{
                'time': 1668524580,
                'planned': 1668524460,
                'line': 'U3',
                'destination': 'Fürstenried West',
                'type': 'U-Bahn',
                'icon': 'mdi:subway',
                'cancelled': False,
                'messages': []
            }, ... ]
            
        """
        return asyncio.run(self.departures_async(self.station_id, limit, offset, transport_types))

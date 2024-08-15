"""Provides the class MvgApi."""

from __future__ import annotations

import asyncio
import re
from enum import Enum
from typing import Any

import aiohttp
from furl import furl

MVGAPI_DEFAULT_LIMIT = 100  # API defaults to 10, limits to 100


class Base(Enum):
    """MVG APIs base URLs."""

    FIB = "https://mvg.de/api/fib/v3"
    ZDM = "https://www.mvg.de/.rest/zdm"


class Endpoint(Enum):
    """MVG API endpoints with URLs and arguments."""

    FIB_LOCATION: tuple[str, list[str]] = ("/location", ["query"])
    FIB_NEARBY: tuple[str, list[str]] = ("/station/nearby", ["latitude", "longitude"])
    FIB_DEPARTURE: tuple[str, list[str]] = ("/departure", ["globalId", "limit", "offsetInMinutes"])
    ZDM_STATION_IDS: tuple[str, list[str]] = ("/mvgStationGlobalIds", [])
    ZDM_STATIONS: tuple[str, list[str]] = ("/stations", [])
    ZDM_LINES: tuple[str, list[str]] = ("/lines", [])


class Occupancy(Enum):
    """MVG API occupancy level"""
    UNKNOWN: tuple[int, str] = (0, "UNKNOWN")
    LOW: tuple[int, str] = (1, "LOW")
    MEDIUM: tuple[int, str] = (2, "MEDIUM")
    HIGH: tuple[int, str] = (3, "HIGH")


class TransportType(Enum):
    """MVG products defined by the API with name and icon."""

    BAHN: tuple[str, str, str] = ("BAHN", "mdi:train", "#cc0000")
    SBAHN: tuple[str, str, str] = ("SBAHN", "mdi:subway-variant", "#4c9045")
    UBAHN: tuple[str, str, str] = ("UBAHN", "mdi:subway", "#0064b0")
    TRAM: tuple[str, str, str] = ("TRAM", "mdi:tram", "#e40a0b")
    BUS: tuple[str, str, str] = ("BUS", "mdi:bus", "#00586a")
    REGIONAL_BUS: tuple[str, str, str] = ("REGIONAL_BUS", "mdi:bus", "#00586a")
    SEV: tuple[str, str, str] = ("SEV", "mdi:taxi", "#00586a")
    SCHIFF: tuple[str, str, str] = ("SCHIFF", "mdi:ferry", "#00586a")

    @classmethod
    def all(cls) -> list[TransportType]:
        """Return a list of all products."""
        return [getattr(TransportType, c.name) for c in cls if c.name != "SEV"]

class Color:

    @staticmethod
    def background_foreground_colors(transport_type: TransportType, line: str) -> tuple:
        # default to type background color and white foreground
        bg = transport_type.value[2]
        fg = "#ffffff"

        sbahn_line_bg_color_map = {
            "S1": "#17beea",
            "S2": "#76b82a",
            "S3": "#951b81",
            "S4": "#e30613",
            "S5": "#0094c5",
            "S6": "#00975f",
            "S7": "#943126",
            "S8": "#000000",
        }
        sbahn_line_fg_color_map = {
            "S8": "#ffcc00"
        }
        
        if transport_type == TransportType.SBAHN:
            bg = sbahn_line_bg_color_map.get(line, bg)
            fg = sbahn_line_fg_color_map.get(line, fg)

        ubahn_line_bg_color_map = {
            "U1": "#549e00",
            "U2": "#db0000",
            "U3": "#f58600",
            "U4": "#00d1b2",
            "U5": "#d17a08",
            "U6": "#007cc4",
            "U7": "#000000",
            "U8": "#000000"
        }

        if transport_type == TransportType.UBAHN:
            bg = ubahn_line_bg_color_map.get(line, bg)
        
        return bg, fg

class MvgApiError(Exception):
    """Failed communication with MVG API."""


class MvgApi:
    """A class interface to retrieve stations, lines and departures from the MVG.

    The implementation uses the Münchner Verkehrsgesellschaft (MVG) API at https://www.mvg.de.
    It can be instanciated by station name and place or global station id.

    :param name: name, place ('Universität, München') or global station id (e.g. 'de:09162:70')
    :raises MvgApiError: raised on communication failure or unexpected result
    :raises ValueError: raised on bad station id format
    """

    def __init__(self, station: str) -> None:
        """Initialize the MVG interface."""
        station = station.strip()
        if not self.valid_station_id(station):
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
    async def __api(base: Base, endpoint: Endpoint, args: dict[str, Any] | None = None, url_id: str | None = None, ) -> Any:
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
        if url_id is not None:
            url /= url_id
        url.set(query_params=args)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url.url,
                ) as resp:
                    if resp.status != 200:
                        raise MvgApiError(f"Bad API call: Got response ({resp.status}) from {url.url}")
                    if resp.content_type != "application/json":
                        raise MvgApiError(f"Bad API call: Got content type {resp.content_type} from {url.url}")
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
        return asyncio.run(MvgApi.lines_async())
    
    @staticmethod
    async def station_multi_async(query: str) -> list[dict[str, str]]:
        """
        Find stations by station name and place.

        :param name: name, place ('Universität, München')
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the list of matching stations as dictionary with keys 'id', 'name', 'place', 'latitude', 'longitude'

        Example result::

            [{'id': 'de:09162:6', 'name': 'Hauptbahnhof', 'place': 'München',
                'latitude': 48.14003, 'longitude': 11.56107}]
        """
        query = query.strip()
        try:
            args = dict.fromkeys(Endpoint.FIB_LOCATION.value[1])
            args.update({"query": query.strip()})
            result = await MvgApi.__api(Base.FIB, Endpoint.FIB_LOCATION, args)
            assert isinstance(result, list)

            if len(result) == 0:
                return []

            # return first location of type "STATION" if name was provided
            stations = [
                {
                    "id": location["globalId"],
                    "name": location["name"],
                    "place": location["place"],
                    "latitude": result[0]["latitude"],
                    "longitude": result[0]["longitude"],
                    "products": location["transportTypes"],
                }
                for location in result
                if location["type"] == "STATION"
            ]

            return stations

        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad API call: Could not parse station data") from exc

    @staticmethod
    async def station_async(query: str) -> dict[str, str] | None:
        """
        Find a station by station name and place or global station id.

        :param name: name, place ('Universität, München') or global station id (e.g. 'de:09162:70')
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the first matching station as dictionary with keys 'id', 'name', 'place', 'latitude', 'longitude'

        Example result::

            {'id': 'de:09162:6', 'name': 'Hauptbahnhof', 'place': 'München',
                'latitude': 48.14003, 'longitude': 11.56107}
        """
        stations = await MvgApi.station_multi_async(
            query=query
        )

        if not stations:
            return None

        return stations[0]

    @staticmethod
    def station(query: str) -> dict[str, str] | None:
        """
        Find a station by station name and place or global station id.

        :param name: name, place ('Universität, München') or global station id (e.g. 'de:09162:70')
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the first matching station as dictionary with keys 'id', 'name', 'place', 'latitude', 'longitude'

        Example result::

            {'id': 'de:09162:6', 'name': 'Hauptbahnhof', 'place': 'München',
                'latitude': 48.14003, 'longitude': 11.56107}
        """
        return asyncio.run(MvgApi.station_async(query))
    
    @staticmethod
    async def station_get_async(station_id: str) -> dict[str, str] | None:
        """
        Get a station by station id.

        :param station_id: global station id (e.g. 'de:09162:70')
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the first matching station as dictionary with keys 'id', 'name', 'place', 'latitude', 'longitude'

        Example result::

            {'id': 'de:09162:6', 'name': 'Hauptbahnhof', 'place': 'München',
                'latitude': 48.14003, 'longitude': 11.56107}
        """
        try:
            result = await MvgApi.__api(Base.ZDM, Endpoint.ZDM_STATIONS, url_id=station_id)
            assert isinstance(result, dict)
            return result
        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad API call: Could not parse station data") from exc

    @staticmethod
    async def nearby_async(
        latitude: float,
        longitude: float,
        transport_types: list[TransportType] | None = None,
    ) -> dict[str, str] | None:
        """
        Find the nearest station by coordinates.

        :param latitude: coordinate in decimal degrees
        :param longitude: coordinate in decimal degrees
        :param transport_types: filter by transport types, defaults to None (all types)
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the first matching station as dictionary with keys 'id', 'name', 'place', 'latitude', 'longitude'

        Example result::

            {
                'id': 'de:09162:1480',
                'name': 'Forstenrieder Allee',
                'place': 'München',
                'latitude': 48.0951,
                'longitude': 11.49937,
                'types': ['U-Bahn', 'Bus']
            }
        """
        stations = await MvgApi.nearby_multi_async(
            latitude=latitude,
            longitude=longitude,
            transport_types=transport_types,
            limit=1,
        )

        if not stations:
            return None

        return stations[0]

    @staticmethod
    async def nearby_multi_async(
        latitude: float,
        longitude: float,
        transport_types: list[TransportType] | None = None,
        limit: int = -1,
    ) -> list[dict[str, str]]:
        """
        Find the nearest stations by coordinates.

        :param latitude: coordinate in decimal degrees
        :param longitude: coordinate in decimal degrees
        :param transport_types: filter by transport types, defaults to None (all types)
        :param limit: limit number of stations returned. set -1 for max.
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the list of nearby stations ordered by increasing distance as list of dictionary
                    with keys 'id', 'name', 'place', 'latitude', 'longitude'

        Example result::

            [{
                'id': 'de:09162:1480',
                'name': 'Forstenrieder Allee',
                'place': 'München',
                'latitude': 48.0951,
                'longitude': 11.49937,
                'types': ['U-Bahn', 'Bus']
            },
            {
                'id': 'de:09162:1409',
                'name': 'Limmatstraße',
                'place': 'München',
                'latitude': 48.0951,
                'longitude': 11.49937,
                'types': ['Bus']
            }, ...]
        """
        try:
            args = dict.fromkeys(Endpoint.FIB_NEARBY.value[1])
            args.update({"latitude": latitude, "longitude": longitude})
            result = await MvgApi.__api(Base.FIB, Endpoint.FIB_NEARBY, args)
            assert isinstance(result, list)

            if transport_types is None:
                transport_types = TransportType.all()

            query_transport_types = [t.name for t in transport_types]

            # return locations of type "STATION"
            return_stations = []
            for location in result:
                location_transport_types = location["transportTypes"]

                if any([query_type in location_transport_types for query_type in query_transport_types]):
                    station = {
                        "id": location["globalId"],
                        "name": location["name"],
                        "place": location["place"],
                        "latitude": result[0]["latitude"],
                        "longitude": result[0]["longitude"],
                        "types": [TransportType[t].value[0] for t in location_transport_types]
                    }
                    return_stations.append(station)

            # limit results
            if limit < 0:
                # if limit is negative, return all available results
                return return_stations

            return return_stations[:limit]

        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad API call: Could not parse station data") from exc

    @staticmethod
    def nearby(
        latitude: float,
        longitude: float,
        transport_types: list[TransportType] | None = None,
    ) -> dict[str, str] | None:
        """
        Find the nearest station by coordinates.

        :param latitude: coordinate in decimal degrees
        :param longitude: coordinate in decimal degrees
        :param transport_types: filter by transport types, defaults to None (all types)
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the first matching station as dictionary with keys 'id', 'name', 'place', 'latitude', 'longitude'

        Example result::

            {
                'id': 'de:09162:1480',
                'name': 'Forstenrieder Allee',
                'place': 'München',
                'latitude': 48.0951,
                'longitude': 11.49937,
                'types': ['U-Bahn', 'Bus']
            }
        """
        return asyncio.run(MvgApi.nearby_async(latitude, longitude, transport_types))

    @staticmethod
    def nearby_multi(
        latitude: float,
        longitude: float,
        transport_types: list[TransportType] | None = None,
        limit: int = -1
    ) -> list[dict[str, str]]:
        """
        Find the nearest station by coordinates.

        :param latitude: coordinate in decimal degrees
        :param longitude: coordinate in decimal degrees
        :param transport_types: filter by transport types, defaults to None (all types)
        :param limit: limit number of stations returned. set -1 for max.
        :raises MvgApiError: raised on communication failure or unexpected result
        :return: the list of nearby stations ordered by increasing distance as list of dictionary
                     with keys 'id', 'name', 'place', 'latitude', 'longitude', 'types'

        Example result::

            [{
                'id': 'de:09162:1480',
                'name': 'Forstenrieder Allee',
                'place': 'München',
                'latitude': 48.0951,
                'longitude': 11.49937,
                'types': ['U-Bahn', 'Bus']
            },
            {
                'id': 'de:09162:1409',
                'name': 'Limmatstraße',
                'place': 'München',
                'latitude': 48.0951,
                'longitude': 11.49937,
                'types': ['Bus']
            }, ...]
        """
        return asyncio.run(MvgApi.nearby_multi_async(latitude, longitude, transport_types, limit))

    @staticmethod
    async def departures_async(
        station_id: str,
        limit: int = MVGAPI_DEFAULT_LIMIT,
        offset: int = 0,
        transport_types: list[TransportType] | None = None,
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
            args.update({"globalId": station_id, "offsetInMinutes": offset, "limit": limit})
            if transport_types is None:
                transport_types = TransportType.all()
            args.update({"transportTypes": ",".join([product.name for product in transport_types])})
            result = await MvgApi.__api(Base.FIB, Endpoint.FIB_DEPARTURE, args)
            assert isinstance(result, list)

            departures: list[dict[str, Any]] = []
            for departure in result:
                # bg, fg = Color.background_foreground_colors(TransportType[departure.get("transportType", "")], departure.get("label", "?"))
                departures.append(
                    {
                        "realtimeDepartureTime": int(departure.get("realtimeDepartureTime", 0) / 1000),
                        "plannedDepartureTime": int(departure.get("plannedDepartureTime", 0) / 1000),
                        "delay": int(departure.get("delayInMinutes", 0)),
                        "realtime": departure.get("realtime", False),
                        "transportType": TransportType[departure.get("transportType", "")].value[0],
                        "line": departure.get("label", "?").strip(),
                        "destination": departure.get("destination", "?"),
                        "icon": TransportType[departure.get("transportType", "")].value[1],
                        "platform": departure.get("platform"),
                        "stopPositionNumber": departure.get("stopPositionNumber"),
                        "stopPointGlobalId": departure.get("stopPointGlobalId", ""),
                        "messages": departure.get("messages", []),
                        "occupancy": Occupancy[departure.get("occupancy", "UNKNOWN")].value[1],
                        "cancelled": departure.get("cancelled", False),
                        "sev": departure.get("sev", False),
                        "platformChanged": departure.get("platformChanged", False),
                    }
                )
            return departures

        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad MVG API call: Invalid departure data") from exc

    def departures(
        self, limit: int = MVGAPI_DEFAULT_LIMIT, offset: int = 0, transport_types: list[TransportType] | None = None
    ) -> list[dict[str, Any]]:
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

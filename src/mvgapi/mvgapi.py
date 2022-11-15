"""
Provides the class MvgApi to retrieve stations, lines, destinations and departures
from the latest Münchner Verkehrsgesellschaft (MVG) API at https://www.mvg.de.
"""


from __future__ import annotations

import asyncio
import re
from enum import Enum
from typing import Any

import aiohttp
from furl import furl

MVGAPI_URL = "https://www.mvg.de/api/fib/v1"
MVGAPI_DEPARTURES_LIMIT = 50  # API defaults to 10, limits to 100


class MvgApiEndpoint(Enum):
    """MVG API endpoints with URLs and arguments"""
    LOCATION = ("/location", ["query"])
    NEARBY = ("/nearby", ["latitude", "longitude"])
    DEPARTURE = ("/departure", ["globalId", "limit", "offsetInMinutes"])


class MvgApiTransportType(Enum):
    """MVG products defined by the API with name and icon."""
    BAHN = ("Bahn", "mdi:train")
    SBAHN = ("S-Bahn", "mdi:subway-variant")
    UBAHN = ("U-Bahn", "mdi:subway")
    TRAM = ("Tram", "mdi:tram")
    BUS = ("Bus", "mdi:bus")
    REGIONAL_BUS = ("Regionalbus", "mdi:bus")
    SEV = ("SEV", "mdi:taxi")
    SHIFF = ("Schiff", "mdi:ferry")


class MvgApiError(Exception):
    """Failed communication with MVG API."""


class MvgApi:
    """
    An interface class to the MVG API.

    Basic Usage:

    ```
    station = MvgApi.station('Universität, München')
    if station:
        mvgapi = MvgApi(station['id'])
        lines = mvgapi.lines()
        destinations = mvgapi.destinations()
        departures = mvgapi.departures()
        print(station, lines, destinations, departures)
    ```

    Asynchronous Usage:

    ```
    async def demo():
        station = await MvgApi.station_async('Universität, München')
        if station:
            lines = await MvgApi.lines_async(station['id'])
            destinations = await MvgApi.destinations_async(station['id'])
            departures = await MvgApi.departures_async(station['id'])
            print(station, lines, destinations, departures)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(demo())
    ```
    """

    def __init__(self,
                 station: str
                 ) -> None:
        self.loop = asyncio.get_event_loop()
        result = self.loop.run_until_complete(self.station_async(station))
        if result is None:
            raise ValueError("Invalid station.")
        self.station_id = result["id"]
        """
        Create an instance of the MvgApi by station name and place or global station id.

        :param name: name, place ('Universität, München') or global station id (e.g. 'de:09162:70')
        :raises MvgApiError: raised on communication failure or unexpected result
        :raises ValueError: raised on bad station id format
        """

    @staticmethod
    def is_global_station_id(station_id: str) -> bool:
        """
        Check if the station id is a global station ID according to VDV Recommendation 432.

        :param station_id: a global station id (e.g. 'de:09162:70')
        :return: True if valid, False if Invalid
        """
        return bool(re.match("de:[0-9]{2,5}:[0-9]+", station_id))

    @staticmethod
    async def api(endpoint: MvgApiEndpoint, args: dict[str, Any] | None = None) -> Any:
        """
        Call the API endpoint with the given arguments.

        :param endpoint: the endpoint (LOCATION, NEARBY, DEPARTURE)
        :param args: a dictionary containing arguments (query, latitude, longitude, id, footway)
        :return: the response as JSON object
        :raises MvgApiError: raised on communication failure or unexpected result
        """
        url = furl(MVGAPI_URL)
        url /= endpoint.value[0]
        url.set(query_params=args)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url.url) as resp:
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
    async def station_async(query: str) -> dict[str, str] | None:
        """
        Find a station by station name and place or global station id.

        :param name: name, place ('Universität, München') or global station id (e.g. 'de:09162:70')
        :return: the fist matching station as dictionary with keys 'id', 'name', 'place'
        :raises MvgApiError: raised on communication failure or unexpected result

        Example result:

            { "id": "de:09162:70", "name": "Hauptbahnhof", "place": "München" }
        """
        try:
            args = dict.fromkeys(MvgApiEndpoint.LOCATION.value[1])
            args.update({"query": query.strip()})
            result = await MvgApi.api(MvgApiEndpoint.LOCATION, args)
            assert isinstance(result, list)

            # return None if result is empty
            if len(result) == 0:
                return None

            # return name and place from first result if station id was provided
            if MvgApi.is_global_station_id(query):
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
        :return: the fist matching station as dictionary with keys 'id', 'name', 'place'
        :raises MvgApiError: raised on communication failure or unexpected result

        Example result:

            { 'id': 'de:09162:70', 'name': 'Universität', 'place': 'München' }
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(MvgApi.station_async(query))

    @staticmethod
    async def nearby_async(latitude: float, longitude: float) -> dict[str, str] | None:
        """
        Find the nearest station by coordinates.

        :param latitude: coordinate in decimal degrees
        :param longitude: coordinate in decimal degrees
        :return: the fist matching station as dictionary with keys 'id', 'name', 'place'
        :raises MvgApiError: raised on communication failure or unexpected result

        Example result:

            { 'id': 'de:09162:70', 'name': 'Universität', 'place': 'München' }
        """
        try:
            args = dict.fromkeys(MvgApiEndpoint.LOCATION.value[1])
            args.update({"latitude": latitude, "longitude": longitude})
            result = await MvgApi.api(MvgApiEndpoint.NEARBY, args)
            assert isinstance(result, list)

            # return first location of type "STATION"
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
    def nearby(latitude: float, longitude: float) -> dict[str, str] | None:
        """
        Find the nearest station by coordinates.

        :param latitude: coordinate in decimal degrees
        :param longitude: coordinate in decimal degrees
        :return: the fist matching station as dictionary with keys 'id', 'name', 'place'
        :raises MvgApiError: raised on communication failure or unexpected result

        Example result:

            { 'id': 'de:09162:70', 'name': 'Universität', 'place': 'München' }
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(MvgApi.nearby_async(latitude, longitude))

    @staticmethod
    async def departures_async(
        station_id: str,
        limit: int = 10,
        offset: int = 0,
        lines: list[str] | None = None,
        destinations: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retreive the next departures for a station by station id.

        :param station_id: the global station id ('de:09162:70')
        :param limit: limit of departures, defaults to 10
        :param offset: offset (e.g. walking distance to the station) in minutes, defaults to 0
        :param lines: filter by a list of lines, defaults to None
        :param destinations: filter by a list if destinations, defaults to None
        :return: a list of departures as dictionary
        :raises MvgApiError: raised on communication failure or unexpected result
        :raises ValueError: raised on bad station id format

        Example result:

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
        if not MvgApi.is_global_station_id(station_id):
            raise ValueError("Invalid format of global staton id.")

        try:
            args = dict.fromkeys(MvgApiEndpoint.LOCATION.value[1])
            args.update({"globalId": station_id,
                         "offsetInMinutes": offset,
                         "limit": MVGAPI_DEPARTURES_LIMIT})
            result = await MvgApi.api(MvgApiEndpoint.DEPARTURE, args)
            assert isinstance(result, list)

            departures: list[dict[str, Any]] = []
            for departure in result:
                if all([
                    lines is None or (departure["label"] in lines),
                    destinations is None or (departure["destination"] in destinations),
                    limit == 0 or len(departures) < limit,
                ]):
                    departures.append(
                        {
                            "time": int(departure["realtimeDepartureTime"] / 1000),
                            "planned": int(departure["plannedDepartureTime"] / 1000),
                            "line": departure["label"],
                            "destination": departure["destination"],
                            "type": MvgApiTransportType[departure["transportType"]].value[0],
                            "icon": MvgApiTransportType[departure["transportType"]].value[1],
                            "cancelled": departure["cancelled"],
                            "messages": departure["messages"],
                        }
                    )
            return departures

        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad MVG API call: Invalid departure data") from exc

    def departures(
        self,
        limit: int = 10,
        offset: int = 0,
        lines: list[str] | None = None,
        destinations: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retreive the next departures.

        :param limit: limit of departures, defaults to 10
        :param offset: offset (e.g. walking distance to the station) in minutes, defaults to 0
        :param lines: filter by a list of lines, defaults to None
        :param destinations: filter by a list if destinations, defaults to None
        :return: a list of departures as dictionary
        :raises MvgApiError: raised on communication failure or unexpected result

        Example result:

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
        return self.loop.run_until_complete(
            self.departures_async(self.station_id, limit, offset, lines, destinations))

    @staticmethod
    async def lines_async(station_id: str) -> list[str]:
        """
        Retrieve the serving lines for a station by station id.

        :param station_id: the global station id ('de:09162:70')
        :return: line names as list
        :raises MvgApiError: raised on communication failure or unexpected result
        :raises ValueError: raised on bad station id format

        Example result:

            [ '153', '154', '58', '68', 'U3', 'U6' ]
        """
        if not MvgApi.is_global_station_id(station_id):
            raise ValueError("Invalid format of global staton id.")

        try:
            args = dict.fromkeys(MvgApiEndpoint.LOCATION.value[1])
            args.update({"globalId": station_id, "limit": MVGAPI_DEPARTURES_LIMIT})
            result = await MvgApi.api(MvgApiEndpoint.DEPARTURE, args)
            assert isinstance(result, list)

            lines: list[str] = []
            for departure in result:
                lines.append(departure["label"])
            return sorted(set(lines))

        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad MVG API call: Invalid departure data") from exc

    def lines(self) -> list[str]:
        """
        Retrieve the serving lines.

        :return: line names as list
        :raises MvgApiError: raised on communication failure or unexpected result
        :raises ValueError: raised on bad station id format

        Example result:

            [ '153', '154', '58', '68', 'U3', 'U6' ]
        """
        return self.loop.run_until_complete(self.lines_async(self.station_id))

    @staticmethod
    async def destinations_async(station_id: str) -> list[str]:
        """
        Retrieve the final destinations for a station by given station id.

        :param station_id: the unique station id ('de:09162:70')
        :return: final destinations as list
        :raises MvgApiError: raised on communication failure or unexpected result
        :raises ValueError: raised on bad station id format

        Example result:

            ['Fröttmaning', 'Fürstenried West', 'Garching, Forschungszentrum', ...]
        """
        if not MvgApi.is_global_station_id(station_id):
            raise ValueError("Invalid format of global staton id.")

        try:
            args = dict.fromkeys(MvgApiEndpoint.LOCATION.value[1])
            args.update({"globalId": station_id, "limit": MVGAPI_DEPARTURES_LIMIT})
            result = await MvgApi.api(MvgApiEndpoint.DEPARTURE, args)
            assert isinstance(result, list)

            destinations: list[str] = []
            for departure in result:
                destinations.append(departure["destination"])
            return sorted(set(destinations))

        except (AssertionError, KeyError) as exc:
            raise MvgApiError("Bad MVG API call: Invalid departure data") from exc

    def destinations(self) -> list[str]:
        """
        Retrieve the final destinations.

        :return: final destinations as list
        :raises MvgApiError: raised on communication failure or unexpected result
        :raises ValueError: raised on bad station id format

        Example result:

            ['Fröttmaning', 'Fürstenried West', 'Garching, Forschungszentrum', ...]
        """
        return self.loop.run_until_complete(self.destinations_async(self.station_id))

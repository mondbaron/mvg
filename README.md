# mvgapi

This package aims to provide a clean, performant and barrier-free interface to timetable information of the *Münchner Verkehrsgesellschaft* (MVG), responsible for public transport in Munich. It exports the class `MvgApi` to retrieve stations, lines, destinations and departures from the unofficial JSON API at https://www.mvg.de.

## Disclaimer

This project is **not an official project from the *Münchner Verkehrsgesellschaft* (MVG)**. It was developed as private project from lack of a documented and openly accessible API. It simply reproduces the requests made by https://www.mvg.de to provide a barrier-free access to local timetable information.

Therefore, the following **usage restrictions from the [MVG Imprint](https://www.mvg.de/impressum.html) do apply to all users of this package**:

> Our systems are used for direct customer interaction. The processing of our content or data by third parties requires our express consent. For **private, non-commercial purposes, moderate use is tolerated** without our explicit consent. Any form of **data mining does not constitute moderate use**. We reserve the right to revoke this permission in principle or in individual cases. Please direct any questions to: redaktion@mvg.de
> 
> (*MVG Imprint, available at https://www.mvg.de/impressum.html, accessed on 15. Nov 2022*)

## Why another MVG API package?

The project was inspired by two existing packages:
- The package [`PyMVGLive`](https://pypi.org/project/PyMVGLive) from 2017 does provide an interface to the former MVGLive API at `mvg-live.de`. As of 2022 the MVGLive website does not exist anymore and the package has been archived. Although the old API still works for some stations, it does not for others - mainly due to updated station identifiers. Therefore, the package is considered deprecated and cannot be used for new designs.
- The newer package [`mvg-api`](https://pypi.org/project/mvg-api) offers an implementation from 2020 based on the API at `www.mvg.de/api/fahrinfo`. It considers the updated station identifiers and still works perfectly. This package provides the basis for recent projects such as [`mvg-cli`](https://pypi.org/project/mvg-cli).

So why another MVG API package? In the end three reasons were decisive:
- The recent website at uses a new API at `www.mvg.de/api/fib/v1`, which seems to be more performant than the previous one.
- None of the existing packages offer asynchronous calls for concurrent code projects.
- An optimized package was required to develop a [Home Assistant](https://www.home-assistant.io) integration.

## Basic Usage

The interface was designed to be simple and intuitive. Basic usage follows these steps:
- Find a station using `MvgApi.station(station)` by its name and place (e.g. `"Universität, München"`) or its global station identifier (e.g. `"de:09162:70"`).
- Alternatively, `MvgApi.nearby(latitude, longitude)` finds the nearest station.
- Create an API instance using `MvgApi(station)` by station name and place or its global identifier.
- Use the methods `.lines()`, `.destinations()` and `.departures()` to retrieve information from the API.

A basic example looks like this:

```python
from mvgapi import MvgApi

station = MvgApi.station('Universität, München')
if station:
    mvgapi = MvgApi(station['id'])
    lines = mvgapi.lines()
    destinations = mvgapi.destinations()
    departures = mvgapi.departures()
    print(station, lines, destinations, departures)
```

### Filters

The results from `.departures(limit, offset, lines, destination)` can be filtered using the following arguments:

- `limit` limits the output to the given number of departures, defaults to 10
- `offset` adds an offset (e.g. walking distance to the station) in minutes, defaults to 0
- `lines` filters the result by a list of lines (e.g. `["U3", "U6"]`)
- `destinations` filters the result by a list of final destinations (e.g. `["Münchner Freiheit", "Olympiazentrum"]`)

### Example results

`station()` results a `dict`:
```
{ 
'id': 'de:09162:70', 
'name': 'Universität', 
'place': 'München'
}
```
`lines()` results a `list`:
```
[ '153', '154', '58', '68', 'U3', 'U6' ]
```
`destinations()` results a `list`:
```
[ 'Fröttmaning', 'Fürstenried West', 'Garching, Forschungszentrum', ... ]
```
`departures()` results a `list` of `dict`:
```
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
```

## Advanced Usage: Asynchronous Methods

The class `MvgApi` internally calls asynchronous methods using `asyncio` and `aiohttp` to perform the web requests efficiently. These asynchronous methods are marked by the suffix `_async` and can be utilized by users in projects with concurrent code.

The basic example but with asynchronous calls looks like this:

```python
from mvgapi import MvgApi

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

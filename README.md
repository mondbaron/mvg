# Changelog medlor

My Home-Assistant addon needs an updated MVG API.
This munich_transport_trip modification can be used to lookup trips instead of departures. 
munich_transport_trip and munich_transport can use my modified MVG API (compatible).

```
1. munich_transport_trip
   https://github.com/medlor/mvg
   https://github.com/medlor/home-assistant-munich-transport
   Follow setup as described in Readme. Because we overwrite the MVG package, we need to login
   to docker then manually issue (only needed in case original MVG package has already been installed):
   $ pip uninstall mvg
   $ pip install git+https://github.com/medlor/mvg@main
   Use Icongito Window to see changes in the Lovelace cards immediately.
```
## config/configuration.yaml
```
sensor:
  - platform: munich_transport_trip
    departures:
      - name: "Giesing nach Frankfurter Ring"
        departure_station: "de:09162:1110"  #"Fasanenpark (b M..nchen)"
        destination_station: "de:09162:750" # Frankfurter Ring
        walking_time: 6
```

## Setup HA automations to trigger a refresh when you need it:
```
alias: "MVG: Update Trip to Frankfurter Ring"
description: ""
trigger:
  - platform: time_pattern
    minutes: /1
condition:
  - condition: time
    after: "07:00:00"
    before: "08:30:00"
    weekday:
      - mon
      - tue
      - wed
      - thu
      - fri
action:
  - service: homeassistant.update_entity
    metadata: {}
    data: {}
    target:
      entity_id:
        - sensor.giesing_nach_frankfurter_ring
mode: single
```

--------------------------

# mvg

This package aims to provide a clean, performant and barrier-free interface to timetable information of the *Münchner Verkehrsgesellschaft* (MVG), responsible for public transport in Munich. It exports the class `MvgApi` to retrieve stations, lines and departures from the unofficial JSON API at https://www.mvg.de.

## Disclaimer

This project is **not an official project from the Münchner Verkehrsgesellschaft (MVG)**. It was developed as a private project from lack of a documented and openly accessible API. It simply reproduces the requests made by https://www.mvg.de to provide a barrier-free access to local timetable information.

Therefore, the following **usage restrictions from the MVG Imprint do apply to all users of this package**:

> Our systems are used for direct customer interaction. The processing of our content or data by third parties requires our express consent. For **private, non-commercial purposes, moderate use is tolerated** without our explicit consent. Any form of **data mining does not constitute moderate use**. We reserve the right to revoke this permission in principle or in individual cases. Please direct any questions to: redaktion@mvg.de
> 
> (from https://www.mvg.de/impressum.html, accessed on 04. Feb 2023)

## Why another MVG package?

The project was inspired by two existing packages:
- The package [PyMVGLive](https://pypi.org/project/PyMVGLive) from 2017 does provide an interface to the former MVGLive API at `mvg-live.de`. As of 2022 the MVGLive website does not exist anymore and the package has been archived. Although the old API still works for some stations, it does not for others - mainly due to updated station identifiers. Therefore, the package is considered deprecated and cannot be used for new designs.
- The newer package [mvg-api](https://pypi.org/project/mvg-api) offers an implementation from 2020 based on the API at `www.mvg.de/api/fahrinfo`. It considers the updated station identifiers and still works perfectly. This package provides the basis for recent projects such as [mvg-cli](https://pypi.org/project/mvg-cli).

So why another MVG API package? In the end three reasons were decisive:
- The recent website at uses a new API at `www.mvg.de/api/fib/v2`, which seems to be more performant than the previous one.
- None of the existing packages offer asynchronous calls for concurrent code projects.
- An optimized package was required to develop a [Home Assistant](https://www.home-assistant.io) integration.

## Installation

Install from the Python Package Index (PyPI) using `pip`:
```
pip install mvg
```

## Basic Usage

The interface was designed to be simple and intuitive. Basic usage follows these steps:
- Find a station using `MvgApi.station(station)` by its name and place (e.g. `"Universität, München"`) or its global station identifier (e.g. `"de:09162:70"`).
- Alternatively, `MvgApi.nearby(latitude, longitude)` finds the nearest station.
- Create an API instance using `MvgApi(station)` by station name and place or its global identifier.
- Use the method `.departures()` to retrieve information from the API.

A basic example looks like this:

```python
from mvg import MvgApi

station = MvgApi.station('Universität, München')
if station:
    mvgapi = MvgApi(station['id'])
    departures = mvgapi.departures()
    print(station, departures)
```

### Available Stations and Lines

The static methods `MvgApi.stations()` and `MvgApi.lines()` expose a list of all available stations and a list of all available lines from designated API endpoints. While these calls are great for reference, they are also quite extensive and should not be used within a frequent query loop.

### Filters

The results from `.departures(limit, offset, transport_types)` can be filtered using the following arguments:

- `limit` limits the output to the given number of departures, defaults to 10
- `offset` adds an offset (e.g. walking distance to the station) in minutes, defaults to 0
- `transport_types` filters the result by a list of transport types (e.g. `[TransportType.UBAHN]`)

A filtered example looks like this:

```python
from mvg import MvgApi, TransportType

station = MvgApi.station('Universität, München')
if station:
    mvgapi = MvgApi(station['id'])
    departures = mvgapi.departures(
        limit=3,
        offset=5,
        transport_types=[TransportType.UBAHN])
    print(station, departures)
```

### Example results

`station()` or `nearby()` results a `dict`:
```
{ 
'id': 'de:09162:70', 
'name': 'Universität', 
'place': 'München'
'latitude': 48.15007, 
'longitude': 11.581
}
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
import asyncio
from mvg import MvgApi

async def demo() -> None:
    station = await MvgApi.station_async('Universität, München')
    if station:
        departures = MvgApi.departures_async(station['id'])
        print(station, await departures)
loop = asyncio.get_event_loop()
loop.run_until_complete(demo())
```

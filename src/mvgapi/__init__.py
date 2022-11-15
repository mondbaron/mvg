"""
An unofficial interface to timetable information of the Münchner Verkehrsgesellschaft (MVG).
"""

from .mvgapi import MvgApi, MvgApiEndpoint, MvgApiError, MvgApiTransportType

__all__ = ["MvgApi", "MvgApiEndpoint", "MvgApiError", "MvgApiTransportType"]

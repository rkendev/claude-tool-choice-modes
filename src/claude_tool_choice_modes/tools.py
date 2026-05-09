"""Two demo tools with deliberately differentiated descriptions.

Both return mocked dict lookups — no HTTP, no external services. The
"Do NOT use for X" anti-instructions in each ``description`` are the
CCA-F D2 disambiguation pattern the showcase exists to demonstrate:
when ``tool_choice="auto"``, description quality is what routes Claude
to the right tool.
"""

from __future__ import annotations

from typing import Any, cast

CITY_DATA: dict[str, dict[str, int | str]] = {
    "Tokyo": {"population": 14094034, "country": "Japan"},
    "New York": {"population": 8336817, "country": "United States"},
    "Amsterdam": {"population": 921402, "country": "Netherlands"},
    "São Paulo": {"population": 12325232, "country": "Brazil"},
}


def get_city_population(city: str) -> int:
    """Return the most recent census population estimate for a major city."""
    if city not in CITY_DATA:
        raise ValueError(f"unknown city: {city}")
    return cast(int, CITY_DATA[city]["population"])


def get_city_country(city: str) -> str:
    """Return the country a major city is located in."""
    if city not in CITY_DATA:
        raise ValueError(f"unknown city: {city}")
    return cast(str, CITY_DATA[city]["country"])


POPULATION_TOOL: dict[str, Any] = {
    "name": "get_city_population",
    "description": (
        "Return the most recent census population estimate for a major "
        "city as an integer. Use this when the user asks how many people "
        "live in a city or how big a city is. Do NOT use for non-population "
        "facts such as country, area, or timezone."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "The city name, e.g. 'Tokyo'."},
        },
        "required": ["city"],
        "additionalProperties": False,
    },
}

COUNTRY_TOOL: dict[str, Any] = {
    "name": "get_city_country",
    "description": (
        "Return the country a major city is located in as a string. Use "
        "this when the user asks which country a city is in. Do NOT use "
        "for population, area, or other non-country facts."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "The city name, e.g. 'Tokyo'."},
        },
        "required": ["city"],
        "additionalProperties": False,
    },
}

ALL_TOOLS: list[dict[str, Any]] = [POPULATION_TOOL, COUNTRY_TOOL]

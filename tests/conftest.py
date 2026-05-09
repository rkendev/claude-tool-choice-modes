"""Project-scoped pytest configuration.

Hosts the ``vcr_config`` fixture so every cassette in the suite shares
one redaction policy. Multiple test modules will record cassettes
(``tests/unit/test_showcase.py`` is the first), so project scope is
cleaner than per-module duplication.
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Redact auth headers from any VCR cassette this project records."""
    return {
        "filter_headers": [
            ("authorization", "REDACTED"),
            ("x-api-key", "REDACTED"),
        ],
    }

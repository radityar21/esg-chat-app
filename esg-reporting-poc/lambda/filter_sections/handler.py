"""
=============================================================================
Lambda: FilterSectionsFn
=============================================================================
Purpose:
    Filters Map state output to include only INCLUDED/INCLUDED_WITH_WARNINGS
    sections. Required because Step Functions does not support JSONPath filter
    expressions like [?(@.status=='INCLUDED')].

Input:
    {"sections": [{...status: "INCLUDED"...}, {...status: "EXCLUDED"...}, ...]}

Output:
    {"included": [...only sections with status INCLUDED or INCLUDED_WITH_WARNINGS...],
     "excluded_count": 1,
     "total_count": 4}

Deployment:
    Runtime: Python 3.11, Memory: 128 MB, Timeout: 10s
=============================================================================
"""

from __future__ import annotations
from typing import Any


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Filter generated sections to only those that passed validation.

    Args:
        event: Dict with "sections" list from Map state output.
        context: Lambda context.

    Returns:
        Dict with "included" list and counts.
    """
    sections = event.get("sections", [])

    included = [
        s for s in sections
        if s.get("status") in ("INCLUDED", "INCLUDED_WITH_WARNINGS")
    ]

    return {
        "included": included,
        "excluded_count": len(sections) - len(included),
        "total_count": len(sections),
        "included_count": len(included),
    }

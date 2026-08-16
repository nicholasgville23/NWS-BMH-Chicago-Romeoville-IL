print("@/bmh/implementation_registry.py module loaded included.")

"""
Implementation registry for the KLOT_BMH WNG689 BMH station.

The workstation launcher resolves runtime behaviors through this registry
and dispatches them via bmh.runtime_dispatch.invoke().
"""

from datetime import datetime, timezone


def poll_zones(context=None):
    """Poll forecast zone configuration for the WNG689 listening area.

    The listening counties are NW Indiana (Porter, Lake, LaPorte, Jasper)
    and NE Illinois. For now this returns a static snapshot; a future
    version may fetch zone boundaries from api.weather.gov.
    """
    context = context or {}
    zones = [
        {"zone": "INZ002", "county": "Porter", "state": "IN"},
        {"zone": "INZ001", "county": "Lake", "state": "IN"},
        {"zone": "INZ003", "county": "LaPorte", "state": "IN"},
        {"zone": "INZ004", "county": "Jasper", "state": "IN"},
        {"zone": "ILZ001", "county": "Cook", "state": "IL"},
    ]
    return {
        "station": "WNG689",
        "polled_at": datetime.now(timezone.utc).isoformat(),
        "zones": zones,
        "count": len(zones),
    }


def poll_alerts(context=None):
    """Poll for active alerts in the WNG689 listening area."""
    context = context or {}
    return {
        "station": "WNG689",
        "polled_at": datetime.now(timezone.utc).isoformat(),
        "alerts": [],
    }


# Canonical registry. Keys are looked up by the launcher and passed to
# bmh.runtime_dispatch.invoke().
IMPLEMENTATIONS = {
    "poll_zones": poll_zones,
    "poll_alerts": poll_alerts,
}

# Backward-compatible alias for the (misspelled) name used by older
# launcher scripts, e.g. `from bmh.implementation_registry import IMPLEMETATIONS`.
IMPLEMETATIONS = IMPLEMENTATIONS

__all__ = ["IMPLEMENTATIONS", "IMPLEMETATIONS", "poll_zones", "poll_alerts"]

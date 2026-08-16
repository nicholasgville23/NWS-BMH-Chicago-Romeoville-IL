print("Runtime Dispatch for the KLOT_BMH WNG689 BMH Station in Hebron, or Valparaiso, IN, or Indiana.")

"""
Runtime dispatch for the KLOT_BMH WNG689 BMH station.

The dispatch layer exposes the single entry point used by the workstation
launcher (WNG689_BMH.py):

    invoke(handler, context)

The first argument is either a callable implementation (as resolved from
bmh.implementation_registry.IMPLEMENTATIONS) or a registry key string.
The context is the caller's globals() dict, passed through to the handler.
"""

from bmh.implementation_registry import IMPLEMENTATIONS


def invoke(handler, context=None):
    """Invoke a registered BMH implementation.

    Args:
        handler (callable or str): The implementation to run, or a key into
            bmh.implementation_registry.IMPLEMENTATIONS.
        context (dict, optional): Caller context (globals()) passed to the
            handler. Defaults to an empty dict.

    Returns:
        The handler's return value.

    Raises:
        KeyError: If ``handler`` is a string not present in IMPLEMENTATIONS.
        TypeError: If ``handler`` is neither callable nor a registered key.
    """
    if isinstance(handler, str):
        if handler not in IMPLEMENTATIONS:
            raise KeyError(
                "Unknown BMH implementation: %r. Available: %s"
                % (handler, sorted(IMPLEMENTATIONS))
            )
        handler = IMPLEMENTATIONS[handler]

    if not callable(handler):
        raise TypeError("BMH handler %r is not callable" % (handler,))

    return handler(context or {})

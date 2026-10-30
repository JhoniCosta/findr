"""Builds icon descriptors in the serialization format of ``Gio.Icon.to_string()``.

Keeping icons as strings lets providers stay GTK-free while the UI resolves
them with ``Gio.Icon.new_for_string``.
"""


def themed_icon(*names: str) -> str:
    """A themed icon with fallbacks, e.g. ``themed_icon("image-png", "image-x-generic")``."""
    if not names:
        raise ValueError("at least one icon name is required")
    if len(names) == 1:
        return names[0]
    return ". GThemedIcon " + " ".join(names)


def icon_for_mime_type(mime_type: str | None) -> str:
    if not mime_type:
        return themed_icon("text-x-generic")
    media, _, _ = mime_type.partition("/")
    specific = mime_type.replace("/", "-")
    return themed_icon(specific, f"{media}-x-generic", "text-x-generic")

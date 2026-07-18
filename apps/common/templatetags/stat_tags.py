"""Template filters for presenting platform statistics on public pages."""

from django import template

register = template.Library()


def _trim(number: float) -> str:
    """Render a float without a trailing ``.0`` (e.g. ``15.0`` -> ``15``)."""
    text = f"{number:.1f}"
    if text.endswith(".0"):
        return text[:-2]
    return text


@register.filter(name="compact_count")
def compact_count(value):
    """Format an integer count into a compact, marketing-friendly label.

    Examples::

        950     -> "950"
        3500    -> "3.5k+"
        15000   -> "15k+"
        2500000 -> "2.5M+"
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        return value

    if number >= 1_000_000:
        return f"{_trim(number / 1_000_000)}M+"
    if number >= 1_000:
        return f"{_trim(number / 1_000)}k+"
    return str(number)


@register.filter(name="percent")
def percent(value):
    """Format a numeric percentage, dropping a redundant ``.0`` decimal."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    return f"{_trim(number)}%"

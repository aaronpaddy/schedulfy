"""
Shared helpers for course data: prerequisite parsing, day normalization,
and prerequisite checking.

These live outside app_ai.py so the API layer and the AI service can share one
definition of what a prerequisite list is and when two class days collide.
"""

import json

MAX_UNWRAP_DEPTH = 6

# Canonical weekday names, keyed by every spelling seen in imported catalogs.
_DAY_ALIASES = {
    'M': 'Monday', 'MO': 'Monday', 'MON': 'Monday', 'MONDAY': 'Monday',
    'T': 'Tuesday', 'TU': 'Tuesday', 'TUE': 'Tuesday', 'TUES': 'Tuesday',
    'TUESDAY': 'Tuesday',
    'W': 'Wednesday', 'WE': 'Wednesday', 'WED': 'Wednesday',
    'WEDNESDAY': 'Wednesday',
    'R': 'Thursday', 'TH': 'Thursday', 'THU': 'Thursday', 'THUR': 'Thursday',
    'THURS': 'Thursday', 'THURSDAY': 'Thursday',
    'F': 'Friday', 'FR': 'Friday', 'FRI': 'Friday', 'FRIDAY': 'Friday',
    'S': 'Saturday', 'SA': 'Saturday', 'SAT': 'Saturday', 'SATURDAY': 'Saturday',
    'U': 'Sunday', 'SU': 'Sunday', 'SUN': 'Sunday', 'SUNDAY': 'Sunday',
}

# Two-letter forms must be tried before single letters when expanding a compact
# string like "TTh", otherwise the 'T' in "Th" is read as Tuesday.
_DIGRAPHS = ('TH', 'TU', 'MO', 'WE', 'FR', 'SA', 'SU')


def canonical_code(code):
    """Normalize a course code for comparison: 'cs 101' and 'CS101' match."""
    if code is None:
        return ''
    return ''.join(str(code).split()).upper()


def parse_prerequisites(raw):
    """Parse a prerequisite value into a flat list of course codes.

    Tolerates the shapes that have accumulated in the catalog: a real list, a
    JSON string, a JSON string that was encoded twice by an export/import
    round-trip, or a bare comma-separated string.
    """
    return _flatten(raw, 0)


def _flatten(value, depth):
    if depth > MAX_UNWRAP_DEPTH or value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        out = []
        for item in value:
            out.extend(_flatten(item, depth + 1))
        return out

    if not isinstance(value, str):
        return [str(value)]

    text = value.strip()
    if not text or text in ('[]', 'null', 'None'):
        return []

    # A JSON payload that may itself contain another JSON payload.
    if text[0] in '["':
        try:
            return _flatten(json.loads(text), depth + 1)
        except (ValueError, TypeError):
            pass

    if ',' in text:
        return [part.strip() for part in text.split(',') if part.strip()]

    return [text]


def serialize_prerequisites(raw):
    """Return a clean JSON array string, safe to store or re-import."""
    seen, ordered = set(), []
    for code in parse_prerequisites(raw):
        key = canonical_code(code)
        if key and key not in seen:
            seen.add(key)
            ordered.append(code.strip() if isinstance(code, str) else code)
    return json.dumps(ordered)


def unmet_prerequisites(raw, completed):
    """Prerequisites from `raw` that are absent from the `completed` codes."""
    done = {canonical_code(c) for c in (completed or [])}
    missing, seen = [], set()
    for code in parse_prerequisites(raw):
        key = canonical_code(code)
        if key and key not in done and key not in seen:
            seen.add(key)
            missing.append(code)
    return missing


def normalize_days(day_value):
    """Expand a day string into a set of canonical weekday names.

    Handles 'Monday,Wednesday', 'MWF', 'TTh', 'mon/wed' and mixed casing, so
    two catalogs using different conventions still collide correctly.
    """
    if not day_value:
        return set()

    if isinstance(day_value, (list, tuple, set)):
        tokens = [str(d) for d in day_value]
    else:
        tokens = str(day_value).replace('/', ',').replace('|', ',').replace(';', ',').split(',')

    days = set()
    for token in tokens:
        for part in token.split():
            days.update(_expand_day_token(part))
    return days


def _expand_day_token(token):
    key = ''.join(ch for ch in token.upper() if ch.isalpha())
    if not key:
        return set()

    if key in _DAY_ALIASES:
        return {_DAY_ALIASES[key]}

    # Compact form such as 'MWF' or 'TTH': walk it, preferring digraphs.
    days, i = set(), 0
    while i < len(key):
        pair = key[i:i + 2]
        if pair in _DIGRAPHS:
            days.add(_DAY_ALIASES[pair])
            i += 2
            continue
        single = key[i]
        if single in _DAY_ALIASES:
            days.add(_DAY_ALIASES[single])
        i += 1
    return days


def parse_json_list(raw):
    """Parse a value that should be a JSON array, tolerating encoding damage.

    Accepts a real list, a JSON string, or a JSON string that was encoded twice
    by an export/import round-trip. Returns [] when nothing usable is found.
    """
    return _flatten_json(raw, 0)


def _flatten_json(value, depth):
    if depth > MAX_UNWRAP_DEPTH or value is None:
        return []

    if isinstance(value, (list, tuple)):
        # A single-element list wrapping a JSON string is the round-trip
        # damage; unwrap it rather than treating the string as an item.
        if len(value) == 1 and isinstance(value[0], str) and value[0].strip()[:1] in '[{':
            return _flatten_json(value[0], depth + 1)
        return [item for item in value if item not in (None, '')]

    if isinstance(value, dict):
        return [value]

    if not isinstance(value, str):
        return []

    text = value.strip()
    if not text or text in ('[]', 'null', 'None'):
        return []
    if text[0] not in '[{':
        return []

    try:
        return _flatten_json(json.loads(text), depth + 1)
    except (ValueError, TypeError):
        return []


def serialize_time_slots(raw):
    """Return a clean JSON array of time-slot objects, safe to re-import."""
    slots = [slot for slot in parse_json_list(raw) if isinstance(slot, dict)]
    return json.dumps(slots)


def serialize_tags(raw):
    """Return a clean JSON array of tag strings, safe to re-import."""
    tags, seen = [], set()
    for tag in parse_prerequisites(raw):   # same shapes: list of plain strings
        text = str(tag).strip()
        if text and text.lower() not in seen:
            seen.add(text.lower())
            tags.append(text)
    return json.dumps(tags)

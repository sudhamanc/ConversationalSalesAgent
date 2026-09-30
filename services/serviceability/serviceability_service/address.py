"""Address parsing, validation and normalization (deterministic, no I/O).

Moved from ``ServiceabilityAgent/serviceability_agent/tools/address_tools.py``.
"""

from __future__ import annotations

import logging
import re

from pydantic import ValidationError

from .models import Address, AddressValidationResult, NormalizedAddress, US_STATE_CODES, ZipCodeResult

logger = logging.getLogger("serviceability.address")

_ZIP_PATTERN = re.compile(r"\b\d{5}(-\d{4})?\b")
_STATE_PATTERN = re.compile(r"\b([A-Za-z]{2})\b")
_PO_BOX_PATTERN = re.compile(r"\b(P\.?\s?O\.?|POST\s+OFFICE)\s*BOX\b", re.IGNORECASE)
_INTERNATIONAL_PATTERN = re.compile(r"\b(UK|Canada|México|Mexico)\b", re.IGNORECASE)
_PREFIX_PATTERN = re.compile(
    r"^\s*(?:i\s+am\s+at|i'm\s+at|we\s+are\s+at|we're\s+at|at|address\s*:?)\s+", re.IGNORECASE
)
_NATURAL_PATTERN = re.compile(
    r"^\s*(?P<street>\d+\s+.+?)\s+(?P<city>[A-Za-z][A-Za-z .'-]+?)\s+"
    r"(?P<state>[A-Za-z]{2})\s+(?P<zip>\d{5})(?:-\d{4})?\s*$",
    re.IGNORECASE,
)

US_STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI",
    "wyoming": "WY", "district of columbia": "DC", "washington dc": "DC", "washington d.c.": "DC",
}
# A full state name counts only right before the trailing ZIP (same comma part). Longest names
# first so "west virginia" wins over "virginia".
_STATE_NAME_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in sorted(US_STATE_NAMES, key=len, reverse=True))
    + r")\s+\d{5}(?:-\d{4})?\s*$",
    re.IGNORECASE,
)

# USPS street suffixes (common forms and abbreviations), lower case, no dots.
STREET_SUFFIXES = frozenset({
    "st", "street", "ave", "av", "avenue", "rd", "road", "blvd", "boulevard", "dr", "drive",
    "ln", "lane", "way", "ct", "court", "pl", "place", "pkwy", "parkway", "hwy", "highway",
    "ter", "terrace", "cir", "circle", "sq", "square", "trl", "trail", "pike", "tpke",
    "turnpike", "expy", "expressway", "fwy", "freeway", "plz", "plaza", "aly", "alley",
    "row", "loop", "run", "walk", "xing", "crossing", "cv", "cove", "pt", "point",
})
_DIRECTIONALS = frozenset({"n", "s", "e", "w", "ne", "nw", "se", "sw"})
_UNIT_WORDS = frozenset({"suite", "ste", "apt", "apartment", "unit", "fl", "floor", "rm", "room", "bldg", "building"})
_TRAILING_ZIP = re.compile(r"^(?P<body>.+?)\s+(?P<zip>\d{5})(?:-\d{4})?\s*$")

PO_BOX_ERROR = "Physical address required for serviceability check. PO Boxes are not supported."
INTERNATIONAL_ERROR = "We currently only service addresses within the United States."
ZIP_ERROR = "Valid 5-digit ZIP code required. Format: Street, City, State ZIP"
STATE_ERROR = "Two-letter state code required (e.g., PA, CA, NY). Format: Street, City, State ZIP"
INCOMPLETE_ERROR = "Complete address required. Format: Street, City, State ZIP"
HOUSE_NUMBER_ERROR = "Street address must include a building/house number"


def _invalid(error: str) -> AddressValidationResult:
    return AddressValidationResult(valid=False, error=error)


def _state_from_text(text: str) -> str:
    """Last 2-letter US state code in the text, else a full state name before the ZIP, else ''."""
    for candidate in reversed(_STATE_PATTERN.findall(text)):
        if candidate.upper() in US_STATE_CODES:
            return candidate.upper()
    name = _STATE_NAME_PATTERN.search(text.rsplit(",", 1)[-1])
    return US_STATE_NAMES[name.group(1).lower()] if name else ""


def _norm_token(token: str) -> str:
    return token.lower().rstrip(".")


def _parse_commaless(text: str) -> tuple[str, str, str] | None:
    """Split ``<number> <street words> <suffix> [dir] [unit] <city words> <state> <zip>``.

    The street ends at the first street suffix (St, Ave, Rd, ...) that follows
    the house number and at least one name word, optionally followed by a
    directional (N, SW, ...) and a unit ("Suite 400", "#5"). The state is the
    2-letter code or full state name just before the ZIP. Returns
    ``(street, city, state_code)`` or ``None`` when the shape does not match.
    """
    match = _TRAILING_ZIP.match(text.replace(",", " "))
    if not match:
        return None
    tokens = match.group("body").split()

    state, state_len = "", 0
    if tokens and tokens[-1].upper() in US_STATE_CODES:
        state, state_len = tokens[-1].upper(), 1
    else:
        for n in (3, 2, 1):
            name = " ".join(tokens[-n:]).lower()
            if len(tokens) > n and name in US_STATE_NAMES:
                state, state_len = US_STATE_NAMES[name], n
                break
    if not state:
        return None
    rest = tokens[:-state_len]
    if len(rest) < 4 or not rest[0][0].isdigit():
        return None

    for i in range(2, len(rest) - 1):
        if _norm_token(rest[i]) not in STREET_SUFFIXES:
            continue
        end = i + 1
        if end < len(rest) - 1 and _norm_token(rest[end]) in _DIRECTIONALS:
            end += 1
        if end < len(rest) - 2 and _norm_token(rest[end]) in _UNIT_WORDS:
            end += 2
        elif end < len(rest) - 1 and rest[end].startswith("#") and len(rest[end]) > 1:
            end += 1
        if end < len(rest):
            return " ".join(rest[:end]), " ".join(rest[end:]), state
    return None


def validate_and_parse_address(address_string: str) -> AddressValidationResult:
    """Validate a raw address string and split it into street, city, state and ZIP.

    Rejects PO boxes and non-US addresses. Accepts comma-separated input
    ("123 Market St, Philadelphia, PA 19107") and comma-less natural input
    ("I am at 123 Main street philadelphia pa 19103" -> street "123 Main street",
    city "philadelphia"; the street ends at its suffix). The state may be a
    2-letter code or a full state name. Input case is preserved. Does not
    check coverage.
    """
    if _PO_BOX_PATTERN.search(address_string):
        logger.info("Address rejected: PO box")
        return _invalid(PO_BOX_ERROR)
    if _INTERNATIONAL_PATTERN.search(address_string):
        logger.info("Address rejected: international")
        return _invalid(INTERNATIONAL_ERROR)

    # Strip conversational prefixes ("I am at ...").
    cleaned = _PREFIX_PATTERN.sub("", address_string.strip())

    zip_match = _ZIP_PATTERN.search(cleaned)
    if not zip_match:
        return _invalid(ZIP_ERROR)

    state = _state_from_text(cleaned)
    if not state:
        return _invalid(STATE_ERROR)

    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    if len(parts) >= 3:
        street, city = parts[0], parts[1]
    else:
        # Comma-less (or partly comma-separated) input: split on the street
        # suffix first, fall back to the generic pattern.
        parsed = _parse_commaless(cleaned)
        if parsed:
            street, city, state = parsed
        else:
            natural = _NATURAL_PATTERN.match(cleaned)
            if not natural:
                return _invalid(INCOMPLETE_ERROR)
            street, city = natural.group("street").strip(), natural.group("city").strip()

    if not re.search(r"\d+", street):
        return _invalid(HOUSE_NUMBER_ERROR)

    try:
        address = Address(street=street, city=city, state=state, zip_code=zip_match.group()[:5])
    except ValidationError:
        return _invalid(INCOMPLETE_ERROR)
    logger.debug("Parsed address in ZIP %s", address.zip_code)
    return AddressValidationResult(valid=True, address=address)


def normalize_address(address: Address) -> NormalizedAddress:
    """Standard one-line form: title-cased street/city, upper-case state.

    ``123 market st, philadelphia, pa 19107`` -> ``123 Market St, Philadelphia, PA 19107``
    """
    return NormalizedAddress(
        normalized_address=f"{address.street.title()}, {address.city.title()}, "
        f"{address.state.upper()} {address.zip_code}"
    )


def extract_zip_code(address_string: str) -> ZipCodeResult:
    """First 5-digit ZIP code in the text (ZIP+4 truncated), or ``""``."""
    match = _ZIP_PATTERN.search(address_string)
    return ZipCodeResult(zip_code=match.group()[:5] if match else "")

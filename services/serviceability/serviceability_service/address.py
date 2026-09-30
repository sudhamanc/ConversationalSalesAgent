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

PO_BOX_ERROR = "Physical address required for serviceability check. PO Boxes are not supported."
INTERNATIONAL_ERROR = "We currently only service addresses within the United States."
ZIP_ERROR = "Valid 5-digit ZIP code required. Format: Street, City, State ZIP"
STATE_ERROR = "Two-letter state code required (e.g., PA, CA, NY). Format: Street, City, State ZIP"
INCOMPLETE_ERROR = "Complete address required. Format: Street, City, State ZIP"
HOUSE_NUMBER_ERROR = "Street address must include a building/house number"


def _invalid(error: str) -> AddressValidationResult:
    return AddressValidationResult(valid=False, error=error)


def validate_and_parse_address(address_string: str) -> AddressValidationResult:
    """Validate a raw address string and split it into street, city, state and ZIP.

    Rejects PO boxes and non-US addresses. Accepts comma-separated input
    ("123 Market St, Philadelphia, PA 19107") and natural input
    ("I am at 123 Main street philadelphia pa 19103"). Does not check coverage.
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

    state = ""
    for candidate in reversed(_STATE_PATTERN.findall(cleaned)):
        if candidate.upper() in US_STATE_CODES:
            state = candidate.upper()
            break
    if not state:
        return _invalid(STATE_ERROR)

    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    if len(parts) >= 3:
        street, city = parts[0], parts[1]
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

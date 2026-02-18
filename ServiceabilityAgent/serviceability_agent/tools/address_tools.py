"""
Address validation tools for the Serviceability Agent.

These tools handle address parsing, validation, and normalization.
"""

import re
from typing import Dict, Any
from ..utils.logger import get_logger

logger = get_logger(__name__)


def validate_and_parse_address(address_string: str) -> Dict[str, Any]:
    """
    Validates and parses a raw address string into structured components.
    
    This is a deterministic tool that validates address format and extracts
    components (street, city, state, ZIP). Does NOT check serviceability.
    
    Args:
        address_string: Raw address text from user input
        
    Returns:
        dict with 'valid' boolean and either 'address' dict or 'error' string
        
    Examples:
        >>> validate_and_parse_address("123 Market St, Philadelphia, PA 19107")
        {'valid': True, 'address': {'street': '123 Market St', 'city': 'Philadelphia', ...}}
        
        >>> validate_and_parse_address("PO Box 1234, Philly, PA 19107")
        {'valid': False, 'error': 'Physical address required for serviceability check...'}
    """
    logger.info(f"Parsing address: {address_string}")
    
    # Basic validation patterns
    us_zip_pattern = r'\b\d{5}(-\d{4})?\b'
    state_pattern = r'\b[A-Z]{2}\b'
    
    # Check for PO Box (not allowed)
    if re.search(r'\b(P\.?\s?O\.?|POST\s+OFFICE)\s*BOX\b', address_string, re.IGNORECASE):
        logger.warning("PO Box address rejected")
        return {
            "valid": False,
            "error": "Physical address required for serviceability check. PO Boxes are not supported."
        }
    
    # Check for international patterns (basic check)
    if re.search(r'\b(UK|Canada|México|Mexico)\b', address_string, re.IGNORECASE):
        logger.warning("International address detected")
        return {
            "valid": False,
            "error": "We currently only service addresses within the United States."
        }
    
    # Extract ZIP code
    zip_match = re.search(us_zip_pattern, address_string)
    if not zip_match:
        logger.warning("No valid ZIP code found")
        return {
            "valid": False,
            "error": "Valid 5-digit ZIP code required. Format: Street, City, State ZIP"
        }
    
    # Extract state (must be uppercase)
    state_match = re.search(state_pattern, address_string)
    if not state_match:
        logger.warning("No valid state code found")
        return {
            "valid": False,
            "error": "Two-letter state code required (e.g., PA, CA, NY). Format: Street, City, State ZIP"
        }
    
    # Split by comma to extract parts
    parts = [p.strip() for p in address_string.split(',')]
    if len(parts) < 3:
        logger.warning("Incomplete address format")
        return {
            "valid": False,
            "error": "Complete address required. Format: Street, City, State ZIP"
        }
    
    # Extract components
    street = parts[0]
    city = parts[1]
    
    # Last part should contain state and ZIP
    last_part = parts[-1]
    state = state_match.group()
    zip_code = zip_match.group().split('-')[0]  # Take only 5-digit portion
    
    # Validate street has numbers (actual address)
    if not re.search(r'\d+', street):
        logger.warning("Street address missing house number")
        return {
            "valid": False,
            "error": "Street address must include a building/house number"
        }
    
    logger.info(f"Successfully parsed address: {street}, {city}, {state} {zip_code}")
    
    return {
        "valid": True,
        "address": {
            "street": street,
            "city": city,
            "state": state,
            "zip_code": zip_code
        }
    }


def normalize_address(address: Dict[str, str]) -> str:
    """
    Normalizes an address dict to standard format for API calls.
    
    Args:
        address: Dict with street, city, state, zip_code keys
        
    Returns:
        Standardized address string
        
    Example:
        >>> normalize_address({
        ...     "street": "123 market st",
        ...     "city": "philadelphia",
        ...     "state": "PA",
        ...     "zip_code": "19107"
        ... })
        "123 Market St, Philadelphia, PA 19107"
    """
    # Title case for street and city
    street = address['street'].title()
    city = address['city'].title()
    state = address['state'].upper()
    zip_code = address['zip_code']
    
    normalized = f"{street}, {city}, {state} {zip_code}"
    logger.debug(f"Normalized address: {normalized}")
    
    return normalized


def extract_zip_code(address_string: str) -> str:
    """
    Quick utility to extract just the ZIP code from an address string.
    
    Args:
        address_string: Address text
        
    Returns:
        5-digit ZIP code or empty string if not found
    """
    us_zip_pattern = r'\b\d{5}(-\d{4})?\b'
    match = re.search(us_zip_pattern, address_string)
    if match:
        # Return only 5-digit portion
        return match.group().split('-')[0]
    return ""

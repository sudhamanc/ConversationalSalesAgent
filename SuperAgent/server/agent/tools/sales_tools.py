"""
Sales tools available to the Super Agent.

Each tool is a plain function that the ADK agent can invoke.
In production these would call real CRM / inventory / GIS APIs;
currently they return mock data for development.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


def check_service_availability(address: str) -> dict:
    """Check whether telecom services are available at a given address.

    Args:
        address: The street address to check for service availability.

    Returns:
        A dict with availability status and available service tiers.
    """
    logger.info(f"Checking service availability for: {address}")

    # Mock response – replace with real GIS / serviceability API
    return {
        "status": "available",
        "address": address,
        "available_services": [
            {"name": "Fiber Internet", "speeds": ["100 Mbps", "500 Mbps", "1 Gbps"], "available": True},
            {"name": "SD-WAN", "available": True},
            {"name": "Managed Wi-Fi", "available": True},
            {"name": "Voice (SIP Trunking)", "available": True},
        ],
        "estimated_install_days": 5,
    }


def get_product_catalog(category: str = "all") -> dict:
    """Retrieve the product catalog, optionally filtered by category.

    Args:
        category: Product category filter. Options: 'internet', 'voice',
                  'security', 'managed_services', or 'all'.

    Returns:
        A dict containing matching products with pricing.
    """
    logger.info(f"Fetching product catalog for category: {category}")

    catalog = {
        "internet": [
            {"name": "Business Fiber 100", "speed": "100 Mbps", "price": "$79/mo"},
            {"name": "Business Fiber 500", "speed": "500 Mbps", "price": "$149/mo"},
            {"name": "Business Fiber Gig", "speed": "1 Gbps", "price": "$249/mo"},
        ],
        "voice": [
            {"name": "SIP Trunking Basic", "channels": 5, "price": "$25/mo per channel"},
            {"name": "SIP Trunking Pro", "channels": 20, "price": "$20/mo per channel"},
        ],
        "security": [
            {"name": "DDoS Protection", "price": "$99/mo"},
            {"name": "Managed Firewall", "price": "$199/mo"},
        ],
        "managed_services": [
            {"name": "Managed Wi-Fi", "price": "$49/mo per AP"},
            {"name": "SD-WAN", "price": "$299/mo"},
        ],
    }

    if category == "all":
        return {"products": catalog}
    return {"products": {category: catalog.get(category, [])}}


def lookup_customer(identifier: str) -> dict:
    """Look up a customer by name, account number, or email.

    Args:
        identifier: Customer name, account number, or email address.

    Returns:
        A dict with customer details or a not-found message.
    """
    logger.info(f"Looking up customer: {identifier}")

    # Mock CRM lookup
    mock_customers = {
        "acme": {
            "name": "Acme Corp",
            "account_id": "ACME-001",
            "status": "active",
            "services": ["Fiber Internet 500 Mbps", "SIP Trunking Pro"],
            "contract_end": "2027-03-15",
        },
        "globex": {
            "name": "Globex Industries",
            "account_id": "GLX-042",
            "status": "active",
            "services": ["Fiber Internet 1 Gbps", "SD-WAN", "Managed Firewall"],
            "contract_end": "2026-11-30",
        },
    }

    key = identifier.lower().strip()
    for k, v in mock_customers.items():
        if k in key or v["account_id"].lower() in key:
            return {"found": True, "customer": v}

    return {"found": False, "message": f"No customer found matching '{identifier}'."}

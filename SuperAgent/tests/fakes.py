"""In-process stand-ins for the remote A2A agents (scripted models, no network)."""

from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

from sales_common.context import export_context_delta
from sales_common.testing import ScriptLlm
from super_agent.registry import AGENTS


def add_new_company(company_name: str, street: str, city: str, state: str, zip_code: str, tool_context: ToolContext,
                    contact_email: str = "") -> dict:
    """Register a company (``contact_email`` stands for a contact already on file)."""
    ctx = {"customer_id": "CUST-20260930-001", "company_name": company_name,
           "address": {"street": street, "city": city, "state": state, "zip_code": zip_code}}
    if contact_email:
        ctx["contact"] = {"name": "Jane", "email": contact_email}
    tool_context.state["customer_context"] = ctx
    return {"success": True, "customer_id": ctx["customer_id"], "company_name": company_name}


def check_service_availability(street: str, city: str, state: str, zip_code: str, tool_context: ToolContext) -> dict:
    """Check coverage."""
    tool_context.state["serviceability_context"] = {
        "is_serviceable": True, "service_address": {"zip_code": zip_code}, "available_products": ["FIB-1G"]}
    return {"serviceable": True, "zip_code": zip_code}


def schedule_installation(order_id: str, date: str, tool_context: ToolContext) -> dict:
    """Schedule an installation."""
    return {"success": True, "order_id": order_id, "appointment_id": "APT-1", "scheduled_date": date,
            "notification_queued": True, "notification_id": "NTF-FAKE-1"}


def generate_offer_quote(sku: str, tool_context: ToolContext) -> dict:
    """Quote."""
    tool_context.state["offer_context"] = {"offer_id": "OFF-1", "items": [{"product_id": sku}]}
    return {"offer_id": "OFF-1", "items": [{"product_id": sku, "final_price": 99.0}], "total_price": 99.0}


def process_payment(order_id: str, tool_context: ToolContext) -> dict:
    """Charge the order (publishes payment_context like the real tool)."""
    tool_context.state["payment_context"] = {"order_id": order_id, "status": "completed"}
    return {"success": True, "order_id": order_id, "status": "completed", "transaction_id": "TXN-1"}


#: Payment agent charging ORD-1.
PAYMENT_PAYS = ([{"call": "process_payment", "args": {"order_id": "ORD-1"}}, {"text": "Payment processed."}], [process_payment])

ADDRESS = {"company_name": "Crane.io", "street": "123 Main St", "city": "Philadelphia", "state": "PA", "zip_code": "19103"}

SCRIPTS = {
    "discovery_agent": ([{"call": "add_new_company", "args": {**ADDRESS, "contact_email": "jane@crane.io"}}, {"text": "Welcome Crane.io! Let me check service availability."}], [add_new_company]),
    "serviceability_agent": ([{"call": "check_service_availability", "args": {k: ADDRESS[k] for k in ("street", "city", "state", "zip_code")}}, {"text": "This location is serviceable with Fiber."}], [check_service_availability]),
    "service_fulfillment_agent": ([{"call": "schedule_installation", "args": {"order_id": "ORD-1", "date": "2026-10-02"}}, {"text": "Installation confirmed APT-1."}], [schedule_installation]),
    "offer_management_agent": ([{"call": "generate_offer_quote", "args": {"sku": "FIB-1G"}}, {"text": "Quote OFF-1 ready."}], [generate_offer_quote]),
}


def add_new_contact(company_name: str, contact_name: str, email: str, tool_context: ToolContext) -> dict:
    """Save the customer's contact (publishes customer_context.contact)."""
    ctx = dict(tool_context.state.get("customer_context") or {})
    tool_context.state["customer_context"] = {**ctx, "contact": {"name": contact_name, "email": email}}
    return {"success": True, "company_name": company_name, "email": email}


#: Discovery registering a company with no contact on file (the contact card comes next).
DISCOVERY_WITHOUT_CONTACT = ([{"call": "add_new_company", "args": ADDRESS},
                              {"text": "Welcome Crane.io! Where should we send your quote?"}], [add_new_company, add_new_contact])
#: Discovery saving the contact from the card.
DISCOVERY_SAVES_CONTACT = [{"call": "add_new_contact", "args": {"company_name": "Crane.io", "contact_name": "Jane",
                                                                "email": "jane@crane.io"}},
                           {"text": "Confirmations will go to jane@crane.io."}]


def build_fake_agents(scripts: dict | None = None) -> dict:
    agents = {}
    for spec in AGENTS:
        steps, tools = {**SCRIPTS, **(scripts or {})}.get(spec.name, ([{"text": f"{spec.name} reply"}], []))
        agents[spec.name] = Agent(
            name=spec.name,
            model=ScriptLlm(steps=steps),
            instruction="test",
            tools=tools,
            after_tool_callback=[export_context_delta],
        )
    return agents


def router(target: str) -> ScriptLlm:
    return ScriptLlm(json_reply={"target": target, "reason": "test"})

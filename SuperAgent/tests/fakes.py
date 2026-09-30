"""In-process stand-ins for the remote A2A agents (scripted models, no network)."""

from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

from sales_common.context import export_context_delta
from sales_common.testing import ScriptLlm
from super_agent.registry import AGENTS


def add_new_company(company_name: str, street: str, city: str, state: str, zip_code: str, tool_context: ToolContext) -> dict:
    """Register a company."""
    ctx = {"customer_id": "CUST-20260930-001", "company_name": company_name,
           "address": {"street": street, "city": city, "state": state, "zip_code": zip_code}}
    tool_context.state["customer_context"] = ctx
    return {"success": True, "customer_id": ctx["customer_id"], "company_name": company_name}


def check_service_availability(street: str, city: str, state: str, zip_code: str, tool_context: ToolContext) -> dict:
    """Check coverage."""
    tool_context.state["serviceability_context"] = {
        "is_serviceable": True, "service_address": {"zip_code": zip_code}, "available_products": ["FIB-1G"]}
    return {"serviceable": True, "zip_code": zip_code}


def schedule_installation(order_id: str, date: str, tool_context: ToolContext) -> dict:
    """Schedule an installation."""
    return {"success": True, "order_id": order_id, "appointment_id": "APT-1", "scheduled_date": date}


def generate_offer_quote(sku: str, tool_context: ToolContext) -> dict:
    """Quote."""
    tool_context.state["offer_context"] = {"offer_id": "OFF-1", "items": [{"product_id": sku}]}
    return {"offer_id": "OFF-1", "items": [{"product_id": sku, "final_price": 99.0}], "total_price": 99.0}


ADDRESS = {"company_name": "Crane.io", "street": "123 Main St", "city": "Philadelphia", "state": "PA", "zip_code": "19103"}

SCRIPTS = {
    "discovery_agent": ([{"call": "add_new_company", "args": ADDRESS}, {"text": "Welcome Crane.io! Let me check service availability."}], [add_new_company]),
    "serviceability_agent": ([{"call": "check_service_availability", "args": {k: ADDRESS[k] for k in ("street", "city", "state", "zip_code")}}, {"text": "This location is serviceable with Fiber."}], [check_service_availability]),
    "service_fulfillment_agent": ([{"call": "schedule_installation", "args": {"order_id": "ORD-1", "date": "2026-10-02"}}, {"text": "Installation confirmed APT-1."}], [schedule_installation]),
    "offer_management_agent": ([{"call": "generate_offer_quote", "args": {"sku": "FIB-1G"}}, {"text": "Quote OFF-1 ready."}], [generate_offer_quote]),
}


def build_fake_agents() -> dict:
    agents = {}
    for spec in AGENTS:
        steps, tools = SCRIPTS.get(spec.name, ([{"text": f"{spec.name} reply"}], []))
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

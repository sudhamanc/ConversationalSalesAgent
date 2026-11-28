"""A2UI 1.0 surfaces built from remote tool results (specs: generative-ui, guided-checkout).

The chat UI renders these with CopilotKit's standard catalog plus the app's
``SecurePaymentForm`` (``SuperAgent/client/src/a2ui/salesUI.js``; exported
catalog: ``SuperAgent/server/a2ui/catalog.json``). Everything shown comes from
the tool result or the session's journey state: no model is called here. Every
Button calls the client function ``sendChatMessage`` with a customer-voice
message, so a click becomes the customer's next chat turn.

``build_surface(tool, response, state)`` returns
``{"surface_id", "kind", "operations"}`` or ``None``. ``kind`` (quote,
serviceability, products, cart, order, scheduling, payment, contact) lets the UI skip
the legacy card of the same kind.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Callable, Optional

from sales_common.mcp_client import mcp_result_payload

A2UI_VERSION = "1.0"
ROOT_ID = "root"
SEND_FUNCTION = "sendChatMessage"
PAYMENT_FORM = "SecurePaymentForm"

QUOTE_TOOLS = frozenset({"generate_offer_quote", "find_best_bundle_offer", "get_quote_details"})
SERVICEABILITY_TOOLS = frozenset({"check_service_availability"})
PRODUCT_LIST_TOOLS = frozenset({"list_available_products", "search_products_by_criteria"})
COMPARE_TOOLS = frozenset({"compare_products"})
PRODUCT_DETAIL_TOOLS = frozenset({"get_product_by_id"})
CART_TOOLS = frozenset({"add_to_cart", "remove_from_cart", "get_cart"})
ORDER_TOOLS = frozenset({"create_order", "get_order"})
SLOT_TOOLS = frozenset({"check_availability"})
SCHEDULED_TOOLS = frozenset({"schedule_installation"})
PAYMENT_METHOD_TOOLS = frozenset({"get_payment_methods"})
PAYMENT_TOOLS = frozenset({"process_payment"})
#: Most products listed (and buttons) in one surface.
MAX_PRODUCTS = 6
MAX_PRODUCT_BUTTONS = 3
MAX_SLOTS = 10
#: Contract terms the offer service prices (pricing_tools: 12, 24 or 36 months).
CONTRACT_TERMS = (12, 24, 36)
WINDOW_NAMES = {"AM": "morning", "PM": "afternoon", "all_day": "all day"}

Node = dict[str, Any]
State = dict[str, Any]


class _Surface:
    """Collects flat A2UI component nodes with generated ids."""

    def __init__(self) -> None:
        self.nodes: list[Node] = []
        self.data_model: dict[str, Any] = {}
        self._count = 0

    def add(self, component: str, node_id: Optional[str] = None, **props: Any) -> str:
        if node_id is None:
            self._count += 1
            node_id = f"{component.lower()}-{self._count}"
        self.nodes.append({"id": node_id, "component": component, **{k: v for k, v in props.items() if v is not None}})
        return node_id

    def text(self, text: str, **props: Any) -> str:
        return self.add("Text", text=text, **props)

    def caption(self, text: str) -> str:
        return self.add("Caption", text=text)

    def title(self, text: str) -> str:
        return self.add("Title", text=text, size="lg")

    def title_badge(self, text: str, badge: str, color: str) -> str:
        return self.add("Row", gap=2, align="center", children=[
            self.title(text), self.add("Badge", label=badge, color=color),
        ])

    def label_value(self, label: str, value: str) -> str:
        return self.add(
            "Row", justify="spaceBetween",
            children=[self.caption(label), self.text(value, fontWeight="medium")],
        )

    def button(self, label: str, message: str, primary: bool = False) -> str:
        return self.add(
            "Button",
            label=label,
            variant="primary" if primary else None,
            onClick={"functionCall": {"@call": SEND_FUNCTION, "args": {"message": message}}},
        )

    def buttons(self, specs: list[tuple[str, str]], primary_first: bool = True) -> str:
        ids = [self.button(label, message, primary=(primary_first and i == 0)) for i, (label, message) in enumerate(specs)]
        return self.add("Row", gap=2, wrap="wrap", children=ids)

    def card(self, children: list[str]) -> "_Surface":
        self.add("Card", node_id=ROOT_ID, children=children)
        return self


# --- formatting -------------------------------------------------------------


def _num(value: Any) -> str:
    """Numbers as text; whole floats (A2A carries ints as 5000.0) without the decimal part."""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return str(value)


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "-"


def _date(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _long_date(day: date) -> str:
    return f"{day.strftime('%A, %B')} {day.day}, {day.year}"


def _short_date(day: date) -> str:
    return f"{day.strftime('%a, %b')} {day.day}"


def _clock(hhmm: Any) -> str:
    """'08:00' -> '8 AM', '13:30' -> '1:30 PM'."""
    try:
        hour, minute = (int(p) for p in str(hhmm).split(":")[:2])
    except ValueError:
        return str(hhmm)
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12 or 12
    return f"{hour12} {suffix}" if minute == 0 else f"{hour12}:{minute:02d} {suffix}"


def _window_text(slot: dict) -> str:
    start, end = slot.get("start_time"), slot.get("end_time")
    if start and end:
        return f"{_clock(start)}–{_clock(end)}"
    return WINDOW_NAMES.get(str(slot.get("window")), str(slot.get("window") or ""))


def _payload(response: Any) -> Optional[dict]:
    """The tool's JSON object: a plain dict (FunctionTool) or an MCP CallToolResult."""
    if not isinstance(response, dict):
        return None
    if "structuredContent" in response or "structured_content" in response or (
        "content" in response and isinstance(response.get("content"), list)
    ):
        return mcp_result_payload(response)
    return response


def _stamp_actions(surface_id: str, surface: _Surface) -> None:
    """Every Button's ``sendChatMessage`` args name its surface and its component id,
    so the UI can show which choice was made (spec: generative-ui, acted surfaces)."""
    for node in surface.nodes:
        call = (node.get("onClick") or {}).get("functionCall") if node.get("component") == "Button" else None
        if isinstance(call, dict) and call.get("@call") == SEND_FUNCTION and isinstance(call.get("args"), dict):
            call["args"] = {**call["args"], "surface": surface_id, "button": node["id"]}


def _operations(surface_id: str, surface: _Surface) -> list[dict]:
    _stamp_actions(surface_id, surface)
    create: dict[str, Any] = {"surfaceId": surface_id, "components": surface.nodes}
    if surface.data_model:
        create["dataModel"] = surface.data_model
    return [{"version": A2UI_VERSION, "createSurface": create}]


def _ctx(state: State, key: str) -> dict:
    value = (state or {}).get(key)
    return value if isinstance(value, dict) else {}


# --- quote -----------------------------------------------------------------


def _quote(data: dict, state: State) -> Optional[_Surface]:
    quote = data.get("quote") if isinstance(data.get("quote"), dict) else data
    if not quote.get("offer_id"):
        return None
    s = _Surface()
    offer_id = quote["offer_id"]
    items = [i for i in quote.get("items") or [] if isinstance(i, dict)]
    rows = [
        [
            str(i.get("product_name") or i.get("product_id") or "-"),
            _num(i.get("quantity", 1)),
            _money((i.get("price_points") or {}).get("unit_price", i.get("unit_price"))),
            _money(i.get("final_price")),
        ]
        for i in items
    ]
    monthly = quote.get("monthly_total", quote.get("total_price"))
    term = _num(quote["term_months"]) if quote.get("term_months") else None
    children = [
        s.title(f"Your quote for {quote['company_name']}" if quote.get("company_name") else "Your quote"),
        s.caption(f"Quote {offer_id}" + (f" · valid until {str(quote['expires_at'])[:10]}" if quote.get("expires_at") else "")),
    ]
    if rows:
        children.append(s.add("Table", columns=["Service", "Qty", "Unit price", "Price"], rows=rows))
    children.append(s.add("Divider"))
    if term:
        children.append(s.label_value("Contract term", f"{term} months"))
    if quote.get("total_discount"):
        children.append(s.label_value("Discount", f"-{_money(quote['total_discount'])}"))
    children.append(s.label_value("Monthly total", _money(monthly)))
    if quote.get("yearly_total"):
        children.append(s.label_value("Yearly total", _money(quote["yearly_total"])))
    which = f"quote {offer_id}" + (f" ({term} months)" if term else "")
    children.append(s.buttons([("Accept quote", f"I'll take {which}. Please place my order.")]
                              + [(f"{t} months", f"Please re-quote {offer_id} on a {t}-month term.")
                                 for t in CONTRACT_TERMS if str(t) != term]
                              + [("Add a service", f"I'd like to add another service to {which}."),
                                 ("Email it to me", f"Please email me {which}.")]))
    return s.card(children)


# --- serviceability ---------------------------------------------------------


def _address_line(address: Any) -> str:
    if not isinstance(address, dict):
        return ""
    street, city, state, zip_code = (address.get(k) or "" for k in ("street", "city", "state", "zip_code"))
    return ", ".join(p for p in (street, city, f"{state} {zip_code}".strip()) if p)


def _serviceability(data: dict, state: State) -> Optional[_Surface]:
    if "serviceable" not in data:
        return None
    s = _Surface()
    address = _address_line(data.get("address"))
    if data.get("serviceable"):
        children = [s.title_badge("Service is available", "Serviceable", "success")]
        if address:
            children.append(s.caption(address))
        if data.get("infrastructure_type"):
            children.append(s.label_value("Network", str(data["infrastructure_type"])))
        if data.get("max_speed_mbps"):
            children.append(s.label_value("Max speed", f"{_num(data['max_speed_mbps'])} Mbps"))
        if data.get("estimated_install_days") is not None:
            children.append(s.label_value("Installation lead time", f"{_num(data['estimated_install_days'])} days"))
        categories = [str(c) for c in data.get("available_product_categories") or []]
        if categories:
            children.append(s.label_value("Services", ", ".join(categories)))
        children.append(s.buttons([
            ("Show plans", "Show me the plans available at my address"),
            ("Get a quote", "I'd like a quote for internet service at this address"),
        ]))
    else:
        children = [s.title_badge("Service is not available yet", "Not serviceable", "warning")]
        if address:
            children.append(s.caption(address))
        if data.get("reason"):
            children.append(s.text(str(data["reason"]), color="secondary"))
        children.append(s.buttons([
            ("Other options", "What other options do I have?"),
            ("Try another address", "I'd like to check a different address"),
        ]))
    return s.card(children)


# --- products ---------------------------------------------------------------


def _speeds(product: dict) -> tuple[str, str]:
    speeds = product.get("speeds") if isinstance(product.get("speeds"), dict) else {}
    return str(speeds.get("download") or "-"), str(speeds.get("upload") or "-")


def _is_internet(product: dict) -> bool:
    """Internet plans (category "Fiber Internet", "Coax Internet") depend on the address's network."""
    return "internet" in str(product.get("category") or "").lower()


def _available_ids(state: State) -> set[str]:
    svc = _ctx(state, "serviceability_context")
    if not svc.get("is_serviceable"):
        return set()
    return {str(p) for p in svc.get("available_products") or []}


def _products(data: dict, state: State) -> Optional[_Surface]:
    products = [p for p in data.get("products") or [] if isinstance(p, dict) and p.get("product_name")]
    available = _available_ids(state)
    at_address = False
    if available:
        # Internet plans are sold only where the network supports them; other
        # categories (Voice, SD-WAN, Mobile) ride any access.
        filtered = [p for p in products if p.get("product_id") in available or not _is_internet(p)]
        if filtered:
            at_address = len(filtered) < len(products)
            products = filtered
    if not products:
        return None
    shown = products[:MAX_PRODUCTS]
    s = _Surface()
    rows = [[str(p["product_name"]), str(p.get("technology") or "-"), *_speeds(p)] for p in shown]
    title = f"{data['category']} plans" if data.get("category") else "Available plans"
    more = len(products) - len(shown)
    caption = f"{len(products)} plans" + (" at your address" if at_address else "") + (f" · showing {len(shown)}" if more > 0 else "")
    children = [s.title(title), s.caption(caption),
                s.add("Table", columns=["Plan", "Technology", "Download", "Upload"], rows=rows)]
    children.append(s.buttons(
        [(f"Quote {p['product_name']}", f"I'd like a quote for {p['product_name']}") for p in shown[:1]]
        + [(f"About {p['product_name']}", f"Tell me more about {p['product_name']}") for p in shown[:MAX_PRODUCT_BUTTONS]]
    ))
    return s.card(children)


def _compare(data: dict, state: State) -> Optional[_Surface]:
    comparison = data.get("comparison") if isinstance(data.get("comparison"), dict) else {}
    table = comparison.get("comparison_table") if isinstance(comparison.get("comparison_table"), dict) else {}
    names = [str(n) for n in table.get("product_name") or []]
    if len(names) < 2:
        return None
    s = _Surface()

    def row(label: str, key: str) -> list[str]:
        values = list(table.get(key) or [])
        cells = []
        for i in range(len(names)):
            v = values[i] if i < len(values) else "-"
            cells.append(", ".join(map(str, v)) if isinstance(v, list) else str(v))
        return [label, *cells]

    rows = [
        row("Technology", "technology"),
        row("Download", "download_speed"),
        row("Upload", "upload_speed"),
        row("Uptime SLA", "uptime_sla"),
        row("Key features", "key_features"),
    ]
    children = [s.title("Plan comparison"), s.add("Table", columns=["", *names], rows=rows)]
    if data.get("recommendation"):
        children.append(s.text(str(data["recommendation"]), color="secondary"))
    ids = list(comparison.get("products") or [])
    fastest = data.get("fastest_product_id")
    pick = names[ids.index(fastest)] if fastest in ids and ids.index(fastest) < len(names) else names[0]
    children.append(s.buttons([(f"Quote {n}", f"I'd like a quote for {n}") for n in [pick] + [n for n in names if n != pick][:1]]))
    return s.card(children)


def _product_detail(data: dict, state: State) -> Optional[_Surface]:
    if not data.get("product_name"):
        return None
    s = _Surface()
    name = str(data["product_name"])
    download, upload = _speeds(data)
    children = [s.title(name), s.caption(" · ".join(str(x) for x in (data.get("category"), data.get("technology")) if x))]
    if data.get("description"):
        children.append(s.text(str(data["description"])))
    if download != "-":
        children.append(s.label_value("Download / upload", f"{download} / {upload}"))
    features = [str(f) for f in data.get("features") or []][:8]
    if features:
        children.append(s.add("Table", columns=["Included"], rows=[[f] for f in features]))
    children.append(s.buttons([
        (f"Quote {name}", f"I'd like a quote for {name}"),
        ("Compare plans", f"Compare {name} with similar plans"),
    ]))
    return s.card(children)


# --- cart and order -----------------------------------------------------------


def _cart(data: dict, state: State) -> Optional[_Surface]:
    cart = data.get("cart") if isinstance(data.get("cart"), dict) else data
    items = [i for i in cart.get("items") or [] if isinstance(i, dict)]
    if not items:
        return None
    s = _Surface()
    rows = [
        [str(i.get("service_type") or i.get("product_name") or "-"), _num(i.get("quantity", 1)),
         _money(i.get("subtotal", i.get("price")))]
        for i in items
    ]
    children = [
        s.title("Your cart"),
        s.add("Table", columns=["Service", "Qty", "Monthly"], rows=rows),
        s.label_value("Monthly total", _money(cart.get("total_amount"))),
        s.buttons([
            ("Place my order", "That's everything. Please place my order."),
            ("Add another service", "I'd like to add another service to my order"),
        ]),
    ]
    return s.card(children)


def _order(data: dict, state: State) -> Optional[_Surface]:
    order = data.get("order") if isinstance(data.get("order"), dict) else data
    if not order.get("order_id"):
        return None
    s = _Surface()
    status = str(order.get("status") or "").replace("_", " ")
    children = [
        s.title_badge("Order created" if order.get("status") == "pending_payment" else "Your order",
                      status.capitalize() or "Order", "info"),
        s.caption(f"Order {order['order_id']}"),
    ]
    if order.get("service_type"):
        children.append(s.label_value("Service", str(order["service_type"])))
    if order.get("service_address"):
        children.append(s.label_value("Address", str(order["service_address"])))
    if order.get("total_amount") is not None:
        children.append(s.label_value("Monthly total", _money(order["total_amount"])))
    if order.get("status") == "pending_payment":
        children.append(s.text("Next: choose an installation time, then pay to confirm your order.", color="secondary"))
    return s.card(children)


# --- installation -----------------------------------------------------------


def _slot_message(day: date, slot: dict) -> str:
    window = WINDOW_NAMES.get(str(slot.get("window")))
    return (f"Please book my installation for {_long_date(day)}, {_window_text(slot)}"
            + (f" ({window})." if window else "."))


def _slots(data: dict, state: State) -> Optional[_Surface]:
    slots = [x for x in data.get("available_slots") or [] if isinstance(x, dict) and _date(x.get("date"))][:MAX_SLOTS]
    if not slots:
        return None
    s = _Surface()
    by_day: dict[date, list[dict]] = {}
    for slot in slots:
        by_day.setdefault(_date(slot["date"]), []).append(slot)
    rows = []
    first = True
    for day, day_slots in by_day.items():
        buttons = []
        for slot in day_slots:
            buttons.append(s.button(_window_text(slot), _slot_message(day, slot), primary=first))  # soonest first
            first = False
        rows.append(s.add("Row", justify="spaceBetween", align="center", wrap="wrap", gap=2, children=[
            s.text(_short_date(day), fontWeight="medium"),
            s.add("Row", gap=2, children=buttons),
        ]))
    children = [s.title("Choose an installation time")]
    if data.get("service_address"):
        children.append(s.caption(str(data["service_address"])))
    children.extend(rows)
    return s.card(children)


def _scheduled(data: dict, state: State) -> Optional[_Surface]:
    day = _date(data.get("scheduled_date") or data.get("appointment_date"))
    if not day or not data.get("appointment_id"):
        return None
    s = _Surface()
    children = [
        s.title_badge("Installation scheduled", "Confirmed", "success"),
        s.caption(f"Appointment {data['appointment_id']}"),
        s.label_value("Date", _long_date(day)),
        s.label_value("Time", _window_text(data)),
    ]
    if data.get("service_address"):
        children.append(s.label_value("Address", str(data["service_address"])))
    return s.card(children)


# --- payment ------------------------------------------------------------------


def _method_label(method: dict) -> str:
    if method.get("payment_type") == "ach":
        kind = f"{method.get('account_type') or 'bank'} account".capitalize()
    else:
        kind = str(method.get("card_brand") or "card").capitalize()
        kind = {"Amex": "American Express", "Mastercard": "Mastercard", "Visa": "Visa"}.get(kind, kind)
    return f"{kind} ending {method.get('last_four') or '••••'}"


def _payment_methods(data: dict, state: State) -> Optional[_Surface]:
    if "payment_methods" not in data:
        return None
    order = _ctx(state, "order_context")
    amount = order.get("total_amount", order.get("price"))
    s = _Surface()
    children = [s.title("Pay for your order")]
    if order.get("order_id"):
        children.append(s.caption(f"Order {order['order_id']}"))
    if amount is not None:
        children.append(s.label_value("Amount due", _money(amount)))
    methods = [m for m in data.get("payment_methods") or [] if isinstance(m, dict)][:4]
    if methods:
        children.append(s.text("Pay with a saved method", fontWeight="medium"))
        children.append(s.buttons([
            (f"Pay with {_method_label(m)}", f"Pay for my order with my {_method_label(m)}.") for m in methods
        ]))
        children.append(s.add("Divider"))
    children.append(s.add(PAYMENT_FORM, amount=_money(amount) if amount is not None else None,
                          title="Add a new payment method" if methods else "Add a payment method"))
    return s.card(children)


def _receipt(data: dict, state: State) -> Optional[_Surface]:
    if str(data.get("status") or "").lower() not in ("completed", "approved", "captured"):
        return None
    s = _Surface()
    children = [
        s.title_badge("Payment received", "Paid", "success"),
        s.label_value("Amount", _money(data.get("amount"))),
    ]
    if data.get("order_id"):
        children.append(s.label_value("Order", str(data["order_id"])))
    if data.get("transaction_id"):
        children.append(s.label_value("Transaction", str(data["transaction_id"])))
    if data.get("email_confirmation_queued"):
        children.append(s.caption("A receipt is on its way to your email."))
    return s.card(children)


# --- contact -------------------------------------------------------------------


def _has_contact_email(state: State) -> bool:
    contact = _ctx(state, "customer_context").get("contact")
    return isinstance(contact, dict) and bool(contact.get("email"))


def _contact_card(title: str, note: str, then: str, state: State) -> _Surface:
    """Name / email / phone fields; the Save button sends them as a chat message (spec: guided-checkout)."""
    s = _Surface()
    contact = _ctx(state, "customer_context").get("contact") or {}
    s.data_model = {"contact": {"name": str(contact.get("name") or ""), "email": "", "phone": ""}}
    email_ok = {"@call": "email", "args": {"value": {"@path": "/contact/email"}}}
    name_ok = {"@call": "required", "args": {"value": {"@path": "/contact/name"}}}
    save = s.add(
        "Button", label="Save contact details", variant="primary",
        checks=[{"condition": name_ok, "message": "Enter your name"},
                {"condition": email_ok, "message": "Enter a valid email address"}],
        onClick={"functionCall": {"@call": SEND_FUNCTION, "args": {"message": {"@call": "formatString", "args": {
            "value": "My contact details: name ${/contact/name}, email ${/contact/email}, phone ${/contact/phone}." + then}}}}},
    )
    children = [
        s.title(title),
        s.caption(note),
        s.add("TextField", label="Your name", value={"@path": "/contact/name"}, placeholder="Jane Doe"),
        s.add("TextField", label="Email", value={"@path": "/contact/email"}, placeholder="jane@company.com",
              checks=[{"condition": email_ok, "message": "Enter a valid email address"}]),
        s.add("TextField", label="Phone (optional)", value={"@path": "/contact/phone"}, placeholder="215-555-0100"),
        s.add("Row", children=[save]),
    ]
    return s.card(children)


def _registration_contact(data: dict, state: State) -> Optional[_Surface]:
    if not data.get("customer_id") or _has_contact_email(state):
        return None
    return _contact_card(
        "Where should we send your quote and order confirmation?",
        "We email your quote, order confirmation, payment receipt and installation reminders.",
        "", state,
    )


def _order_contact(data: dict, state: State) -> Optional[_Surface]:
    return _contact_card(
        "Who should receive your order confirmation?",
        "An email address is needed to place your order.",
        " Please place my order.", state,
    )


#: Results that are errors but still get a card: create_order without an email.
_ERROR_BUILDERS: dict[tuple[str, str], tuple[str, Callable[[dict, State], Optional[_Surface]]]] = {
    ("create_order", "contact_email_required"): ("contact", _order_contact),
}

_BUILDERS: dict[str, tuple[str, Callable[[dict, State], Optional[_Surface]]]] = {
    "add_new_company": ("contact", _registration_contact),
    **{t: ("quote", _quote) for t in QUOTE_TOOLS},
    **{t: ("serviceability", _serviceability) for t in SERVICEABILITY_TOOLS},
    **{t: ("products", _products) for t in PRODUCT_LIST_TOOLS},
    **{t: ("products", _compare) for t in COMPARE_TOOLS},
    **{t: ("products", _product_detail) for t in PRODUCT_DETAIL_TOOLS},
    **{t: ("cart", _cart) for t in CART_TOOLS},
    **{t: ("order", _order) for t in ORDER_TOOLS},
    **{t: ("scheduling", _slots) for t in SLOT_TOOLS},
    **{t: ("scheduling", _scheduled) for t in SCHEDULED_TOOLS},
    **{t: ("payment", _payment_methods) for t in PAYMENT_METHOD_TOOLS},
    **{t: ("payment", _receipt) for t in PAYMENT_TOOLS},
}

SURFACE_TOOLS = frozenset(_BUILDERS)


def surface_id_for(tool: str, data: dict) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:12]
    return f"{tool}-{digest}"


def build_surface(tool: str, response: Any, state: Optional[State] = None) -> Optional[dict]:
    """The ``a2ui`` SSE payload fields for one tool result, or ``None``.

    ``state`` is the journey state (session state at turn start plus context
    updates seen so far): it filters product lists to the checked address and
    gives the payment surface its amount due.
    """
    entry = _BUILDERS.get(tool)
    if entry is None and not any(t == tool for t, _ in _ERROR_BUILDERS):
        return None
    data = _payload(response)
    if not data:
        return None
    if data.get("success") is False or data.get("error"):
        entry = _ERROR_BUILDERS.get((tool, str(data.get("error"))))
        if entry is None:
            return None
    kind, builder = entry
    try:
        surface = builder(data, state or {})
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    if surface is None:
        return None
    surface_id = surface_id_for(tool, data)
    return {"surface_id": surface_id, "kind": kind, "operations": _operations(surface_id, surface)}

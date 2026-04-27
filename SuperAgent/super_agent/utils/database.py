"""
Unified SQLite persistence layer for the Multi-Agent Sales System.

Consolidates 4 formerly independent databases (Discovery, Orders, Quotes,
Notifications) plus 2 new tables (payments, fulfillments) and a post-sale
customer_master into a single ``sales_agent.db``.

Key features
------------
- Single WAL-enabled SQLite file with FK enforcement
- Thread-safe via ``threading.Lock()``
- 17 tables across 7 domains (Discovery, Offer, Order, Payment,
  Fulfillment, Customer, Communication)
- TTL-based lifecycle management (``cleanup_stale_records()``)
- Cross-table customer state queries (``check_customer_state()``)

Configuration
-------------
Set ``SALES_AGENT_DB_PATH`` env var to override the default location
(``SuperAgent/data/sales_agent.db``).
"""

import json
import logging
import os
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("superagent.database")

# ---------------------------------------------------------------------------
# DB path & connection management
# ---------------------------------------------------------------------------

_DEFAULT_DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)
_DEFAULT_DB_PATH = os.path.join(_DEFAULT_DB_DIR, "sales_agent.db")

_lock = threading.Lock()


def _get_db_path() -> str:
    """Return the resolved database file path, creating parent dirs."""
    db_path = os.getenv("SALES_AGENT_DB_PATH", _DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return db_path


def get_connection() -> sqlite3.Connection:
    """Return a new WAL-enabled connection with FK enforcement.

    Callers are responsible for closing the connection.
    """
    conn = sqlite3.connect(_get_db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema: all 17 tables
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
-- =========================================================================
-- Discovery Domain (6 tables — migrated from discover_prospecting_clean.db)
-- =========================================================================

CREATE TABLE IF NOT EXISTS accounts (
    "Company Name"         TEXT PRIMARY KEY,
    "Parent Company"       TEXT,
    Industry               TEXT,
    "Territory/Region"     TEXT,
    Street                 TEXT,
    City                   TEXT,
    State                  TEXT,
    zip_code               TEXT NOT NULL,
    address_line2          TEXT,
    Website                TEXT,
    "Existing Customer"    TEXT,
    "Current Products"     TEXT,
    "Products of Interest" TEXT,
    customer_id            TEXT,
    created_at             TEXT,
    updated_at             TEXT
);

CREATE INDEX IF NOT EXISTS idx_accounts_customer_id
    ON accounts(customer_id);

CREATE TABLE IF NOT EXISTS contacts (
    "Company Name"            TEXT,
    "Name"                    TEXT,
    "Title"                   TEXT,
    "Role in Decision Making" TEXT,
    "Email"                   TEXT,
    "Phone"                   TEXT,
    "Notes"                   TEXT,
    created_at                TEXT
);

CREATE INDEX IF NOT EXISTS idx_contacts_company
    ON contacts("Company Name");

CREATE TABLE IF NOT EXISTS spend (
    "Company Name"           TEXT,
    "Estimated Annual Spend" INTEGER,
    "Digital"                INTEGER,
    "Programmatic"           INTEGER,
    "TV"                     INTEGER,
    "Audio"                  INTEGER,
    "OOH"                    INTEGER,
    "Search"                 INTEGER,
    "Social"                 INTEGER,
    "Primary Agency"         TEXT
);

CREATE INDEX IF NOT EXISTS idx_spend_company
    ON spend("Company Name");

CREATE TABLE IF NOT EXISTS opportunities (
    "Company Name"         TEXT,
    "Opportunity Name"     TEXT,
    "Stage"                TEXT,
    "Total MRC (Est)"      INTEGER,
    "Budget"               TEXT,
    "Authority"            TEXT,
    "Need"                 TEXT,
    "Timeline (days)"      INTEGER,
    "Target Close Date"    TEXT,
    "Next Step"            TEXT,
    "BANT_Budget_Score"    INTEGER,
    "BANT_Authority_Score" INTEGER,
    "BANT_Need_Score"      INTEGER,
    "BANT_Timing_Score"    INTEGER,
    "BANT_Weighted_0to3"   REAL,
    "BANT_Score_0to100"    REAL,
    "BANT_Priority_Bucket" TEXT,
    "BANT_Data_Gaps"       TEXT,
    created_at             TEXT,
    updated_at             TEXT
);

CREATE INDEX IF NOT EXISTS idx_opportunities_company
    ON opportunities("Company Name");

CREATE TABLE IF NOT EXISTS insights (
    "Company Name"            TEXT,
    "Buying Signals"          TEXT,
    "Pain Points"             TEXT,
    "Recommended Positioning" TEXT
);

CREATE INDEX IF NOT EXISTS idx_insights_company
    ON insights("Company Name");

CREATE TABLE IF NOT EXISTS actions (
    "Company Name"          TEXT,
    "Owner"                 TEXT,
    "Priority"              TEXT,
    "Initial Outreach Date" TEXT,
    "Follow-Up Cadence"     TEXT
);

CREATE INDEX IF NOT EXISTS idx_actions_company
    ON actions("Company Name");

-- =========================================================================
-- Offer Domain (1 table — migrated from quotes.db)
-- =========================================================================

CREATE TABLE IF NOT EXISTS quotes (
    offer_id        TEXT PRIMARY KEY,
    customer_id     TEXT,
    company_name    TEXT,
    items_json      TEXT NOT NULL,
    term_months     INTEGER NOT NULL DEFAULT 12,
    bant_score      REAL NOT NULL DEFAULT 0.0,
    subtotal        REAL NOT NULL,
    total_discount  REAL NOT NULL DEFAULT 0.0,
    total_price     REAL NOT NULL,
    monthly_total   REAL NOT NULL,
    yearly_total    REAL NOT NULL,
    full_quote_json TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    expires_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_quotes_customer  ON quotes(customer_id);
CREATE INDEX IF NOT EXISTS idx_quotes_company   ON quotes(company_name);
CREATE INDEX IF NOT EXISTS idx_quotes_status    ON quotes(status);

-- =========================================================================
-- Order Domain (4 tables — migrated from orders.db)
-- =========================================================================

CREATE TABLE IF NOT EXISTS carts (
    cart_id       TEXT PRIMARY KEY,
    customer_id   TEXT NOT NULL,
    total_amount  REAL NOT NULL DEFAULT 0.0,
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    expires_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_carts_customer ON carts(customer_id);
CREATE INDEX IF NOT EXISTS idx_carts_status   ON carts(status);

CREATE TABLE IF NOT EXISTS cart_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_id       TEXT NOT NULL REFERENCES carts(cart_id) ON DELETE CASCADE,
    service_type  TEXT NOT NULL,
    price         REAL NOT NULL,
    quantity      INTEGER NOT NULL DEFAULT 1,
    subtotal      REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON cart_items(cart_id);

CREATE TABLE IF NOT EXISTS orders (
    order_id       TEXT PRIMARY KEY,
    customer_name  TEXT NOT NULL,
    customer_id    TEXT NOT NULL,
    service_address TEXT NOT NULL,
    contact_phone  TEXT NOT NULL,
    contact_email  TEXT,
    offer_id       TEXT REFERENCES quotes(offer_id),
    status         TEXT NOT NULL DEFAULT 'draft',
    total_amount   REAL NOT NULL DEFAULT 0.0,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    expires_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_offer    ON orders(offer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status   ON orders(status);

CREATE TABLE IF NOT EXISTS order_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    service_type  TEXT NOT NULL,
    price         REAL NOT NULL,
    quantity      INTEGER NOT NULL DEFAULT 1,
    subtotal      REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);

-- =========================================================================
-- Payment Domain (1 table — NEW, replaces PaymentAgent in-memory mock)
-- =========================================================================

CREATE TABLE IF NOT EXISTS payments (
    payment_id     TEXT PRIMARY KEY,
    order_id       TEXT NOT NULL REFERENCES orders(order_id),
    customer_id    TEXT NOT NULL,
    transaction_id TEXT,
    amount         REAL NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
    credit_score   INTEGER,
    payment_method TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    expires_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_payments_order    ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_status   ON payments(status);

-- =========================================================================
-- Fulfillment Domain (1 table — NEW, replaces ServiceFulfillment mock)
-- =========================================================================

CREATE TABLE IF NOT EXISTS fulfillments (
    fulfillment_id  TEXT PRIMARY KEY,
    order_id        TEXT NOT NULL REFERENCES orders(order_id),
    customer_id     TEXT NOT NULL,
    dispatch_id     TEXT,
    activation_id   TEXT,
    circuit_id      TEXT,
    account_id      TEXT,
    appointment_date TEXT,
    status          TEXT NOT NULL DEFAULT 'scheduled',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fulfillments_order    ON fulfillments(order_id);
CREATE INDEX IF NOT EXISTS idx_fulfillments_customer ON fulfillments(customer_id);
CREATE INDEX IF NOT EXISTS idx_fulfillments_status   ON fulfillments(status);

-- =========================================================================
-- Customer Domain (1 table — NEW, populated ONLY after fulfillment)
-- =========================================================================

CREATE TABLE IF NOT EXISTS customer_master (
    customer_id         TEXT PRIMARY KEY,
    company_name        TEXT NOT NULL,
    street              TEXT NOT NULL,
    city                TEXT NOT NULL,
    state               TEXT NOT NULL,
    zip_code            TEXT NOT NULL,
    contact_name        TEXT,
    contact_email       TEXT,
    contact_phone       TEXT,
    first_order_id      TEXT REFERENCES orders(order_id),
    circuit_id          TEXT,
    account_id          TEXT,
    contracted_products TEXT,
    monthly_revenue     REAL,
    activated_at        TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

-- =========================================================================
-- Communication Domain (2 tables — migrated from notifications.db)
-- =========================================================================

CREATE TABLE IF NOT EXISTS notifications (
    notification_id   TEXT PRIMARY KEY,
    notification_type TEXT NOT NULL,
    recipient_email   TEXT,
    recipient_phone   TEXT,
    subject           TEXT,
    message           TEXT,
    metadata_json     TEXT,
    customer_id       TEXT,
    order_id          TEXT,
    status            TEXT NOT NULL DEFAULT 'pending',
    channels_json     TEXT NOT NULL DEFAULT '[]',
    created_at        TEXT NOT NULL,
    updated_at        TEXT,
    sent_at           TEXT,
    error             TEXT
);

CREATE INDEX IF NOT EXISTS idx_notif_email    ON notifications(recipient_email);
CREATE INDEX IF NOT EXISTS idx_notif_phone    ON notifications(recipient_phone);
CREATE INDEX IF NOT EXISTS idx_notif_type     ON notifications(notification_type);
CREATE INDEX IF NOT EXISTS idx_notif_customer ON notifications(customer_id);
CREATE INDEX IF NOT EXISTS idx_notif_order    ON notifications(order_id);

CREATE TABLE IF NOT EXISTS dedup_cache (
    dedup_key  TEXT PRIMARY KEY,
    sent_at    TEXT NOT NULL
);
"""


def init_db() -> None:
    """Create all 17 tables and indexes.  Safe to call multiple times."""
    with _lock:
        conn = get_connection()
        try:
            conn.executescript(_SCHEMA_SQL)
            conn.commit()
            logger.info("Unified database initialised at %s", _get_db_path())
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# TTL defaults (used by agent tools when inserting records)
# ---------------------------------------------------------------------------

QUOTE_EXPIRY_DAYS = 30
CART_EXPIRY_HOURS = 24
ORDER_EXPIRY_HOURS = 48
PAYMENT_EXPIRY_MINUTES = 15
ESCALATION_DAYS = 7


def compute_expires_at(created_at: str, entity: str) -> str:
    """Return an ISO-8601 ``expires_at`` value for the given entity type.

    Parameters
    ----------
    created_at : str
        ISO-8601 datetime string (``YYYY-MM-DDTHH:MM:SS``).
    entity : str
        One of ``"quote"``, ``"cart"``, ``"order"``, ``"payment"``.

    Returns
    -------
    str
        ISO-8601 datetime string for ``expires_at``.
    """
    dt = datetime.fromisoformat(created_at)
    deltas = {
        "quote": timedelta(days=QUOTE_EXPIRY_DAYS),
        "cart": timedelta(hours=CART_EXPIRY_HOURS),
        "order": timedelta(hours=ORDER_EXPIRY_HOURS),
        "payment": timedelta(minutes=PAYMENT_EXPIRY_MINUTES),
    }
    delta = deltas.get(entity)
    if delta is None:
        raise ValueError(f"Unknown entity type: {entity!r}")
    return (dt + delta).isoformat()


# ---------------------------------------------------------------------------
# cleanup_stale_records — TTL enforcement + notification triggers
# ---------------------------------------------------------------------------

def cleanup_stale_records() -> Dict[str, int]:
    """Expire / cancel / escalate stale records based on TTL rules.

    Returns a dict with counts of affected rows per category, e.g.::

        {"quotes_expired": 2, "carts_expired": 0, "orders_cancelled": 1,
         "orders_escalated": 0, "notifications_sent": 1}

    **Notification triggers:**
    - Each cart that transitions to ``expired`` triggers an
      ``ABANDONED_CART`` notification (if the customer has an email).
    - Each order that transitions to ``cancelled`` triggers an
      ``ORDER_CANCELLED`` notification.
    """
    now = datetime.now(timezone.utc).isoformat()
    escalation_cutoff = (datetime.now(timezone.utc) - timedelta(days=ESCALATION_DAYS)).isoformat()

    counts: Dict[str, int] = {
        "quotes_expired": 0,
        "carts_expired": 0,
        "orders_cancelled": 0,
        "orders_escalated": 0,
        "notifications_sent": 0,
    }

    with _lock:
        conn = get_connection()
        try:
            # --- Expire quotes ---
            cur = conn.execute(
                "UPDATE quotes SET status='expired', updated_at=? "
                "WHERE status='active' AND expires_at < ?",
                (now, now),
            )
            counts["quotes_expired"] = cur.rowcount

            # --- Expire carts (collect IDs for notifications) ---
            rows = conn.execute(
                "SELECT c.cart_id, c.customer_id, a.\"Company Name\", "
                "       (SELECT ct.\"Email\" FROM contacts ct "
                "        WHERE ct.\"Company Name\" = a.\"Company Name\" LIMIT 1) AS email "
                "FROM carts c "
                "LEFT JOIN accounts a ON c.customer_id = a.customer_id "
                "WHERE c.status='active' AND c.expires_at < ?",
                (now,),
            ).fetchall()

            if rows:
                conn.execute(
                    "UPDATE carts SET status='expired', updated_at=? "
                    "WHERE status='active' AND expires_at < ?",
                    (now, now),
                )
                counts["carts_expired"] = len(rows)

            # --- Cancel pending-payment orders (collect IDs for notifications) ---
            order_rows = conn.execute(
                "SELECT o.order_id, o.customer_id, o.contact_email "
                "FROM orders o "
                "WHERE o.status='pending_payment' AND o.expires_at < ?",
                (now,),
            ).fetchall()

            if order_rows:
                conn.execute(
                    "UPDATE orders SET status='cancelled', updated_at=? "
                    "WHERE status='pending_payment' AND expires_at < ?",
                    (now, now),
                )
                counts["orders_cancelled"] = len(order_rows)

            # --- Escalate paid orders stuck without fulfillment ---
            cur = conn.execute(
                "UPDATE orders SET status='escalated', updated_at=? "
                "WHERE status='paid' AND updated_at < ?",
                (now, escalation_cutoff),
            )
            counts["orders_escalated"] = cur.rowcount

            conn.commit()

            # --- Send notifications for expired carts / cancelled orders ---
            notif_count = 0
            comms = sys.modules.get(
                "customer_communication_agent.tools.notification_tools"
            )

            if comms and hasattr(comms, "send_notification"):
                for row in rows:
                    email = row["email"] if row["email"] else None
                    if email:
                        try:
                            comms.send_notification(
                                notification_type="ABANDONED_CART",
                                customer_id=row["customer_id"] or "",
                                recipient_email=email,
                                metadata=json.dumps({
                                    "cart_id": row["cart_id"],
                                    "company_name": row["Company Name"] or "",
                                }),
                            )
                            notif_count += 1
                        except Exception as exc:
                            logger.warning("Failed ABANDONED_CART notif for cart %s: %s",
                                           row["cart_id"], exc)

                for row in order_rows:
                    email = row["contact_email"] if row["contact_email"] else None
                    if email:
                        try:
                            comms.send_notification(
                                notification_type="ORDER_CANCELLED",
                                customer_id=row["customer_id"] or "",
                                order_id=row["order_id"],
                                recipient_email=email,
                                metadata=json.dumps({
                                    "order_id": row["order_id"],
                                    "reason": "TTL expiry — pending payment timed out",
                                }),
                            )
                            notif_count += 1
                        except Exception as exc:
                            logger.warning("Failed ORDER_CANCELLED notif for order %s: %s",
                                           row["order_id"], exc)

            counts["notifications_sent"] = notif_count

        finally:
            conn.close()

    logger.info("cleanup_stale_records: %s", counts)
    return counts


# ---------------------------------------------------------------------------
# check_customer_state — cross-table state lookup for resume capability
# ---------------------------------------------------------------------------

def check_customer_state(customer_id: str) -> Dict[str, Any]:
    """Query all tables and return the current pipeline position of a customer.

    Used by DiscoveryAgent when a returning customer is identified so the
    conversation can resume where they left off.

    Parameters
    ----------
    customer_id : str
        The ``CUST-YYYYMMDD-XXX`` identifier assigned at Discovery time.

    Returns
    -------
    dict
        JSON-serialisable summary with keys:
        ``customer_id``, ``account``, ``active_quotes``, ``active_carts``,
        ``pending_orders``, ``payments``, ``fulfillments``,
        ``is_activated_customer``.
    """
    result: Dict[str, Any] = {
        "customer_id": customer_id,
        "account": None,
        "active_quotes": [],
        "active_carts": [],
        "pending_orders": [],
        "payments": [],
        "fulfillments": [],
        "is_activated_customer": False,
    }

    conn = get_connection()
    try:
        # --- Account info ---
        row = conn.execute(
            'SELECT "Company Name", Street, City, State, zip_code, '
            '"Existing Customer", customer_id '
            "FROM accounts WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        if row:
            result["account"] = {
                "company_name": row["Company Name"],
                "street": row["Street"],
                "city": row["City"],
                "state": row["State"],
                "zip_code": row["zip_code"],
                "existing_customer": row["Existing Customer"],
            }

        # --- Active quotes (not expired) ---
        for row in conn.execute(
            "SELECT offer_id, company_name, total_price, status, "
            "created_at, expires_at "
            "FROM quotes WHERE customer_id = ? AND status = 'active'",
            (customer_id,),
        ):
            result["active_quotes"].append({
                "offer_id": row["offer_id"],
                "company_name": row["company_name"],
                "total_price": row["total_price"],
                "status": row["status"],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
            })

        # --- Active carts ---
        for row in conn.execute(
            "SELECT cart_id, total_amount, status, created_at "
            "FROM carts WHERE customer_id = ? AND status = 'active'",
            (customer_id,),
        ):
            result["active_carts"].append({
                "cart_id": row["cart_id"],
                "total_amount": row["total_amount"],
                "status": row["status"],
                "created_at": row["created_at"],
            })

        # --- Pending / paid orders ---
        for row in conn.execute(
            "SELECT order_id, offer_id, status, total_amount, created_at "
            "FROM orders WHERE customer_id = ? AND status IN ('draft','pending_payment','paid')",
            (customer_id,),
        ):
            result["pending_orders"].append({
                "order_id": row["order_id"],
                "offer_id": row["offer_id"],
                "status": row["status"],
                "total_amount": row["total_amount"],
                "created_at": row["created_at"],
            })

        # --- Payment status ---
        for row in conn.execute(
            "SELECT payment_id, order_id, status, amount, created_at "
            "FROM payments WHERE customer_id = ? "
            "ORDER BY created_at DESC LIMIT 5",
            (customer_id,),
        ):
            result["payments"].append({
                "payment_id": row["payment_id"],
                "order_id": row["order_id"],
                "status": row["status"],
                "amount": row["amount"],
                "created_at": row["created_at"],
            })

        # --- Fulfillment status ---
        for row in conn.execute(
            "SELECT fulfillment_id, order_id, status, appointment_date, "
            "circuit_id, activation_id "
            "FROM fulfillments WHERE customer_id = ? "
            "ORDER BY created_at DESC LIMIT 5",
            (customer_id,),
        ):
            result["fulfillments"].append({
                "fulfillment_id": row["fulfillment_id"],
                "order_id": row["order_id"],
                "status": row["status"],
                "appointment_date": row["appointment_date"],
                "circuit_id": row["circuit_id"],
                "activation_id": row["activation_id"],
            })

        # --- Activated customer? ---
        cm = conn.execute(
            "SELECT customer_id FROM customer_master WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        result["is_activated_customer"] = cm is not None

    finally:
        conn.close()

    return result

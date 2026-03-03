#!/usr/bin/env python3
"""Quick E2E test for the full sales flow: Discovery→Serviceability→Product→Pricing→Order→Installation→Payment."""

import json
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"


def post(path, body=None, token=None):
    data = json.dumps(body).encode() if body else b""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


def chat(message, token, session_id):
    """Send a chat message and collect the full streamed text response."""
    body = {"message": message, "session_id": session_id}
    raw = post("/api/chat", body, token)
    texts = []
    author = None
    error = None
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("data: "):
            continue
        try:
            d = json.loads(line[6:])
            if d.get("type") == "token" and d.get("text"):
                texts.append(d["text"])
            if d.get("author"):
                author = d["author"]
            if d.get("type") == "error":
                error = d.get("message", "Unknown error")
        except Exception:
            pass
    return "".join(texts), author, error


def step(label, message, token, session_id):
    print(f"\n{'='*60}")
    print(f"STEP: {label}")
    print(f"USER: {message[:80]}{'...' if len(message)>80 else ''}")
    text, author, error = chat(message, token, session_id)
    if error:
        print(f"❌ ERROR: {error}")
    else:
        preview = text[:400].replace("\n", " | ")
        print(f"AGENT ({author}): {preview}{'...' if len(text)>400 else ''}")
        print("✅ OK")
    return text, error


def main():
    # Auth
    sess = json.loads(post("/api/session"))
    token = sess["token"]
    session_id = sess["session_id"]
    print(f"Session: {session_id}")

    # Step 1: Discovery + BANT
    text, err = step(
        "Discovery + BANT",
        "Hi, we are Apex Digital Inc at 1601 Market St, Philadelphia PA 19103. "
        "Technology company, need fiber internet ASAP, budget approved, I am the CEO, within 1 week.",
        token, session_id,
    )
    if err:
        return
    time.sleep(3)

    # Step 2: Contact info (triggers serviceability)
    text, err = step(
        "Contact info + trigger serviceability",
        "Contact: Sam Rivera, CEO, sam@apexdigital.com, 215-555-0400. "
        "Please add contact, create opportunity and check serviceability.",
        token, session_id,
    )
    if err:
        return
    time.sleep(3)

    # Step 3: Product details
    text, err = step(
        "Product details",
        "Show me details for Business Fiber 5 Gbps",
        token, session_id,
    )
    if err:
        return
    time.sleep(3)

    # Step 4: Pricing
    text, err = step(
        "Pricing/quote",
        "Give me a quote for Business Fiber 5 Gbps with a 2 year contract",
        token, session_id,
    )
    if err:
        return
    time.sleep(3)

    # Step 5: Add to cart
    text, err = step(
        "Add to cart / start order",
        "I want to order Business Fiber 5 Gbps. Add it to my cart.",
        token, session_id,
    )
    if err:
        return
    time.sleep(3)

    # Step 6: Schedule installation
    text, err = step(
        "Proceed to schedule installation",
        "No additional items. Please proceed to schedule installation.",
        token, session_id,
    )
    if err:
        return
    # Check if slot list was returned
    if "slot" in text.lower() or "morning" in text.lower() or "afternoon" in text.lower():
        print("✅ Installation slots presented")
    time.sleep(3)

    # Step 7: Pick a slot
    text, err = step(
        "Select installation slot",
        "March 10 morning please",
        token, session_id,
    )
    if err:
        return
    if "scheduled" in text.lower() or "appointment" in text.lower() or "confirmed" in text.lower():
        print("✅ Installation confirmed!")
    time.sleep(3)

    # Step 8: Payment
    text, err = step(
        "Payment",
        "Proceed with payment. Use credit card.",
        token, session_id,
    )
    if err:
        return
    if "approved" in text.lower() or "payment" in text.lower():
        print("✅ Payment processed")
    time.sleep(3)

    # Step 9: Submit order
    text, err = step(
        "Submit order",
        "Yes, submit the order.",
        token, session_id,
    )
    if err:
        return
    if "order" in text.lower() and ("confirm" in text.lower() or "submitted" in text.lower() or "created" in text.lower()):
        print("✅ Order submitted!")

    print(f"\n{'='*60}")
    print("E2E TEST COMPLETE")


if __name__ == "__main__":
    main()

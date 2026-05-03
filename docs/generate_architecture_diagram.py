from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape


WIDTH = 1280
HEIGHT = 900

ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "architecture-diagram-latest.svg"


def esc(text: str) -> str:
    return escape(text)


def rect(x, y, w, h, rx=18, fill="#FFFFFF", stroke="#000000", sw=1, extra="") -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'
    )


def line(x1, y1, x2, y2, stroke="#000000", sw=2, dash="") -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{dash_attr}/>'


def text(x, y, value, size=16, weight=500, fill="#1F2937", anchor="start", family="Inter, Arial, sans-serif", letter_spacing=0) -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
        f'letter-spacing="{letter_spacing}">{esc(value)}</text>'
    )


def tspan(dy, value, size=13, weight=400, fill="#6B7280", family="Inter, Arial, sans-serif") -> str:
    return (
        f'<tspan x="0" dy="{dy}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{esc(value)}</tspan>'
    )


def multiline_text(x, y, lines, size=16, weight=600, fill="#111827", sub_fill="#6B7280") -> str:
    out = [
        f'<text x="{x}" y="{y}" font-family="Inter, Arial, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">'
    ]
    for idx, line_value in enumerate(lines):
        if idx == 0:
            out.append(esc(line_value))
        else:
            out.append(tspan(18, line_value, size=12, weight=400, fill=sub_fill))
    out.append("</text>")
    return "".join(out)


def badge(x, y, label, fill="#F3F4F6", stroke="#D1D5DB", color="#6B7280", w=None) -> str:
    width = w if w is not None else 14 + len(label) * 8.1
    return (
        rect(x, y, width, 28, rx=14, fill=fill, stroke=stroke, sw=1)
        + text(x + width / 2, y + 19, label, size=11, weight=600, fill=color, anchor="middle", family="Menlo, Monaco, monospace", letter_spacing=0.3)
    )


def card(x, y, w, h, title, subtitle, stroke, title_color="#111827", fill="#FFFFFF") -> str:
    pieces = [
        rect(x, y, w, h, rx=12, fill=fill, stroke=stroke, sw=1.5),
        text(x + 18, y + 28, title, size=16, weight=700, fill=title_color),
    ]
    if isinstance(subtitle, list):
        pieces.append(multiline_text(x + 18, y + 50, subtitle, size=12, weight=400, fill="#6B7280", sub_fill="#6B7280"))
    else:
        pieces.append(text(x + 18, y + 50, subtitle, size=12, weight=400, fill="#6B7280"))
    return "".join(pieces)


def agent_box(x, y, w, h, title, title_color, border, items) -> str:
    parts = [
        rect(x, y, w, h, rx=16, fill="#FFFFFF", stroke=border, sw=1.5),
        text(x + 16, y + 26, title, size=11, weight=700, fill=title_color, family="Menlo, Monaco, monospace", letter_spacing=1.2),
    ]
    iy = y + 40
    for item in items:
        parts.append(rect(x + 14, iy, w - 28, 28, rx=8, fill="#FBFDFF", stroke=border, sw=1))
        parts.append(text(x + 28, iy + 19, f"• {item}", size=12, weight=600, fill=title_color))
        iy += 36
    return "".join(parts)


def arrow_down(cx, y1, y2, color="#6366F1") -> str:
    return (
        line(cx, y1, cx, y2 - 12, stroke=color, sw=3)
        + f'<polygon points="{cx-8},{y2-12} {cx+8},{y2-12} {cx},{y2}" fill="{color}"/>'
    )


def arrow_elbow(x1, y1, x2, y2, color="#F59E0B") -> str:
    mid_y = y1 + 18
    return (
        line(x1, y1, x1, mid_y, stroke=color, sw=2.5)
        + line(x1, mid_y, x2, mid_y, stroke=color, sw=2.5)
        + line(x2, mid_y, x2, y2 - 12, stroke=color, sw=2.5)
        + f'<polygon points="{x2-7},{y2-12} {x2+7},{y2-12} {x2},{y2}" fill="{color}"/>'
    )


def build_svg() -> str:
    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">'
    )
    parts.append(
        """
        <defs>
          <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#F8F9FC"/>
            <stop offset="100%" stop-color="#F3F5FA"/>
          </linearGradient>
          <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#0F172A" flood-opacity="0.06"/>
          </filter>
        </defs>
        """
    )
    parts.append(rect(0, 0, WIDTH, HEIGHT, rx=0, fill="url(#bg)", stroke="none", sw=0))
    parts.append(rect(24, 24, WIDTH - 48, HEIGHT - 48, rx=26, fill="#FFFFFF", stroke="#E5E7EB", sw=1.2, extra='filter="url(#shadow)"'))

    parts.append(text(56, 72, "B2B Conversational Sales Agent", size=26, weight=800, fill="#111827"))
    parts.append(text(56, 98, "LATEST MULTI-AGENT ORCHESTRATION ARCHITECTURE", size=12, weight=500, fill="#6B7280", letter_spacing=1.8))

    bx = 650
    for label in ["Google ADK 1.20+", "Gemini 3 Flash", "Python 3.12+", "React 19", "FastAPI", "SQLite WAL"]:
        parts.append(badge(bx, 48, label))
        bx += 14 + len(label) * 8.1 + 8

    # Presentation layer
    parts.append(rect(56, 120, 1168, 96, rx=14, fill="#ECFDF5", stroke="#9AE6B4", sw=1.3))
    parts.append(text(76, 144, "PRESENTATION LAYER", size=11, weight=700, fill="#047857", family="Menlo, Monaco, monospace", letter_spacing=2))
    parts.append(card(76, 160, 150, 36, "B2B Customer", "Natural language requests", "#C7D2FE", "#374151", "#F8FAFC"))
    parts.append(card(240, 152, 330, 56, "React 19 + Vite Client", "Chat UI · streaming messages · activity cards", "#9AE6B4", "#065F46"))
    parts.append(card(584, 152, 290, 56, "FastAPI SSE Server", "Auth · rate limiting · custom ADK streaming", "#9AE6B4", "#065F46"))
    parts.append(card(888, 152, 316, 56, "ADK Runner + InMemorySessionService", "One user message per turn · shared session context", "#9AE6B4", "#065F46"))

    parts.append(arrow_down(640, 216, 238, "#6366F1"))

    # Orchestration layer
    parts.append(rect(56, 242, 1168, 88, rx=14, fill="#EEF2FF", stroke="#C7D2FE", sw=1.3))
    parts.append(text(76, 266, "ORCHESTRATION LAYER", size=11, weight=700, fill="#4338CA", family="Menlo, Monaco, monospace", letter_spacing=2))
    parts.append(rect(76, 282, 540, 34, rx=12, fill="#FFFFFF", stroke="#A5B4FC", sw=1.2))
    parts.append(text(96, 304, "SuperAgent", size=18, weight=800, fill="#1F2A44"))
    parts.append(text(205, 304, "Router-only orchestrator · delegates via ADK transfer_to_agent()", size=13, weight=500, fill="#4F46E5"))
    parts.append(badge(940, 278, "ROUTER", "#F5F3FF", "#C4B5FD", "#6366F1", 86))
    parts.append(badge(1036, 278, "SESSION STATE", "#ECFDF5", "#A7F3D0", "#047857", 112))
    parts.append(badge(1158, 278, "ADK NATIVE", "#FFFBEB", "#FCD34D", "#B45309", 92))
    parts.append(text(96, 322, "Intent analysis · context management · guardrails · multi-turn handoff recovery", size=12, weight=400, fill="#6B7280"))

    # Specialized agents
    parts.append(rect(56, 362, 1168, 240, rx=16, fill="#FFFBEB", stroke="#FCD34D", sw=1.3))
    parts.append(text(76, 386, "SPECIALIZED AGENTS — 10 ACTIVE SUB-AGENTS", size=11, weight=700, fill="#92400E", family="Menlo, Monaco, monospace", letter_spacing=2))

    parts.append(agent_box(76, 402, 372, 176, "DISCOVERY", "#1D4ED8", "#BFDBFE", [
        "DiscoveryAgent",
        "GreetingAgent",
        "FAQAgent",
    ]))
    parts.append(agent_box(468, 402, 372, 176, "CONFIGURATION", "#6D28D9", "#DDD6FE", [
        "ServiceabilityAgent",
        "ProductAgent",
        "OfferManagementAgent",
    ]))
    parts.append(agent_box(860, 402, 344, 176, "TRANSACTION", "#C2410C", "#FED7AA", [
        "OrderAgent",
        "PaymentAgent",
        "ServiceFulfillmentAgent",
        "CustomerCommunicationAgent",
    ]))

    parts.append(arrow_elbow(280, 330, 280, 362, "#F59E0B"))
    parts.append(arrow_elbow(640, 330, 640, 362, "#F59E0B"))
    parts.append(arrow_elbow(1040, 330, 1040, 362, "#F59E0B"))
    parts.append(text(592, 354, "transfer_to_agent()", size=10, weight=500, fill="#B45309", family="Menlo, Monaco, monospace"))

    # Order flow strip
    parts.append(rect(84, 614, 1112, 48, rx=12, fill="#FFF7ED", stroke="#FDBA74", sw=1))
    parts.append(text(104, 636, "PRIMARY SALES FLOW", size=10, weight=700, fill="#9A3412", family="Menlo, Monaco, monospace", letter_spacing=1.6))
    flow = "Discovery → Serviceability → Product → Offer → Order → Scheduling → Payment → Activation"
    parts.append(text(104, 656, flow, size=14, weight=700, fill="#7C2D12"))

    parts.append(arrow_down(640, 602, 634, "#EF4444"))

    # Infrastructure layer
    parts.append(rect(56, 678, 1168, 148, rx=14, fill="#FEF2F2", stroke="#FCA5A5", sw=1.3))
    parts.append(text(76, 702, "INFRASTRUCTURE & DETERMINISTIC TOOLS", size=11, weight=700, fill="#991B1B", family="Menlo, Monaco, monospace", letter_spacing=2))

    parts.append(card(76, 720, 372, 84, "Unified SQLite · sales_agent.db", [
        "accounts · quotes · orders · payments",
        "fulfillments · notifications · customer_master",
    ], "#FCA5A5", "#991B1B"))
    parts.append(card(462, 720, 222, 84, "In-Repo Product Catalog", [
        "Structured catalog +",
        "ChromaDB knowledge",
    ], "#FCA5A5", "#991B1B"))
    parts.append(card(700, 720, 154, 84, "GIS / Coverage API", [
        "Address validation",
        "and serviceability",
    ], "#FCA5A5", "#991B1B"))
    parts.append(card(870, 720, 154, 84, "Pricing Engine", [
        "Deterministic quote",
        "computation",
    ], "#FCA5A5", "#991B1B"))
    parts.append(card(1040, 720, 164, 84, "Payment + Scheduler", [
        "Payment auth · install",
        "scheduling · activation",
    ], "#FCA5A5", "#991B1B"))

    # Footer chips
    chips = [
        "Structured JSON outputs",
        "Importlib isolation",
        "One-message-per-turn flow",
        "Activation creates customer_master",
    ]
    cx = 82
    cy = 852
    for label in chips:
        width = 28 + len(label) * 7.1
        parts.append(rect(cx, cy - 22, width, 26, rx=8, fill="#F3F4F6", stroke="#E5E7EB", sw=1))
        parts.append(text(cx + width / 2, cy - 5, label, size=11, weight=600, fill="#6B7280", anchor="middle", family="Menlo, Monaco, monospace"))
        cx += width + 10

    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    SVG_PATH.write_text(build_svg(), encoding="utf-8")
    print(f"Wrote {SVG_PATH}")


if __name__ == "__main__":
    main()

# SuperAgent – B2B Sales Chat with SSE Streaming

A real-time conversational sales agent built on **Google ADK** and **Gemini 2.0 Flash**.
The server handles all LLM communication; the React client consumes streamed tokens
via Server-Sent Events (SSE) for a native typing effect.

## Architecture

```
SuperAgent/
├── server/                    # Python / FastAPI backend
│   ├── main.py                # Entry point – registers routes, CORS, startup
│   ├── config.py              # All configurable settings (single source of truth)
│   ├── .env.example           # Environment variable template
│   ├── requirements.txt       # Python dependencies
│   ├── agent/                 # Google ADK agent definitions
│   │   ├── agent.py           # Root orchestrator (Super Agent)
│   │   ├── prompts.py         # System message & routing instructions
│   │   ├── sub_agents/        # Specialised sub-agents
│   │   │   ├── greeting_agent.py
│   │   │   ├── product_agent.py
│   │   │   └── faq_agent.py
│   │   └── tools/             # Tools the agent can invoke
│   │       └── sales_tools.py # Mock CRM, catalog, serviceability APIs
│   ├── api/                   # FastAPI route modules
│   │   ├── chat.py            # POST /api/chat – SSE streaming
│   │   └── session.py         # POST/DELETE /api/session
│   ├── middleware/             # Cross-cutting concerns
│   │   ├── auth.py            # Token-based session authentication
│   │   └── rate_limiter.py    # Per-session token-bucket rate limiting
│   └── utils/
│       └── logger.py          # Structured logger with session tracking
│
└── client/                    # React 19 / Vite / Tailwind CSS frontend
    ├── src/
    │   ├── App.jsx            # Root layout
    │   ├── components/        # UI components
    │   │   ├── ChatWindow.jsx
    │   │   ├── ChatInput.jsx
    │   │   ├── MessageBubble.jsx
    │   │   └── TypingIndicator.jsx
    │   ├── hooks/
    │   │   └── useChat.js     # Chat state + SSE streaming hook
    │   ├── utils/
    │   │   └── api.js         # Fetch wrapper for /api/* endpoints
    │   └── styles/
    │       └── index.css      # Tailwind + custom scrollbar / animations
    └── index.html
```

## Key Design Decisions

| Concern | Approach |
|---------|----------|
| **LLM calls** | Server-side only – the client never touches the Gemini API |
| **Streaming** | SSE via `StreamingResponse`; each token is a JSON `data:` event |
| **Auth** | Session tokens issued by `POST /api/session`; validated on every chat request |
| **Rate limiting** | In-memory token-bucket (per-minute + per-hour) per session |
| **Config** | Single `config.py` with `@dataclass(frozen=True)` loaded from env vars |
| **Agent framework** | Google ADK `Agent` class with sub-agents + typed tools |
| **Model** | Gemini 2.0 Flash (free tier) – configurable via `GEMINI_MODEL` |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- A Gemini API key ([Get one free](https://aistudio.google.com/apikey))

### 1. Server

```bash
cd SuperAgent/server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set GOOGLE_API_KEY

python main.py
# Server starts on http://localhost:8000
```

### 2. Client

```bash
cd SuperAgent/client
npm install
npm run dev
# UI starts on http://localhost:3000 (proxied to :8000)
```

### 3. Use

1. Open http://localhost:3000
2. Type a message – the app auto-creates a session
3. Watch tokens stream in real-time

## API Reference

### `POST /api/session`
Creates a new session. Returns `{ session_id, token }`.

### `POST /api/chat`
Streams an LLM response via SSE.

**Headers:** `Authorization: Bearer <token>`

**Body:**
```json
{
  "message": "What internet plans do you offer?",
  "history": [
    { "role": "user", "content": "Hi" },
    { "role": "assistant", "content": "Hello! How can I help?" }
  ]
}
```

**SSE events:**
```
data: {"type": "token", "content": "We offer"}
data: {"type": "token", "content": " three fiber"}
...
data: {"type": "done"}
```

### `DELETE /api/session`
Revokes the current session.

### `GET /health`
Returns `{ status: "ok", agent: "super_sales_agent" }`.

## Configuration

All settings live in `server/config.py` and are overridable via environment
variables. See `server/.env.example` for the full list.

## Adding New Sub-Agents

1. Create `server/agent/sub_agents/your_agent.py`
2. Define an `Agent(...)` instance
3. Import it in `server/agent/agent.py` and add to `_build_sub_agents()`
4. Update routing rules in `server/agent/prompts.py`

## Adding New Tools

1. Create a function in `server/agent/tools/sales_tools.py` (or a new file)
2. Add a docstring – ADK uses it as the tool description for the LLM
3. Register it in the `tools=[...]` list in `server/agent/agent.py`

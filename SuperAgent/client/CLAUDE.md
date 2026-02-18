# Claude Code Instructions - Frontend (React + Vite)

**📖 READ FIRST:** [AGENTS.md](AGENTS.md)

All React/Vite UI development guidelines (Tailwind CSS, state management, SSE) are in AGENTS.md.

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - This file (CLAUDE.md)
   - [AGENTS.md](AGENTS.md)
   - [Root AGENTS.md](/AGENTS.md)

2. **Common tasks → Required reading:**
   - Styling → [AGENTS.md - Styling Rules](AGENTS.md#styling-rules)
   - Components → [AGENTS.md - Component Patterns](AGENTS.md#component-patterns)
   - State → [AGENTS.md - State Management](AGENTS.md#state-management)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## Key Rules

1. **Read AGENTS.md** for complete UI development guide
2. **Tailwind CSS ONLY** - No inline styles, no CSS modules
3. **Functional components** - No class components
4. **React Context** - State management (no Redux/MobX)
5. **SSE** - Server-Sent Events for streaming chat
6. **Test before commit**

---

## Quick Reference

**Tech Stack:** React 19, Vite 6, Tailwind CSS 3.4
**State:** React Context (`contexts/ChatContext.jsx`)
**API:** SSE streaming from `http://localhost:8000/api/chat/stream`
**Dev Server:** `npm run dev` → http://localhost:3000

---

**Primary Reference:** [AGENTS.md](AGENTS.md)
**Root Architecture:** [/AGENTS.md](/AGENTS.md)
**Backend API:** [/SuperAgent/server/](/SuperAgent/server/)

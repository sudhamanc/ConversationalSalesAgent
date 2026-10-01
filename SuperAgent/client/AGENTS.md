# Frontend Development Guidelines

**Location:** `SuperAgent/client/`

**Parent Context:** [/AGENTS.md](/AGENTS.md) | [/CLAUDE.md](/CLAUDE.md)

---

## 🔴 MANDATORY: Documentation-First Approach

**BEFORE making ANY changes (config, code, structure), you MUST:**

1. **Read the documentation first** - in this order:
   - [Root CLAUDE.md](/CLAUDE.md)
   - [Root AGENTS.md](/AGENTS.md)
   - This file (client/AGENTS.md)

2. **Common tasks → Required reading:**
   - Styling changes → This file (see Styling Rules section)
   - Component development → This file (see Component Patterns section)
   - State management → This file (see State Management section)

3. **DO NOT "explore to figure it out"** - The documentation exists to prevent this!

---

## 🎨 Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 19.0.0 | UI framework - functional components + hooks |
| **Vite** | 6.0.0 | Build tool + dev server |
| **Tailwind CSS** | 3.4.17 | Utility-first styling |
| **SSE (Server-Sent Events)** | Native | Real-time message streaming from backend |

**No Redux, No MobX, No Zustand** - Use React Context for state management.

---

## 📁 Project Structure

```
client/
├── src/
│   ├── App.jsx                     # Root layout: journey sidebar, chat, cart panel
│   ├── main.jsx                    # React entry point
│   ├── components/
│   │   ├── ChatWindow.jsx          # Message list + streaming reply
│   │   ├── ChatInput.jsx           # User input field
│   │   ├── MessageBubble.jsx       # Message display (agent label, markdown)
│   │   ├── TypingIndicator.jsx     # Loading state
│   │   ├── SuggestionCard.jsx      # Suggested next replies
│   │   ├── JourneySidebar.jsx      # Sales journey progress (JourneyStep.jsx)
│   │   ├── CartPanel.jsx           # Cart (CartItem.jsx)
│   │   └── *Card.jsx               # Structured cards: Serviceability, ProductDetails, Quote, Order, Payment
│   ├── contexts/ChatContext.jsx    # Chat, cart and journey state (useChatContext)
│   ├── hooks/useChat.js            # Chat actions hook
│   ├── styles/index.css            # Tailwind imports
│   └── utils/
│       ├── api.js                  # Session + streaming chat client (see API Communication)
│       ├── remoteLog.js            # Forwards client logs to /api/client-log
│       ├── agentLabels.js          # Agent display names
│       ├── responseFormatters.js   # Reply formatting
│       ├── suggestions.js          # Suggestion helpers
│       └── pdfExport.js            # Quote/order PDF export
├── index.html                      # HTML entry point
├── package.json                    # Dependencies
├── vite.config.js                  # Vite config (proxies /api to :8000)
└── tailwind.config.js              # Tailwind configuration
```

---

## 🎨 Styling Rules

### Tailwind CSS Only

**DO:**
```jsx
<div className="flex items-center gap-3 px-6 py-4 bg-white rounded-lg shadow-md">
  <p className="text-sm text-slate-600">Message</p>
</div>
```

**DON'T:**
```jsx
// ❌ Inline styles (avoid)
<div style={{ display: 'flex', padding: '16px' }}>

// ❌ CSS modules (not configured)
<div className={styles.container}>

// ❌ Styled-components (not in stack)
const Container = styled.div`...`
```

### Color Palette

**Defined in `tailwind.config.js`:**

```javascript
colors: {
  primary: {
    50: '#eff6ff',
    100: '#dbeafe',
    // ...
    600: '#2563eb',  // Primary brand color
    // ...
  },
  slate: { /* Neutrals */ },
}
```

**Usage:**
- **Primary actions:** `bg-primary-600 text-white`
- **Text:** `text-slate-900` (headings), `text-slate-600` (body)
- **Borders:** `border-slate-200`
- **Backgrounds:** `bg-slate-50` (light), `bg-white`

### Responsive Design

**Breakpoints:**
```javascript
sm: '640px',   // Mobile landscape
md: '768px',   // Tablet
lg: '1024px',  // Desktop
xl: '1280px',  // Large desktop
```

**Usage:**
```jsx
<div className="w-full md:w-1/2 lg:w-1/3">
  {/* Full width on mobile, half on tablet, third on desktop */}
</div>
```

### Design System

**Spacing:**
- Padding/Margin: `p-4` (16px), `px-6` (24px horizontal), `gap-3` (12px)
- Standard unit: 4px increments (4, 8, 12, 16, 24, 32, 48, 64)

**Typography:**
- Headings: `text-lg font-semibold` (18px, 600 weight)
- Body: `text-sm` (14px) or `text-base` (16px)
- Small text: `text-xs` (12px)

**Shadows:**
- Cards: `shadow-xl`
- Hover states: `hover:shadow-2xl`
- Subtle: `shadow-md`

**Borders:**
- Rounded corners: `rounded-lg` (8px), `rounded-2xl` (16px)
- Border width: `border` (1px), `border-2` (2px)

---

## ⚛️ Component Guidelines

### Functional Components Only

**DO:**
```jsx
export default function ChatWindow() {
  const [messages, setMessages] = useState([]);

  return (
    <div className="flex-1 overflow-y-auto">
      {messages.map(msg => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
    </div>
  );
}
```

**DON'T:**
```jsx
// ❌ No class components
class ChatWindow extends React.Component { ... }
```

### Prop Types (Optional but Recommended)

```jsx
/**
 * Message bubble component
 * @param {Object} props
 * @param {Object} props.message - Message object
 * @param {string} props.message.text - Message text
 * @param {string} props.message.sender - 'user' or 'agent'
 */
export default function MessageBubble({ message }) {
  const isUser = message.sender === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`max-w-[70%] px-4 py-2 rounded-lg ${
        isUser ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-900'
      }`}>
        {message.text}
      </div>
    </div>
  );
}
```

### Component Naming

- **Files:** PascalCase (`ChatWindow.jsx`, `MessageBubble.jsx`)
- **Components:** Same as file name (`function ChatWindow() {}`)
- **Props:** camelCase (`isLoading`, `onSend`)

---

## 🔌 State Management

### React Context Pattern

**Create Context:**
```jsx
// contexts/ChatContext.jsx
import { createContext, useContext, useState } from 'react';

const ChatContext = createContext();

export function ChatProvider({ children }) {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);

  const addMessage = (message) => {
    setMessages(prev => [...prev, { ...message, id: Date.now() }]);
  };

  return (
    <ChatContext.Provider value={{ messages, addMessage, isConnected, setIsConnected }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) throw new Error('useChat must be used within ChatProvider');
  return context;
}
```

**Use Context:**
```jsx
// components/ChatWindow.jsx
import { useChat } from '../contexts/ChatContext';

export default function ChatWindow() {
  const { messages, isConnected } = useChat();

  return (
    <div>
      {!isConnected && <p>Connecting...</p>}
      {messages.map(msg => <MessageBubble key={msg.id} message={msg} />)}
    </div>
  );
}
```

### Local State (useState)

**For component-specific state only:**
```jsx
function ChatInput({ onSend }) {
  const [input, setInput] = useState('');  // Input field value

  const handleSubmit = () => {
    if (input.trim()) {
      onSend(input);
      setInput('');
    }
  };

  return (
    <input
      value={input}
      onChange={(e) => setInput(e.target.value)}
      onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
    />
  );
}
```

---

## 🌐 API Communication

All calls go through `src/utils/api.js` with relative URLs (`/api/...`); the Vite dev server proxies `/api` to the gateway on `:8000`, and in containers the gateway serves the built UI itself. Never hardcode `http://localhost:8000`.

1. **Session:** `POST /api/session` with `{client_id}` returns a bearer `token` (cached by `getToken()`).
2. **Chat:** `streamChat(message, callbacks...)` sends `POST /api/chat` with `Authorization: Bearer <token>` and body `{message}`. The response is an SSE stream read with `res.body.getReader()` (not `EventSource`, which cannot POST). A `401` creates a new session and retries once.
3. **Events** (`data: {...}` lines):

| `type` | Handler | Meaning |
|---|---|---|
| `token` | `onToken(content, author)` | Streamed reply text; `author` is the answering agent |
| `cart_update` | `onCartUpdate(data)` | Cart contents changed |
| `activity_update` | `onActivityUpdate(payload)` | Agent/tool activity for the activity panel |
| `structured_card` | `onStructuredCard(...)` | Rich card (products, quote, order, ...) |
| `suggestions` | `onSuggestions(...)` | Suggested next replies |
| `error` | `onError(message)` | Agent or model failure (e.g. Gemini quota `429`) |
| `done` | `onDone()` | Turn finished |

Client logs are forwarded with `src/utils/remoteLog.js` to `POST /api/client-log`.

---

## 🧪 Testing (Future)

**Recommended Tools:**
- **Unit/Integration:** Vitest + React Testing Library
- **E2E:** Playwright

**Example Test:**
```jsx
// tests/ChatWindow.test.jsx
import { render, screen } from '@testing-library/react';
import ChatWindow from '../src/components/ChatWindow';

test('renders empty chat', () => {
  render(<ChatWindow />);
  expect(screen.queryByRole('article')).not.toBeInTheDocument();
});
```

---

## 📋 Code Style

### Imports

**Order:**
1. React imports
2. Third-party libraries
3. Local components
4. Utils/hooks
5. Styles (if any)

```jsx
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';  // if used

import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';

import { useChat } from '../hooks/useChat';
import { formatTimestamp } from '../utils/date';
```

### Conditional Rendering

**Short conditions:**
```jsx
{isLoading && <TypingIndicator />}
{error && <ErrorMessage text={error} />}
```

**Complex conditions:**
```jsx
{isConnected ? (
  <ChatWindow messages={messages} />
) : (
  <ConnectionError onRetry={reconnect} />
)}
```

### Event Handlers

**Naming:** `handle[Event]` or `on[Event]`

```jsx
function ChatInput({ onSend }) {
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    onSend(input);
    setInput('');
  };

  return <input onKeyPress={handleKeyPress} />;
}
```

---

## 🎯 UI/UX Guidelines

### Message Display

**User messages:** Right-aligned, primary color background
**Agent messages:** Left-aligned, light gray background

```jsx
<div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
  <div className={`max-w-[70%] px-4 py-2 rounded-lg ${
    isUser
      ? 'bg-primary-600 text-white rounded-br-none'
      : 'bg-slate-100 text-slate-900 rounded-bl-none'
  }`}>
    {message.text}
  </div>
</div>
```

### Loading States

**Typing indicator:**
```jsx
export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-lg w-fit">
      <div className="flex gap-1">
        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" />
        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-100" />
        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-200" />
      </div>
      <span className="text-sm text-slate-500">SuperAgent is typing...</span>
    </div>
  );
}
```

### Input Field

**Auto-focus, auto-resize (optional), Enter to send:**
```jsx
<textarea
  ref={inputRef}
  value={input}
  onChange={(e) => setInput(e.target.value)}
  onKeyPress={handleKeyPress}
  placeholder="Type your message..."
  className="flex-1 resize-none border-none outline-none text-sm"
  rows={1}
  autoFocus
/>
```

---

## 🚨 Common Pitfalls

### 1. Stream Not Fully Consumed

**Symptom:** Missing final tokens, or the UI stays "typing" after a reply

**Fix:** Keep the partial last line in a buffer between reads (`buffer = lines.pop()`), and always end the turn on `done` *or* `error`, as `streamChat` in `src/utils/api.js` does.

### 2. Infinite Re-renders

**Symptom:** UI freezes, console errors

**Cause:** Missing dependency array in `useEffect` or `useCallback`

**Fix:**
```jsx
// ❌ BAD
useEffect(() => {
  fetchData();
});  // Runs on every render

// ✅ GOOD
useEffect(() => {
  fetchData();
}, []);  // Runs once on mount
```

### 3. State Not Updating

**Symptom:** UI doesn't reflect state changes

**Cause:** Mutating state directly

**Fix:**
```jsx
// ❌ BAD
messages.push(newMessage);
setMessages(messages);

// ✅ GOOD
setMessages([...messages, newMessage]);
```

### 4. Prop Drilling

**Symptom:** Passing props through many layers

**Fix:** Use Context for deeply nested shared state:
```jsx
// ❌ BAD
<App>
  <Header user={user} />
  <ChatWindow user={user}>
    <MessageList user={user} />
  </ChatWindow>
</App>

// ✅ GOOD
<UserContext.Provider value={user}>
  <App>
    <Header />
    <ChatWindow>
      <MessageList />  {/* useContext(UserContext) inside */}
    </ChatWindow>
  </App>
</UserContext.Provider>
```

---

## 🛠️ Development Workflow

### Local Development

```bash
cd SuperAgent/client
npm run dev
```

**Access:** http://localhost:3000

**Hot Reload:** Vite auto-reloads on file save

### Build for Production

```bash
npm run build
```

**Output:** `dist/` folder with optimized static files

### Preview Production Build

```bash
npm run preview
```

---

## 🤖 Automatic Welcome Message

On session start, `ChatContext.jsx` automatically sends a hidden `"hi"` message to the backend (without showing a user bubble) and streams the GreetingAgent's response as the first assistant message. This provides immediate engagement without requiring the user to type anything.

**Implementation:** `useEffect` in `ChatContext.jsx` calls `streamChat("hi", ...)` on mount, streaming the response as an assistant message. A `cancelled` flag prevents double-fire in React strict mode.

---

## 📖 Reference Files

**Best Examples:**

1. **ChatWindow.jsx** - SSE integration, message display
2. **ChatInput.jsx** - User input, event handling
3. **MessageBubble.jsx** - Conditional styling, props
4. **App.jsx** - Layout structure, Tailwind usage

---

## ✅ Component Checklist

Before committing a new component:

- [ ] **Functional component** (no class components)
- [ ] **Tailwind CSS only** (no inline styles)
- [ ] **PropTypes documented** (JSDoc comments)
- [ ] **Event handlers** named `handle[Event]`
- [ ] **Responsive design** (mobile-first with Tailwind breakpoints)
- [ ] **Accessibility** (ARIA labels where needed)
- [ ] **Error boundaries** (for critical components)
- [ ] **Loading states** (skeleton or spinner)
- [ ] **Cleanup** (`useEffect` return cleanup function)

---

**Parent Documentation:** [/CLAUDE.md](/CLAUDE.md) - Project-wide guidelines
**Backend API:** `SuperAgent/server/` - FastAPI endpoints

/**
 * Remote logging shim.
 *
 * Wraps console.log/warn/error/info so each call is also POSTed to the
 * backend's /api/client-log, which appends to SuperAgent/logs/frontend.log.
 * Original console behavior is preserved (logs still appear in DevTools).
 *
 * Also forwards uncaught errors and unhandled promise rejections.
 */

const ENDPOINT = "http://localhost:8000/api/client-log";

const ORIGINAL = {
  log: console.log.bind(console),
  warn: console.warn.bind(console),
  error: console.error.bind(console),
  info: console.info.bind(console),
};

function safeStringify(value) {
  if (value instanceof Error) {
    return `${value.name}: ${value.message}\n${value.stack || ""}`;
  }
  if (typeof value === "object" && value !== null) {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

function send(level, args) {
  try {
    const message = args.map(safeStringify).join(" ").slice(0, 4000);
    fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        level,
        message,
        timestamp: new Date().toISOString(),
      }),
      keepalive: true,
    }).catch(() => {});
  } catch {
    /* swallow — never let logging break the app */
  }
}

let installed = false;

export function setupRemoteLogging() {
  if (installed) return;
  installed = true;

  ["log", "warn", "error", "info"].forEach((level) => {
    console[level] = (...args) => {
      ORIGINAL[level](...args);
      send(level, args);
    };
  });

  window.addEventListener("error", (event) => {
    send("error", [
      `Uncaught: ${event.message}`,
      `at ${event.filename}:${event.lineno}:${event.colno}`,
      event.error,
    ]);
  });

  window.addEventListener("unhandledrejection", (event) => {
    send("error", ["Unhandled promise rejection:", event.reason]);
  });
}

/**
 * `--a2ui-*` values for generated surfaces, matching the app's Tailwind
 * palette (tailwind.config.js `primary` = blue, slate text, rounded-2xl cards).
 * Passed as `generativeUI.theme`; CopilotKit sets them on each surface root.
 */
export const salesTheme = {
  "--a2ui-color-accent": "#2563eb", // primary-600
  "--a2ui-color-on-accent": "#ffffff",
  "--a2ui-color-focus": "#3b82f6", // primary-500
  "--a2ui-color-text-default": "#1e293b", // slate-800
  "--a2ui-color-text-prose": "#1e293b",
  "--a2ui-color-text-emphasis": "#0f172a", // slate-900
  "--a2ui-color-text-primary": "#1d4ed8", // primary-700
  "--a2ui-color-text-secondary": "#64748b", // slate-500
  "--a2ui-color-text-tertiary": "#94a3b8", // slate-400
  "--a2ui-color-surface": "#ffffff",
  "--a2ui-color-surface-secondary": "#f8fafc", // slate-50
  "--a2ui-color-surface-soft": "#f1f5f9", // slate-100
  "--a2ui-color-panel": "#ffffff",
  "--a2ui-color-border-default": "#e2e8f0", // slate-200
  "--a2ui-color-border-subtle": "#f1f5f9",
  "--a2ui-color-border-strong": "#cbd5e1", // slate-300
  "--a2ui-color-info-soft": "#dbeafe", // primary-100
  "--a2ui-radius-sm": "0.5rem",
  "--a2ui-radius-md": "0.75rem",
  "--a2ui-radius-lg": "1rem", // rounded-2xl
  "--a2ui-radius-xl": "1rem",
  "--a2ui-font-family":
    'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
};

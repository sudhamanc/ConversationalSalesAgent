/**
 * Shows a customer's click on a gateway-built A2UI surface (spec: generative-ui,
 * acted surfaces show completion).
 *
 * A surface arrives as `operations` (one `createSurface`). Each click adds an
 * entry to the surface's action history: `{button, label, status}` with status
 * `pending` (the turn is running), `done` or `failed`. `actedOperations` returns
 * the original operations plus one A2UI 1.0 `updateComponents` per history entry,
 * so the list only ever grows: CopilotKit's runtime (`manager.ingest`) applies the
 * new operations in place and keeps the data model (the contact card's typed
 * values). A list that did not extend the previous one would recreate the surface.
 *
 * - pending: clicked Button highlighted and loading, every other Button and input
 *   disabled, badge "Sending…"
 * - done: clicked Button highlighted with a check icon, the rest disabled, badge
 *   "Saved" (contact card) or "Selected: <label>"
 * - failed: the original components again (clickable), badge removed
 * - closed: the step was completed without a click on this surface (e.g. the
 *   order was placed in the turn that showed the cart): no Button highlighted,
 *   everything disabled, badge `label` ("Order placed"); see `closedEntry`
 *
 * Pure functions, no React: tested with `node --test` (actedSurface.test.js).
 */

export const SEND_FUNCTION = "sendChatMessage";
export const STATUS_BADGE_ID = "acted-status";
/** A Row around the badge keeps it compact (a Card's direct children stretch). */
export const STATUS_ROW_ID = "acted-status-row";
const ROOT_ID = "root";
const A2UI_VERSION = "1.0";

/** Standard-catalog inputs that take `disabled`. */
const INPUTS = new Set([
  "TextField", "TextArea", "Select", "CheckBox", "Radio", "RadioGroup",
  "Slider", "SegmentedControl", "ChoicePicker", "DateTimeInput",
]);

function createOf(operations) {
  const first = Array.isArray(operations) ? operations[0] : null;
  return first && first.createSurface ? first.createSurface : null;
}

/** The text a Button shows (labels are plain strings in gateway-built surfaces). */
export function buttonLabel(operations, buttonId) {
  const create = createOf(operations);
  const node = create?.components?.find((n) => n.id === buttonId && n.component === "Button");
  const label = node?.label ?? node?.text;
  return typeof label === "string" ? label : "";
}

/** History entry that closes a surface whose step was completed elsewhere. */
export function closedEntry(label) {
  return { button: null, label, status: "closed" };
}

function badgeLabel(entry, kind) {
  if (entry.status === "pending") return "Sending…";
  if (entry.status === "closed") return entry.label || "Done";
  if (kind === "contact") return "Saved";
  return entry.label ? `Selected: ${entry.label}` : "Done";
}

function updateFor(create, entry, kind) {
  const changed = [];
  for (const node of create.components || []) {
    if (entry.status === "failed") {
      if (node.component === "Button" || INPUTS.has(node.component) || node.id === ROOT_ID) changed.push(node);
      continue;
    }
    if (node.component === "Button") {
      if (node.id === entry.button) {
        const chosen = { ...node, variant: "primary", disabled: true };
        if (entry.status === "pending") chosen.loading = true;
        else chosen.icon = "check";
        changed.push(chosen);
      } else {
        changed.push({ ...node, variant: node.variant === "primary" ? "default" : node.variant, disabled: true });
      }
    } else if (INPUTS.has(node.component)) {
      changed.push({ ...node, disabled: true });
    } else if (node.id === ROOT_ID) {
      // The badge goes right under the card's title (its first child).
      const children = (node.children || []).filter((c) => c !== STATUS_ROW_ID);
      changed.push({ ...node, children: [...children.slice(0, 1), STATUS_ROW_ID, ...children.slice(1)] });
    }
  }
  if (entry.status !== "failed") {
    changed.push({ id: STATUS_ROW_ID, component: "Row", children: [STATUS_BADGE_ID] });
    changed.push({
      id: STATUS_BADGE_ID,
      component: "Badge",
      label: badgeLabel(entry, kind),
      color: entry.status === "pending" ? "info" : "success",
    });
  }
  return { version: A2UI_VERSION, updateComponents: { surfaceId: create.surfaceId, components: changed } };
}

/**
 * `operations` plus one `updateComponents` per entry of `history`
 * (`[{button, label, status}]`, oldest first). Unchanged when there is no history.
 */
export function actedOperations(operations, history, kind) {
  const create = createOf(operations);
  if (!create || !Array.isArray(history) || history.length === 0) return operations;
  return [...operations, ...history.map((entry) => updateFor(create, entry, kind))];
}

/** True while the surface's last click has not been answered or failed. */
export function isLocked(history) {
  const last = Array.isArray(history) && history.length ? history[history.length - 1] : null;
  return Boolean(last && last.status !== "failed");
}

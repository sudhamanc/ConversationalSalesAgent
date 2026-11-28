// node --test: acted surfaces (spec: generative-ui, acted surfaces show completion).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { actedOperations, buttonLabel, closedEntry, isLocked, STATUS_BADGE_ID, STATUS_ROW_ID } from "./actedSurface.js";

const CATALOG = JSON.parse(
  readFileSync(new URL("../../../server/a2ui/catalog.json", import.meta.url), "utf8")
).components;

const send = (message, button) => ({
  functionCall: { "@call": "sendChatMessage", args: { message, surface: "slots-1", button } },
});

const SLOTS = [
  {
    version: "1.0",
    createSurface: {
      surfaceId: "slots-1",
      components: [
        { id: "root", component: "Card", children: ["title-1", "row-4"] },
        { id: "title-1", component: "Title", text: "Choose an installation time", size: "lg" },
        { id: "button-2", component: "Button", label: "8 AM–12 PM", variant: "primary", onClick: send("Book 8", "button-2") },
        { id: "button-3", component: "Button", label: "1 PM–5 PM", onClick: send("Book 1", "button-3") },
        { id: "row-4", component: "Row", children: ["button-2", "button-3"] },
      ],
    },
  },
];

const CONTACT = [
  {
    version: "1.0",
    createSurface: {
      surfaceId: "contact-1",
      dataModel: { contact: { name: "", email: "", phone: "" } },
      components: [
        { id: "root", component: "Card", children: ["title-1", "textfield-2", "button-3"] },
        { id: "title-1", component: "Title", text: "Where should we send your quote?", size: "lg" },
        { id: "textfield-2", component: "TextField", label: "Email", value: { "@path": "/contact/email" } },
        { id: "button-3", component: "Button", label: "Save contact details", variant: "primary",
          onClick: send({ "@call": "formatString", args: { value: "x" } }, "button-3") },
      ],
    },
  },
];

const nodesOf = (op) => Object.fromEntries(op.updateComponents.components.map((n) => [n.id, n]));

function assertCatalogValid(node) {
  const props = CATALOG[node.component]?.properties;
  assert.ok(props, `${node.component} is in the catalog`);
  for (const key of Object.keys(node)) {
    if (key !== "id") assert.ok(key in props, `${node.component}.${key} is a catalog prop`);
  }
}

test("no history leaves the operations unchanged", () => {
  assert.equal(actedOperations(SLOTS, [], "scheduling"), SLOTS);
  assert.equal(actedOperations(SLOTS, undefined, "scheduling"), SLOTS);
});

test("pending: chosen button loads, others disabled, badge Sending…", () => {
  const ops = actedOperations(SLOTS, [{ button: "button-3", label: "1 PM–5 PM", status: "pending" }], "scheduling");
  assert.equal(ops.length, 2);
  assert.equal(ops[0], SLOTS[0], "the original createSurface is kept, so the list extends the previous one");
  const n = nodesOf(ops[1]);
  assert.equal(ops[1].updateComponents.surfaceId, "slots-1");
  assert.deepEqual([n["button-3"].variant, n["button-3"].disabled, n["button-3"].loading], ["primary", true, true]);
  assert.deepEqual([n["button-2"].variant, n["button-2"].disabled], ["default", true]);
  assert.equal(n[STATUS_BADGE_ID].label, "Sending…");
  assert.deepEqual(n.root.children, ["title-1", STATUS_ROW_ID, "row-4"]);
  assert.deepEqual(n[STATUS_ROW_ID].children, [STATUS_BADGE_ID]);
  Object.values(n).forEach(assertCatalogValid);
});

test("done: the later slot is the only highlighted one, with a check", () => {
  const history = [
    { button: "button-3", label: "1 PM–5 PM", status: "pending" },
    { button: "button-3", label: "1 PM–5 PM", status: "done" },
  ];
  const ops = actedOperations(SLOTS, history, "scheduling");
  assert.equal(ops.length, 3, "one update per history entry: the list only grows");
  const n = nodesOf(ops[2]);
  assert.equal(n["button-3"].icon, "check");
  assert.equal(n["button-3"].loading, undefined);
  assert.equal(n["button-2"].variant, "default", "the gateway's default is no longer highlighted");
  assert.deepEqual(n[STATUS_BADGE_ID], { id: STATUS_BADGE_ID, component: "Badge", label: "Selected: 1 PM–5 PM", color: "success" });
  Object.values(n).forEach(assertCatalogValid);
});

test("failed: original components restored and badge dropped from the card", () => {
  const history = [
    { button: "button-3", label: "1 PM–5 PM", status: "pending" },
    { button: "button-3", label: "1 PM–5 PM", status: "failed" },
  ];
  const n = nodesOf(actedOperations(SLOTS, history, "scheduling")[2]);
  const original = Object.fromEntries(SLOTS[0].createSurface.components.map((c) => [c.id, c]));
  assert.deepEqual(n["button-2"], original["button-2"]);
  assert.deepEqual(n["button-3"], original["button-3"]);
  assert.deepEqual(n.root, original.root);
  assert.equal(n[STATUS_BADGE_ID], undefined);
  assert.equal(isLocked(history), false);
});

test("contact card: fields disabled, badge Saved, data model untouched", () => {
  const history = [{ button: "button-3", label: "Save contact details", status: "done" }];
  const ops = actedOperations(CONTACT, history, "contact");
  const n = nodesOf(ops[1]);
  assert.equal(n["textfield-2"].disabled, true);
  assert.deepEqual(n["textfield-2"].value, { "@path": "/contact/email" }, "typed values stay bound");
  assert.equal(n[STATUS_BADGE_ID].label, "Saved");
  assert.equal(ops[1].updateComponents.dataModel, undefined);
  assert.equal(isLocked(history), true);
  Object.values(n).forEach(assertCatalogValid);
});

test("buttonLabel reads the clicked button's text", () => {
  assert.equal(buttonLabel(SLOTS, "button-3"), "1 PM–5 PM");
  assert.equal(buttonLabel(SLOTS, "nope"), "");
});

test("closed: step completed elsewhere, no button highlighted, badge names the outcome", () => {
  const history = [closedEntry("Order placed")];
  const n = nodesOf(actedOperations(SLOTS, history, "cart")[1]);
  assert.deepEqual([n["button-2"].variant, n["button-2"].disabled], ["default", true]);
  assert.deepEqual([n["button-3"].variant, n["button-3"].disabled], [undefined, true]);
  assert.equal(n["button-2"].icon, undefined);
  assert.deepEqual(n[STATUS_BADGE_ID], { id: STATUS_BADGE_ID, component: "Badge", label: "Order placed", color: "success" });
  assert.equal(isLocked(history), true);
  Object.values(n).forEach(assertCatalogValid);
});

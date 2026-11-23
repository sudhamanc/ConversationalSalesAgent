// Export the sales chat's A2UI 1.0 catalog (standard catalog + SecurePaymentForm +
// sendChatMessage) to SuperAgent/server/a2ui/catalog.json. Gateway tests validate
// the surfaces built in SuperAgent/server/api/a2ui.py against it.
//
// salesUI imports a JSX component, so it is loaded through Vite's SSR loader.
// Run from SuperAgent/client:  npm run export:a2ui-catalog
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const out = resolve(root, "../server/a2ui/catalog.json");

const vite = await createServer({ root, configFile: resolve(root, "vite.config.js"), server: { middlewareMode: true }, appType: "custom", logLevel: "error" });
try {
  const { exportA2UICatalog } = await vite.ssrLoadModule("@copilotkit/react-core/v2/generative-ui");
  const { salesUI, SALES_UI_ID } = await vite.ssrLoadModule("/src/a2ui/salesUI.js");
  const catalog = exportA2UICatalog(salesUI, {
    title: "Connectivity Max sales chat",
    description: `A2UI catalog ${SALES_UI_ID}: CopilotKit standard catalog plus SecurePaymentForm and sendChatMessage.`,
  });
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, JSON.stringify(catalog, null, 2) + "\n");
  console.log(`Wrote ${Object.keys(catalog.components).length} components, ${Object.keys(catalog.functions).length} functions to ${out}`);
} finally {
  await vite.close();
}

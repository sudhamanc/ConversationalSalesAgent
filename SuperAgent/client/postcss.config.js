import tailwindcss from "tailwindcss";
import autoprefixer from "autoprefixer";

/**
 * Tailwind 3 runs on the app's own CSS only. Vendor stylesheets under
 * node_modules (e.g. CopilotKit's `v2/styles.css`, already compiled with
 * Tailwind 4 and native `@layer` rules) pass through untouched.
 */
function appOnly(plugin) {
  const inner = plugin.plugins || [plugin];
  return {
    postcssPlugin: `${plugin.postcssPlugin}-app-only`,
    plugins: inner.map((fn) => (root, result) => {
      const file = result.opts.from || root.source?.input?.file || "";
      if (file.includes("node_modules")) return undefined;
      return fn(root, result);
    }),
  };
}
appOnly.postcss = true;

export default {
  plugins: [appOnly(tailwindcss()), autoprefixer()],
};

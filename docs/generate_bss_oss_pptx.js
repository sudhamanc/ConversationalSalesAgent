const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Sudhaman Chandrasekaran";
pres.title = "Standard vs. Custom BSS/OSS Pattern";

// ── Color Palette: Midnight Executive ──
const C = {
  navy:      "0F2B46",
  midBlue:   "1B6B93",
  teal:      "17A2B8",
  ice:       "E8F4FD",
  white:     "FFFFFF",
  offWhite:  "F4F7FA",
  charcoal:  "2D3748",
  slate:     "64748B",
  lightGray: "E2E8F0",
  accent:    "F59E0B",   // amber for callouts
};

// ── Reusable style factories (never reuse objects – skill rule) ──
const makeShadow = () => ({
  type: "outer", blur: 6, offset: 2, angle: 135, color: "000000", opacity: 0.12,
});

// ── Slide 1: Title ──
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  // Accent bar at top
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.teal },
  });

  s.addText("Standard vs. Custom", {
    x: 0.8, y: 1.2, w: 8.4, h: 1.0,
    fontSize: 44, fontFace: "Trebuchet MS", bold: true,
    color: C.white, align: "left", margin: 0,
  });
  s.addText("BSS / OSS Pattern", {
    x: 0.8, y: 2.1, w: 8.4, h: 0.8,
    fontSize: 36, fontFace: "Trebuchet MS", bold: false,
    color: C.teal, align: "left", margin: 0,
  });

  // Divider line
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 3.1, w: 2.5, h: 0.04, fill: { color: C.accent },
  });

  s.addText("Comcast Business  |  CBIT Enterprise Architecture", {
    x: 0.8, y: 3.5, w: 8.4, h: 0.5,
    fontSize: 14, fontFace: "Calibri", color: C.slate,
    align: "left", margin: 0,
  });

  s.addText("April 2026", {
    x: 0.8, y: 4.8, w: 8.4, h: 0.4,
    fontSize: 12, fontFace: "Calibri", italic: true,
    color: C.slate, align: "left", margin: 0,
  });
}

// ── Slide 2: SOW++ Executive Slide ──
{
  const s = pres.addSlide();
  s.background = { color: C.white };

  // Comcast Business colors for this slide
  const CB = {
    navy: "0C2340", blue: "0047BB", orange: "FF5500",
    orangeLight: "FFF4ED", orangeBadge: "FFE8D6", orangeText: "993300",
    blueLight: "E8F0FC", blueBadge: "D1E2F9", blueText: "003382",
    grayLight: "F0F3F7", grayBadge: "D6DEE8",
    greenLight: "ECFDF5", greenBadge: "D1FAE5", greenText: "065F46",
    green: "059669", greenBorder: "10B981",
    text: "334155", textSecondary: "475569", textDark: "1e293b",
    footerGray: "64748b", border: "e2e8f0",
  };

  // ─ Header bar (navy gradient approximated as solid navy)
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.72, fill: { color: CB.navy },
  });
  s.addText([
    { text: "SOW", options: { fontSize: 18, fontFace: "Source Sans 3", bold: true, color: C.white } },
    { text: "++", options: { fontSize: 18, fontFace: "Source Sans 3", bold: true, color: CB.orange } },
    { text: " — Standards-Led Acceleration", options: { fontSize: 18, fontFace: "Source Sans 3", bold: true, color: C.white } },
  ], {
    x: 0.5, y: 0.08, w: 7.0, h: 0.35, margin: 0,
  });
  s.addText("Addressing Custom Enterprise Quoting Gaps", {
    x: 0.5, y: 0.38, w: 7.0, h: 0.25,
    fontSize: 11, fontFace: "Source Sans 3", color: "BBCEE0", margin: 0,
  });
  s.addText("Q1 2026 Readout\nSDD Demo", {
    x: 7.8, y: 0.12, w: 2.0, h: 0.5,
    fontSize: 10, fontFace: "Source Sans 3", color: "94A3B8",
    align: "right", margin: 0,
  });

  // ─ Quadrant grid (2x2) ─
  const qLeft = 0, qMid = 5.0, qTop = 0.72, qMidY = 2.88;
  const qW = 5.0, qH = 2.16;

  // Q1: Catalyst (top-left, orange tint)
  s.addShape(pres.shapes.RECTANGLE, {
    x: qLeft, y: qTop, w: qW, h: qH, fill: { color: CB.orangeLight },
    line: { color: CB.border, width: 0.5 },
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: qLeft + 0.3, y: qTop + 0.18, w: 0.85, h: 0.26,
    rectRadius: 0.04, fill: { color: CB.orangeBadge },
  });
  s.addText("CATALYST", {
    x: qLeft + 0.3, y: qTop + 0.18, w: 0.85, h: 0.26,
    fontSize: 8, fontFace: "Source Sans 3", bold: true, color: CB.orangeText,
    align: "center", valign: "middle", margin: 0,
  });
  s.addText("Why Now", {
    x: qLeft + 0.3, y: qTop + 0.52, w: 4.4, h: 0.28,
    fontSize: 16, fontFace: "Source Sans 3", bold: true, color: CB.navy, margin: 0,
  });
  s.addText([
    { text: "•  Current platforms support ", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "SMB and standard Enterprise", options: { fontSize: 11, fontFace: "Source Sans 3", bold: true, color: CB.orange } },
    { text: " effectively\n", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "•  Capability gaps emerge for:\n", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "     ◦  Custom Enterprise customers\n", options: { fontSize: 10, fontFace: "Source Sans 3", color: CB.textSecondary } },
    { text: "     ◦  Custom products and pricing\n", options: { fontSize: 10, fontFace: "Source Sans 3", color: CB.textSecondary } },
    { text: "     ◦  Large, complex, multi-site deployments >50 sites\n", options: { fontSize: 10, fontFace: "Source Sans 3", color: CB.textSecondary } },
    { text: "•  These gaps introduce ", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "scale limits", options: { fontSize: 11, fontFace: "Source Sans 3", bold: true, color: CB.orange } },
    { text: ", manual workarounds, and risk", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
  ], {
    x: qLeft + 0.3, y: qTop + 0.82, w: 4.4, h: 1.3, valign: "top", margin: 0, lineSpacingMultiple: 1.15,
  });

  // Q2: Objective (top-right, blue tint)
  s.addShape(pres.shapes.RECTANGLE, {
    x: qMid, y: qTop, w: qW, h: qH, fill: { color: CB.blueLight },
    line: { color: CB.border, width: 0.5 },
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: qMid + 0.3, y: qTop + 0.18, w: 0.95, h: 0.26,
    rectRadius: 0.04, fill: { color: CB.blueBadge },
  });
  s.addText("OBJECTIVE", {
    x: qMid + 0.3, y: qTop + 0.18, w: 0.95, h: 0.26,
    fontSize: 8, fontFace: "Source Sans 3", bold: true, color: CB.blueText,
    align: "center", valign: "middle", margin: 0,
  });
  s.addText("What We Set Out to Do", {
    x: qMid + 0.3, y: qTop + 0.52, w: 4.4, h: 0.28,
    fontSize: 16, fontFace: "Source Sans 3", bold: true, color: CB.navy, margin: 0,
  });
  s.addText([
    { text: "•  Close the Custom Enterprise quoting gap ", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "quickly", options: { fontSize: 11, fontFace: "Source Sans 3", bold: true, color: CB.orange } },
    { text: "\n", options: { fontSize: 11 } },
    { text: "•  Accelerate a ", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "build vs. buy (COTS)", options: { fontSize: 11, fontFace: "Source Sans 3", bold: true, color: CB.orange } },
    { text: " decision\n", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "•  Minimize upfront spend while maximizing learning", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
  ], {
    x: qMid + 0.3, y: qTop + 0.82, w: 4.4, h: 1.3, valign: "top", margin: 0, lineSpacingMultiple: 1.35,
  });

  // Q3: Approach (bottom-left, gray tint)
  s.addShape(pres.shapes.RECTANGLE, {
    x: qLeft, y: qMidY, w: qW, h: qH, fill: { color: CB.grayLight },
    line: { color: CB.border, width: 0.5 },
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: qLeft + 0.3, y: qMidY + 0.18, w: 0.98, h: 0.26,
    rectRadius: 0.04, fill: { color: CB.grayBadge },
  });
  s.addText("APPROACH", {
    x: qLeft + 0.3, y: qMidY + 0.18, w: 0.98, h: 0.26,
    fontSize: 8, fontFace: "Source Sans 3", bold: true, color: CB.navy,
    align: "center", valign: "middle", margin: 0,
  });
  s.addText("How We Got Here", {
    x: qLeft + 0.3, y: qMidY + 0.52, w: 4.4, h: 0.28,
    fontSize: 16, fontFace: "Source Sans 3", bold: true, color: CB.navy, margin: 0,
  });
  s.addText([
    { text: "•  Leveraged ", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "TMF standards", options: { fontSize: 11, fontFace: "Source Sans 3", bold: true, color: CB.orange } },
    { text: " and open APIs as stable reference models\n", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "•  Applied ", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "Spec-Driven Development (SDD)", options: { fontSize: 11, fontFace: "Source Sans 3", bold: true, color: CB.orange } },
    { text: " to enhance core capabilities\n", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "•  Built a ", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "low-cost Prototype", options: { fontSize: 11, fontFace: "Source Sans 3", bold: true, color: CB.orange } },
    { text: " focused on architectural viability — not feature completeness", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
  ], {
    x: qLeft + 0.3, y: qMidY + 0.82, w: 4.4, h: 1.3, valign: "top", margin: 0, lineSpacingMultiple: 1.35,
  });

  // Q4: Outcome (bottom-right, green tint)
  s.addShape(pres.shapes.RECTANGLE, {
    x: qMid, y: qMidY, w: qW, h: qH, fill: { color: CB.greenLight },
    line: { color: CB.border, width: 0.5 },
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: qMid + 0.3, y: qMidY + 0.18, w: 0.9, h: 0.26,
    rectRadius: 0.04, fill: { color: CB.greenBadge },
  });
  s.addText("OUTCOME", {
    x: qMid + 0.3, y: qMidY + 0.18, w: 0.9, h: 0.26,
    fontSize: 8, fontFace: "Source Sans 3", bold: true, color: CB.greenText,
    align: "center", valign: "middle", margin: 0,
  });
  s.addText("What We Proved", {
    x: qMid + 0.3, y: qMidY + 0.52, w: 4.4, h: 0.28,
    fontSize: 16, fontFace: "Source Sans 3", bold: true, color: CB.navy, margin: 0,
  });
  s.addText([
    { text: "•  Proven technical scaffolding:\n", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "     ◦  Canonical models, APIs, orchestration patterns\n", options: { fontSize: 10, fontFace: "Source Sans 3", color: CB.textSecondary } },
    { text: "•  Prototype that validates support for ", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "complex products", options: { fontSize: 11, fontFace: "Source Sans 3", bold: true, color: CB.orange } },
    { text: " and ", options: { fontSize: 11, fontFace: "Source Sans 3", color: CB.text } },
    { text: "large-site scenarios", options: { fontSize: 11, fontFace: "Source Sans 3", bold: true, color: CB.orange } },
  ], {
    x: qMid + 0.3, y: qMidY + 0.82, w: 4.4, h: 0.75, valign: "top", margin: 0, lineSpacingMultiple: 1.15,
  });
  // Decision callout with green left border
  s.addShape(pres.shapes.RECTANGLE, {
    x: qMid + 0.3, y: qMidY + 1.6, w: 0.04, h: 0.48, fill: { color: CB.greenBorder },
  });
  s.addText("Clear decision point:\nConfidently continue targeted build or pivot to alternative options", {
    x: qMid + 0.48, y: qMidY + 1.6, w: 4.2, h: 0.48,
    fontSize: 11, fontFace: "Source Sans 3", bold: true, color: CB.greenText,
    valign: "top", margin: 0, lineSpacingMultiple: 1.2,
  });

  // ─ Key Takeaway bar (Comcast Blue)
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.04, w: 10, h: 0.42, fill: { color: CB.blue },
  });
  s.addText([
    { text: "Key Takeaway: ", options: { fontSize: 12, fontFace: "Source Sans 3", bold: true, color: "FFB584" } },
    { text: "We invested just enough to reduce uncertainty — accelerating decision-making while avoiding premature commitment.", options: { fontSize: 12, fontFace: "Source Sans 3", color: C.white } },
  ], {
    x: 0.5, y: 5.04, w: 9.0, h: 0.42, valign: "middle", margin: 0,
  });

  // ─ Footer
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.46, w: 10, h: 0.17, fill: { color: CB.grayLight },
    line: { color: CB.grayBadge, width: 0.5, dashType: "solid" },
  });
  s.addText("SOW++ · Q1 2026 · Confidential", {
    x: 0.5, y: 5.46, w: 4.0, h: 0.17,
    fontSize: 8, fontFace: "Source Sans 3", color: CB.footerGray, valign: "middle", margin: 0,
  });
  s.addText([
    { text: "Audience: ", options: { fontSize: 8, fontFace: "Source Sans 3", color: CB.footerGray } },
    { text: " CIO ", options: { fontSize: 7, fontFace: "Source Sans 3", bold: true, color: CB.blueText, highlight: CB.blueBadge } },
    { text: "  ", options: { fontSize: 7 } },
    { text: " ARCHITECTS ", options: { fontSize: 7, fontFace: "Source Sans 3", bold: true, color: CB.navy, highlight: CB.grayBadge } },
    { text: "  ", options: { fontSize: 7 } },
    { text: " DEVELOPERS ", options: { fontSize: 7, fontFace: "Source Sans 3", bold: true, color: CB.orangeText, highlight: CB.orangeBadge } },
  ], {
    x: 5.5, y: 5.46, w: 4.0, h: 0.17,
    align: "right", valign: "middle", margin: 0,
  });
}

// ── Slide 3: Agenda / Table of Contents ──
{
  const s = pres.addSlide();
  s.background = { color: C.offWhite };

  s.addText("Agenda", {
    x: 0.8, y: 0.4, w: 8.4, h: 0.7,
    fontSize: 36, fontFace: "Trebuchet MS", bold: true,
    color: C.navy, align: "left", margin: 0,
  });

  const items = [
    { num: "01", title: "Overview", desc: "Why Standard vs. Custom matters" },
    { num: "02", title: "Use Cases & Scenarios", desc: "High-level scenario matrix across business units" },
    { num: "03", title: "High Level Architecture", desc: "End-to-end BSS/OSS stack layout" },
    { num: "04", title: "Impacts to Current State", desc: "Platform-by-platform impact assessment" },
    { num: "05", title: "Product Catalog Support", desc: "Catalog strategy and next steps" },
  ];

  items.forEach((item, i) => {
    const yBase = 1.5 + i * 0.78;
    // Number circle
    s.addShape(pres.shapes.OVAL, {
      x: 0.8, y: yBase, w: 0.5, h: 0.5, fill: { color: C.navy },
    });
    s.addText(item.num, {
      x: 0.8, y: yBase, w: 0.5, h: 0.5,
      fontSize: 14, fontFace: "Calibri", bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0,
    });
    s.addText(item.title, {
      x: 1.5, y: yBase - 0.02, w: 7.5, h: 0.3,
      fontSize: 18, fontFace: "Trebuchet MS", bold: true,
      color: C.charcoal, align: "left", margin: 0,
    });
    s.addText(item.desc, {
      x: 1.5, y: yBase + 0.28, w: 7.5, h: 0.25,
      fontSize: 12, fontFace: "Calibri", color: C.slate,
      align: "left", margin: 0,
    });
  });
}

// ── Slide 3: Overview ──
{
  const s = pres.addSlide();
  s.background = { color: C.white };

  // Section tag
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 0.35, w: 1.2, h: 0.32, fill: { color: C.navy },
  });
  s.addText("1.1", {
    x: 0.8, y: 0.35, w: 1.2, h: 0.32,
    fontSize: 13, fontFace: "Calibri", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0,
  });

  s.addText("Overview", {
    x: 2.15, y: 0.3, w: 7, h: 0.5,
    fontSize: 32, fontFace: "Trebuchet MS", bold: true,
    color: C.navy, align: "left", margin: 0,
  });

  // Context paragraph
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 1.2, w: 8.4, h: 1.5,
    fill: { color: C.ice }, shadow: makeShadow(),
  });
  s.addText(
    "Current state NorthStar applications are based around standard products and processes. " +
    "As Comcast Business continues to grow — expanding its global reach, obtaining new customers " +
    "through acquisitions, and providing differentiating product experiences — CBIT has an opportunity " +
    "to evaluate how it can scale appropriately with the most efficient cost of ownership.",
    {
      x: 1.0, y: 1.35, w: 8.0, h: 1.2,
      fontSize: 14, fontFace: "Calibri", color: C.charcoal,
      align: "left", valign: "top", margin: 0,
    }
  );

  // Two-column callout cards
  // Card 1
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 3.1, w: 4.0, h: 1.8, fill: { color: C.white }, shadow: makeShadow(),
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 3.1, w: 0.08, h: 1.8, fill: { color: C.accent },
  });
  s.addText("Lost Sales Opportunities", {
    x: 1.1, y: 3.2, w: 3.5, h: 0.35,
    fontSize: 16, fontFace: "Trebuchet MS", bold: true,
    color: C.navy, align: "left", margin: 0,
  });
  s.addText(
    "Comcast Business is losing sales opportunities due to lack of support for custom scenarios and permutations in the current platform.",
    {
      x: 1.1, y: 3.6, w: 3.5, h: 1.1,
      fontSize: 12, fontFace: "Calibri", color: C.charcoal,
      align: "left", valign: "top", margin: 0,
    }
  );

  // Card 2
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 3.1, w: 4.0, h: 1.8, fill: { color: C.white }, shadow: makeShadow(),
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 3.1, w: 0.08, h: 1.8, fill: { color: C.teal },
  });
  s.addText("Legacy BSS/OSS Dependency", {
    x: 5.5, y: 3.2, w: 3.5, h: 0.35,
    fontSize: 16, fontFace: "Trebuchet MS", bold: true,
    color: C.navy, align: "left", margin: 0,
  });
  s.addText(
    "Legacy BSS/OSS systems are not scheduled to be deprecated due to lack of equivalent support in NorthStar — creating ongoing dual-stack maintenance costs.",
    {
      x: 5.5, y: 3.6, w: 3.5, h: 1.1,
      fontSize: 12, fontFace: "Calibri", color: C.charcoal,
      align: "left", valign: "top", margin: 0,
    }
  );
}

// ── Slide 4: High Level Scenarios — Standard Products ──
{
  const s = pres.addSlide();
  s.background = { color: C.white };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 0.35, w: 1.4, h: 0.32, fill: { color: C.navy },
  });
  s.addText("1.2.1", {
    x: 0.8, y: 0.35, w: 1.4, h: 0.32,
    fontSize: 13, fontFace: "Calibri", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0,
  });
  s.addText("High Level Scenarios — Standard", {
    x: 2.35, y: 0.3, w: 7, h: 0.5,
    fontSize: 28, fontFace: "Trebuchet MS", bold: true,
    color: C.navy, align: "left", margin: 0,
  });

  const headerStyle = {
    fill: { color: C.navy }, color: C.white, bold: true,
    fontSize: 8, fontFace: "Calibri", align: "center", valign: "middle",
  };
  const cellStyle = {
    fill: { color: C.offWhite }, color: C.charcoal,
    fontSize: 7.5, fontFace: "Calibri", align: "center", valign: "middle",
  };
  const altStyle = {
    fill: { color: C.white }, color: C.charcoal,
    fontSize: 7.5, fontFace: "Calibri", align: "center", valign: "middle",
  };

  const headers = [
    [
      { text: "Scenario", options: { ...headerStyle } },
      { text: "Lead/Opp", options: { ...headerStyle } },
      { text: "Quoting", options: { ...headerStyle } },
      { text: "Ordering", options: { ...headerStyle } },
      { text: "Fulfillment", options: { ...headerStyle } },
      { text: "Billing", options: { ...headerStyle } },
      { text: "Assurance", options: { ...headerStyle } },
      { text: "Digital", options: { ...headerStyle } },
    ],
  ];

  const stdRows = [
    ["< 10 site", "Dynamics", "Bundle Builder/SQO", "Workbench/CSG OSO", "CSG/OSO", "CSG/Amdocs", "ICO/CAFÉ", "Digital Convergence"],
    ["< 100 site", "Dynamics", "SQO - C1/D1", "OSO", "OSO", "Amdocs", "ICO/CAFÉ", "Digital Convergence"],
    ["< 1000 site", "Dynamics", "SQO - C1/D1", "OSO", "OSO", "Amdocs", "ICO/CAFÉ", "Digital Convergence"],
    ["> 1000 site", "Dynamics", "SOW Tool++", "Compass", "OSO/COSMOS", "Singleview", "ICO/CAFÉ", "Digital Convergence"],
    ["CBG Standard", "Dynamics", "SQO - C1/D1", "OSO", "OSO", "Amdocs", "ICO/CAFÉ", "Digital Convergence"],
    ["Nitel Standard", "Dynamics", "Intellipro/SQO", "OSO", "OSO", "Amdocs", "ICO/CAFÉ", "Digital Convergence"],
  ];

  const dataRows = stdRows.map((row, ri) => {
    const style = ri % 2 === 0 ? { ...cellStyle } : { ...altStyle };
    return row.map((cell) => ({ text: cell, options: { ...style } }));
  });

  s.addTable([...headers, ...dataRows], {
    x: 0.3, y: 1.1, w: 9.4,
    colW: [1.2, 0.9, 1.5, 1.3, 1.1, 1.1, 1.0, 1.3],
    border: { pt: 0.5, color: C.lightGray },
    rowH: [0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35],
    autoPage: false,
  });

  // Footnote
  s.addText("Standard contract type — supported by NorthStar stack", {
    x: 0.8, y: 4.9, w: 8, h: 0.3,
    fontSize: 10, fontFace: "Calibri", italic: true,
    color: C.slate, align: "left", margin: 0,
  });
}

// ── Slide 5: High Level Scenarios — Custom Products ──
{
  const s = pres.addSlide();
  s.background = { color: C.white };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 0.35, w: 1.4, h: 0.32, fill: { color: C.navy },
  });
  s.addText("1.2.1", {
    x: 0.8, y: 0.35, w: 1.4, h: 0.32,
    fontSize: 13, fontFace: "Calibri", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0,
  });
  s.addText("High Level Scenarios — Custom", {
    x: 2.35, y: 0.3, w: 7, h: 0.5,
    fontSize: 28, fontFace: "Trebuchet MS", bold: true,
    color: C.navy, align: "left", margin: 0,
  });

  const headerStyle = {
    fill: { color: C.navy }, color: C.white, bold: true,
    fontSize: 8, fontFace: "Calibri", align: "center", valign: "middle",
  };
  const cellStyle = {
    fill: { color: C.offWhite }, color: C.charcoal,
    fontSize: 7.5, fontFace: "Calibri", align: "center", valign: "middle",
  };
  const altStyle = {
    fill: { color: C.white }, color: C.charcoal,
    fontSize: 7.5, fontFace: "Calibri", align: "center", valign: "middle",
  };

  const headers = [
    [
      { text: "Scenario", options: { ...headerStyle } },
      { text: "Lead/Opp", options: { ...headerStyle } },
      { text: "Quoting", options: { ...headerStyle } },
      { text: "Ordering", options: { ...headerStyle } },
      { text: "Fulfillment", options: { ...headerStyle } },
      { text: "Billing", options: { ...headerStyle } },
      { text: "Assurance", options: { ...headerStyle } },
      { text: "Digital", options: { ...headerStyle } },
    ],
  ];

  const custRows = [
    ["< 10 site", "Dynamics", "SOW Tool++", "Workbench/CSG OSO", "CSG/OSO", "CSG/Amdocs", "ICO/CAFÉ", "Digital Convergence"],
    ["< 100 site", "Dynamics", "SOW Tool++", "Compass", "OSO/COSMOS", "Singleview", "ICO/CAFÉ", "Digital Convergence"],
    ["< 1000 site", "Dynamics", "SOW Tool++", "Compass", "OSO/COSMOS", "Singleview", "ICO/CAFÉ", "Digital Convergence"],
    ["> 1000 site", "Dynamics", "SOW Tool++", "Compass", "OSO/COSMOS", "Singleview", "ICO/CAFÉ", "Digital Convergence"],
    ["CBG Custom", "Dynamics", "SOW Tool++", "Compass", "OSO/COSMOS", "Singleview", "ICO/CAFÉ", "Digital Convergence"],
    ["Nitel Custom", "Dynamics", "Intellipro/SOW++", "Compass", "OSO/COSMOS", "Singleview", "ICO/CAFÉ", "Digital Convergence"],
  ];

  const dataRows = custRows.map((row, ri) => {
    const style = ri % 2 === 0 ? { ...cellStyle } : { ...altStyle };
    return row.map((cell) => ({ text: cell, options: { ...style } }));
  });

  s.addTable([...headers, ...dataRows], {
    x: 0.3, y: 1.1, w: 9.4,
    colW: [1.2, 0.9, 1.5, 1.3, 1.1, 1.1, 1.0, 1.3],
    border: { pt: 0.5, color: C.lightGray },
    rowH: [0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35],
    autoPage: false,
  });

  s.addText("Custom contract type — requires SOW Tool++ and Compass/Singleview stack", {
    x: 0.8, y: 4.9, w: 8, h: 0.3,
    fontSize: 10, fontFace: "Calibri", italic: true,
    color: C.slate, align: "left", margin: 0,
  });
}

// ── Slide 6: Business Unit & Specialty Scenarios ──
{
  const s = pres.addSlide();
  s.background = { color: C.white };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 0.35, w: 1.4, h: 0.32, fill: { color: C.navy },
  });
  s.addText("1.2.1", {
    x: 0.8, y: 0.35, w: 1.4, h: 0.32,
    fontSize: 13, fontFace: "Calibri", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0,
  });
  s.addText("Scenarios — International, CBM & Government", {
    x: 2.35, y: 0.3, w: 7, h: 0.5,
    fontSize: 26, fontFace: "Trebuchet MS", bold: true,
    color: C.navy, align: "left", margin: 0,
  });

  const headerStyle = {
    fill: { color: C.navy }, color: C.white, bold: true,
    fontSize: 8, fontFace: "Calibri", align: "center", valign: "middle",
  };
  const cellStyle = {
    fill: { color: C.offWhite }, color: C.charcoal,
    fontSize: 7.5, fontFace: "Calibri", align: "center", valign: "middle",
  };
  const altStyle = {
    fill: { color: C.white }, color: C.charcoal,
    fontSize: 7.5, fontFace: "Calibri", align: "center", valign: "middle",
  };

  const headers = [
    [
      { text: "Scenario", options: { ...headerStyle } },
      { text: "Type", options: { ...headerStyle } },
      { text: "Lead/Opp", options: { ...headerStyle } },
      { text: "Quoting", options: { ...headerStyle } },
      { text: "Ordering", options: { ...headerStyle } },
      { text: "Fulfillment", options: { ...headerStyle } },
      { text: "Billing", options: { ...headerStyle } },
      { text: "Assurance", options: { ...headerStyle } },
    ],
  ];

  const rows = [
    ["Intl - Short Term", "Custom", "Dynamics", "SOW Tool++", "PIVOT", "PIVOT/ILEX", "Geneva", "ICO/CAFÉ"],
    ["Intl - NorthStar", "Custom", "Dynamics", "SOW Tool++", "Compass", "COSMOS", "Singleview", "ICO/CAFÉ"],
    ["CBM - SMB (Std)", "Standard", "Dynamics", "XOE", "XOE", "OrderTech", "Amdocs CBM", "Celestial"],
    ["CBM - Ent/CES (Std)", "Standard", "Dynamics", "SOW Tool++", "OSO", "OrderTech", "Amdocs", "ICO/CAFÉ"],
    ["CBM - SMB (Cust)", "Custom", "Dynamics", "SOW Tool++", "Compass", "OrderTech", "Singleview", "ICO/CAFÉ"],
    ["CBM - Ent/CES (Cust)", "Custom", "Dynamics", "SOW Tool++", "Compass", "OrderTech", "Singleview", "ICO/CAFÉ"],
    ["Fed Gov", "Government", "CGS Dynamics", "CGS Dynamics", "ServiceNow", "ServiceNow", "Encompass", "ServiceNow"],
    ["SLED", "Government", "CGS Dynamics", "CGS Dynamics", "ServiceNow", "ServiceNow", "Encompass", "ServiceNow"],
    ["Fed/SLED (Comcast)", "Custom", "Dynamics", "SOW Tool++", "Compass", "OSO/COSMOS", "Singleview", "ICO/CAFÉ"],
  ];

  const dataRows = rows.map((row, ri) => {
    const style = ri % 2 === 0 ? { ...cellStyle } : { ...altStyle };
    return row.map((cell) => ({ text: cell, options: { ...style } }));
  });

  s.addTable([...headers, ...dataRows], {
    x: 0.3, y: 1.0, w: 9.4,
    colW: [1.4, 0.8, 1.0, 1.2, 1.1, 1.1, 1.1, 1.0],
    border: { pt: 0.5, color: C.lightGray },
    rowH: [0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35],
    autoPage: false,
  });
}

// ── Slide 7: Customer Solutions Use Cases ──
{
  const s = pres.addSlide();
  s.background = { color: C.white };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 0.35, w: 1.4, h: 0.32, fill: { color: C.navy },
  });
  s.addText("1.2.2", {
    x: 0.8, y: 0.35, w: 1.4, h: 0.32,
    fontSize: 13, fontFace: "Calibri", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0,
  });
  s.addText("Customer Solutions Use Cases to be Validated", {
    x: 2.35, y: 0.3, w: 7, h: 0.5,
    fontSize: 26, fontFace: "Trebuchet MS", bold: true,
    color: C.navy, align: "left", margin: 0,
  });

  const useCases = [
    { title: "AI Communications", desc: "Next-generation AI-powered communication services" },
    { title: "CBG Voice for Enterprise Custom", desc: "Enterprise custom customers that need international functionality" },
    { title: "Meraki Stack Expansion", desc: "Adding new functionality for the Meraki stack, e.g. camera for Enterprise Platform Customers" },
    { title: "Cato for Indirect Customers", desc: "Cato SASE offering extended to indirect channel customers" },
    { title: "BVE / UCaaS Sessions", desc: "BVE and/or UCaaS sessions for custom enterprise customers" },
  ];

  useCases.forEach((uc, i) => {
    const yBase = 1.2 + i * 0.82;
    // Card
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.8, y: yBase, w: 8.4, h: 0.7, fill: { color: C.offWhite }, shadow: makeShadow(),
    });
    // Accent bar
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.8, y: yBase, w: 0.06, h: 0.7, fill: { color: C.teal },
    });
    s.addText(uc.title, {
      x: 1.1, y: yBase + 0.05, w: 7.9, h: 0.3,
      fontSize: 15, fontFace: "Trebuchet MS", bold: true,
      color: C.navy, align: "left", margin: 0,
    });
    s.addText(uc.desc, {
      x: 1.1, y: yBase + 0.35, w: 7.9, h: 0.25,
      fontSize: 11, fontFace: "Calibri", color: C.slate,
      align: "left", margin: 0,
    });
  });
}

// ── Slide 8: High Level Architecture ──
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 0.35, w: 1.2, h: 0.32, fill: { color: C.teal },
  });
  s.addText("1.3", {
    x: 0.8, y: 0.35, w: 1.2, h: 0.32,
    fontSize: 13, fontFace: "Calibri", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0,
  });
  s.addText("High Level Architecture", {
    x: 2.15, y: 0.3, w: 7, h: 0.5,
    fontSize: 32, fontFace: "Trebuchet MS", bold: true,
    color: C.white, align: "left", margin: 0,
  });

  // Architecture flow — horizontal boxes with arrows
  const layers = [
    { label: "Lead / Opp\nDynamics", color: C.midBlue },
    { label: "Quoting\nSOW++ / SQO", color: C.midBlue },
    { label: "Ordering\nCompass / OSO", color: C.teal },
    { label: "Fulfillment\nOSO / COSMOS", color: C.teal },
    { label: "Billing\nSingleview\nAmdocs", color: C.midBlue },
    { label: "Assurance\nICO / CAFÉ", color: C.midBlue },
    { label: "Digital\nConvergence", color: C.teal },
  ];

  const boxW = 1.1;
  const gap = 0.16;
  const totalW = layers.length * boxW + (layers.length - 1) * gap;
  const startX = (10 - totalW) / 2;

  layers.forEach((layer, i) => {
    const x = startX + i * (boxW + gap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.5, w: boxW, h: 1.4,
      fill: { color: layer.color }, shadow: makeShadow(),
    });
    s.addText(layer.label, {
      x, y: 1.5, w: boxW, h: 1.4,
      fontSize: 10, fontFace: "Calibri", bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0,
    });
    // Arrow between boxes
    if (i < layers.length - 1) {
      s.addText("\u25B6", {
        x: x + boxW, y: 1.95, w: gap, h: 0.5,
        fontSize: 10, color: C.accent, align: "center", valign: "middle", margin: 0,
      });
    }
  });

  // Two-row layout: Standard vs Custom
  const rowY = [3.4, 4.3];
  const labels = ["Standard Path", "Custom Path"];
  const paths = [
    ["Dynamics", "SQO / C1/D1", "OSO", "OSO", "Amdocs", "ICO/CAFÉ", "Digital Conv."],
    ["Dynamics", "SOW Tool++", "Compass", "OSO/COSMOS", "Singleview", "ICO/CAFÉ", "Digital Conv."],
  ];
  const pathColors = [C.teal, C.accent];

  labels.forEach((lbl, ri) => {
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.3, y: rowY[ri], w: 1.3, h: 0.6, fill: { color: pathColors[ri] },
    });
    s.addText(lbl, {
      x: 0.3, y: rowY[ri], w: 1.3, h: 0.6,
      fontSize: 10, fontFace: "Calibri", bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0,
    });
    paths[ri].forEach((step, ci) => {
      const x = 1.8 + ci * 1.14;
      s.addShape(pres.shapes.RECTANGLE, {
        x, y: rowY[ri], w: 1.05, h: 0.6,
        fill: { color: C.white, transparency: 90 },
        line: { color: pathColors[ri], width: 1 },
      });
      s.addText(step, {
        x, y: rowY[ri], w: 1.05, h: 0.6,
        fontSize: 8, fontFace: "Calibri", color: C.white,
        align: "center", valign: "middle", margin: 0,
      });
    });
  });
}

// ── Slide 9: Impacts to Current State (1/2) ──
{
  const s = pres.addSlide();
  s.background = { color: C.white };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 0.35, w: 1.2, h: 0.32, fill: { color: C.navy },
  });
  s.addText("1.4", {
    x: 0.8, y: 0.35, w: 1.2, h: 0.32,
    fontSize: 13, fontFace: "Calibri", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0,
  });
  s.addText("Impacts to Current State  (1/2)", {
    x: 2.15, y: 0.3, w: 7, h: 0.5,
    fontSize: 28, fontFace: "Trebuchet MS", bold: true,
    color: C.navy, align: "left", margin: 0,
  });

  const headerStyle = {
    fill: { color: C.navy }, color: C.white, bold: true,
    fontSize: 9, fontFace: "Calibri", align: "center", valign: "middle",
  };
  const cellStyle = {
    fill: { color: C.offWhite }, color: C.charcoal,
    fontSize: 8, fontFace: "Calibri", valign: "top",
  };
  const altStyle = {
    fill: { color: C.white }, color: C.charcoal,
    fontSize: 8, fontFace: "Calibri", valign: "top",
  };

  const headers = [[
    { text: "Platform", options: { ...headerStyle } },
    { text: "Feature Impacts", options: { ...headerStyle } },
    { text: "Program", options: { ...headerStyle } },
    { text: "Next Steps", options: { ...headerStyle } },
  ]];

  const rows = [
    ["New Product Catalog", "New catalog to support standard and non-standard requirements, includes authoring", "Scaled Solution Sales", "Decision on catalog options — build vs. buy, potential RFP (Andrew Angelucci, Balaji)"],
    ["SOW++", "CPQ and SOW support to replace the current SOW and Configurators", "Scaled Solution Sales", "Accelerate design and dev in 2026 (was scoped for 2027, budgeted below the line)"],
    ["Galaxy", "Add all standard products to support new custom and large site orders", "Compass", "Evaluate Orion vs Galaxy (Balaji and team). Build Ethernet beyond fed gov work"],
    ["POG", "Impacts for new products/services and new flow from SOW++. Ethernet and Fed Gov products via POG", "Compass / Fed Gov", "Align POG roadmap — evaluate Orion vs Galaxy. Determine TMF641 with landscape for Compass vs CBGI"],
    ["Singleview", "New product support for standard products not currently in Singleview and only in Orion", "TBD", "Assess delta of standard products in Orion vs Singleview"],
  ];

  const dataRows = rows.map((row, ri) => {
    const style = ri % 2 === 0 ? { ...cellStyle } : { ...altStyle };
    return row.map((cell) => ({ text: cell, options: { ...style } }));
  });

  s.addTable([...headers, ...dataRows], {
    x: 0.3, y: 1.0, w: 9.4,
    colW: [1.4, 2.8, 1.4, 3.8],
    border: { pt: 0.5, color: C.lightGray },
    rowH: [0.35, 0.7, 0.7, 0.7, 0.7, 0.55],
    autoPage: false,
  });
}

// ── Slide 10: Impacts to Current State (2/2) ──
{
  const s = pres.addSlide();
  s.background = { color: C.white };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 0.35, w: 1.2, h: 0.32, fill: { color: C.navy },
  });
  s.addText("1.4", {
    x: 0.8, y: 0.35, w: 1.2, h: 0.32,
    fontSize: 13, fontFace: "Calibri", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0,
  });
  s.addText("Impacts to Current State  (2/2)", {
    x: 2.15, y: 0.3, w: 7, h: 0.5,
    fontSize: 28, fontFace: "Trebuchet MS", bold: true,
    color: C.navy, align: "left", margin: 0,
  });

  const headerStyle = {
    fill: { color: C.navy }, color: C.white, bold: true,
    fontSize: 9, fontFace: "Calibri", align: "center", valign: "middle",
  };
  const cellStyle = {
    fill: { color: C.offWhite }, color: C.charcoal,
    fontSize: 8, fontFace: "Calibri", valign: "top",
  };
  const altStyle = {
    fill: { color: C.white }, color: C.charcoal,
    fontSize: 8, fontFace: "Calibri", valign: "top",
  };

  const headers = [[
    { text: "Platform", options: { ...headerStyle } },
    { text: "Feature Impacts", options: { ...headerStyle } },
    { text: "Program", options: { ...headerStyle } },
    { text: "Next Steps", options: { ...headerStyle } },
  ]];

  const rows = [
    ["Middleware / TMF", "TMF APIs handled by S3 and Compass. Determine if other TMF APIs needed for Assurance, Ticketing", "S3/Compass in CBG", "Align architecture on TMF and other APIs in fulfillment, assurance, and billing"],
    ["Digital", "Digital convergence impacted by Custom implementation in SOW \u2192 Singleview. Assess roadmap for D360", "Digital Convergence", "Meet with Digital stakeholders to determine impacts to platform and program"],
    ["CBG/Nitel Migration", "Determine if we need to migrate customers over in 2026", "TBD", "Align with business on migration strategy for 2026"],
    ["International", "International service locations and currency support in the custom stack, SOW++ through Billing", "TBD", "Sudhaman working with Erami and billing domain to setup NetCracker meetings"],
    ["CBM", "TBD", "CBM Genesis", "Andrew Angelucci — determine the proper stack to support CBM growth"],
    ["Public Sector", "Implement functionality above the line in Enclave. Updates below the line to integrate via POG", "Fed Gov / S3", "Align Enclave integration with POG roadmap"],
  ];

  const dataRows = rows.map((row, ri) => {
    const style = ri % 2 === 0 ? { ...cellStyle } : { ...altStyle };
    return row.map((cell) => ({ text: cell, options: { ...style } }));
  });

  s.addTable([...headers, ...dataRows], {
    x: 0.3, y: 1.0, w: 9.4,
    colW: [1.4, 2.8, 1.4, 3.8],
    border: { pt: 0.5, color: C.lightGray },
    rowH: [0.35, 0.6, 0.6, 0.5, 0.6, 0.5, 0.6],
    autoPage: false,
  });
}

// ── Slide 11: Product Catalog Support ──
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 0.35, w: 1.2, h: 0.32, fill: { color: C.teal },
  });
  s.addText("1.5", {
    x: 0.8, y: 0.35, w: 1.2, h: 0.32,
    fontSize: 13, fontFace: "Calibri", bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0,
  });
  s.addText("Product Catalog Support", {
    x: 2.15, y: 0.3, w: 7, h: 0.5,
    fontSize: 32, fontFace: "Trebuchet MS", bold: true,
    color: C.white, align: "left", margin: 0,
  });

  // Key decision cards
  const cards = [
    { title: "Current Challenge", body: "NorthStar catalog supports standard products only. Custom product permutations, international requirements, and acquired-platform products are not represented.", color: C.accent },
    { title: "Decision Required", body: "Build vs. Buy vs. Extend existing catalog. Potential RFP process to evaluate third-party catalog solutions. Andrew Angelucci and Balaji to lead evaluation.", color: C.teal },
    { title: "2026 Scope", body: "New catalog must support both standard and non-standard requirements including authoring capabilities. Aligned under Scaled Solution Sales program.", color: C.midBlue },
  ];

  cards.forEach((card, i) => {
    const yBase = 1.2 + i * 1.35;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.8, y: yBase, w: 8.4, h: 1.15, fill: { color: C.white, transparency: 90 },
      shadow: makeShadow(),
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.8, y: yBase, w: 0.06, h: 1.15, fill: { color: card.color },
    });
    s.addText(card.title, {
      x: 1.1, y: yBase + 0.1, w: 7.9, h: 0.3,
      fontSize: 18, fontFace: "Trebuchet MS", bold: true,
      color: C.white, align: "left", margin: 0,
    });
    s.addText(card.body, {
      x: 1.1, y: yBase + 0.5, w: 7.9, h: 0.55,
      fontSize: 12, fontFace: "Calibri", color: C.ice,
      align: "left", valign: "top", margin: 0,
    });
  });
}

// ── Slide 12: Key Takeaways & Next Steps ──
{
  const s = pres.addSlide();
  s.background = { color: C.white };

  s.addText("Key Takeaways & Next Steps", {
    x: 0.8, y: 0.3, w: 8.4, h: 0.7,
    fontSize: 32, fontFace: "Trebuchet MS", bold: true,
    color: C.navy, align: "left", margin: 0,
  });

  // Amber divider
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 1.05, w: 2.0, h: 0.04, fill: { color: C.accent },
  });

  const takeaways = [
    { title: "Dual-Stack Reality", body: "Standard (NorthStar) and Custom (SOW++ / Compass / Singleview) stacks will coexist; plan for parallel support" },
    { title: "SOW++ Is the Pivot", body: "CPQ and SOW replacement is the linchpin — accelerate design and development in 2026" },
    { title: "Product Catalog Decision", body: "Build vs. Buy evaluation needed immediately (Andrew Angelucci, Balaji)" },
    { title: "International Strategy", body: "Currency and location support built in custom stack; NetCracker biller evaluation underway" },
    { title: "Orion vs Galaxy", body: "Balaji and team to evaluate; impacts Galaxy, POG, and TMF641 architecture decisions" },
    { title: "CBM Growth Path", body: "Determine if CBM builds only in custom or also updates standard Amdocs stack" },
  ];

  takeaways.forEach((t, i) => {
    const yBase = 1.3 + i * 0.68;
    // Number badge
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.8, y: yBase + 0.05, w: 0.35, h: 0.35, fill: { color: C.navy },
    });
    s.addText(String(i + 1), {
      x: 0.8, y: yBase + 0.05, w: 0.35, h: 0.35,
      fontSize: 14, fontFace: "Calibri", bold: true,
      color: C.white, align: "center", valign: "middle", margin: 0,
    });
    s.addText(t.title, {
      x: 1.35, y: yBase, w: 3.0, h: 0.35,
      fontSize: 14, fontFace: "Trebuchet MS", bold: true,
      color: C.navy, align: "left", margin: 0,
    });
    s.addText(t.body, {
      x: 1.35, y: yBase + 0.3, w: 7.8, h: 0.3,
      fontSize: 11, fontFace: "Calibri", color: C.charcoal,
      align: "left", margin: 0,
    });
  });
}

// ── Write file ──
const outPath = "/Users/schand201@cable.comcast.com/Desktop/Github/ConversationalSalesAgent/docs/Standard_vs_Custom_BSS_OSS_Pattern.pptx";
pres.writeFile({ fileName: outPath }).then(() => {
  console.log("PPTX written to: " + outPath);
}).catch((err) => {
  console.error("Error:", err);
});

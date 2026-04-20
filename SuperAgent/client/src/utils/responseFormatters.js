function normalizeText(value) {
  return (value || "").toString().trim();
}

function extractJsonBlock(text) {
  const input = normalizeText(text);
  if (!input.includes("{")) return null;

  let start = -1;
  let depth = 0;
  for (let index = 0; index < input.length; index += 1) {
    const char = input[index];
    if (char === "{") {
      if (start === -1) start = index;
      depth += 1;
    } else if (char === "}") {
      depth -= 1;
      if (depth === 0 && start !== -1) {
        return input.slice(start, index + 1);
      }
    }
  }

  return null;
}

export function parsePaymentConfirmation(text) {
  const jsonBlock = extractJsonBlock(text);
  if (!jsonBlock) return null;
  try {
    const parsed = JSON.parse(jsonBlock);
    if (!parsed || parsed.payment_confirmation !== true) return null;
    if (!parsed.transaction_id || !parsed.status) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function parseOrderConfirmation(text) {
  const jsonBlock = extractJsonBlock(text);
  if (!jsonBlock) return null;
  try {
    const parsed = JSON.parse(jsonBlock);
    if (!parsed || parsed.order_confirmation !== true) return null;
    if (!parsed.order_id || !parsed.customer) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function parseOfferQuote(text) {
  const jsonBlock = extractJsonBlock(text);
  if (!jsonBlock) return null;

  try {
    const parsed = JSON.parse(jsonBlock);
    if (!parsed || typeof parsed !== "object") return null;
    if (!parsed.offer_id || !Array.isArray(parsed.items)) return null;
    if (typeof parsed.total_price !== "number") return null;

    return parsed;
  } catch {
    return null;
  }
}

function parseKeyValueLine(line) {
  const patterns = [
    /^[•\-*]?\s*\*\*([^*]+):\*\*\s*(.+)$/,
    /^[•\-*]?\s*\*\*([^*]+)\*\*:\s*(.+)$/,
    /^[•\-*]?\s*([^:]+):\s*(.+)$/,
  ];

  for (const pattern of patterns) {
    const match = line.match(pattern);
    if (match) {
      return {
        key: normalizeText(match[1]),
        value: normalizeText(match[2]),
      };
    }
  }

  return null;
}

function parseProductLine(line) {
  const match = line.match(/^[•\-*]?\s*\*\*([A-Z0-9-]+)\*\*\s*-\s*(.+)$/);
  if (!match) return null;
  return {
    id: normalizeText(match[1]),
    name: normalizeText(match[2]),
  };
}

function readValue(map, key) {
  return map.get(key) || "";
}

export function parseServiceabilityMessage(text) {
  const input = normalizeText(text);
  if (!input) return null;

  const lines = input.split("\n").map((line) => line.trim()).filter(Boolean);
  const keyValueMap = new Map();
  const products = [];

  lines.forEach((line) => {
    const kv = parseKeyValueLine(line);
    if (kv) {
      keyValueMap.set(kv.key, kv.value);
      return;
    }

    const product = parseProductLine(line);
    if (product) {
      products.push(product);
    }
  });

  const summaryLine = lines.find((line) =>
    line.includes("location is serviceable") || line.includes("location is not serviceable")
  );

  const statusMatch = summaryLine?.match(/(serviceable|not serviceable)/i);
  const isServiceable = statusMatch ? statusMatch[1].toLowerCase() === "serviceable" : null;

  const data = {
    heading: lines.find((line) => line.toLowerCase().includes("i've checked network availability")) || "",
    summary: summaryLine || "",
    isServiceable,
    infrastructureType: readValue(keyValueMap, "Infrastructure Type"),
    serviceZone: readValue(keyValueMap, "Service Zone"),
    switchId: readValue(keyValueMap, "Switch ID"),
    cabinetId: readValue(keyValueMap, "Cabinet ID"),
    availableFiberPairs: readValue(keyValueMap, "Available Fiber Pairs"),
    oltEquipment: readValue(keyValueMap, "OLT Equipment"),
    minimumSpeed: readValue(keyValueMap, "Minimum Speed"),
    maximumSpeed: readValue(keyValueMap, "Maximum Speed"),
    symmetrical: readValue(keyValueMap, "Symmetrical"),
    serviceClass: readValue(keyValueMap, "Service Class"),
    redundancy: readValue(keyValueMap, "Redundancy"),
    installationTimeline: readValue(keyValueMap, "Installation Timeline"),
    products,
  };

  const hasCoreSignal =
    data.summary ||
    data.infrastructureType ||
    data.minimumSpeed ||
    data.maximumSpeed ||
    data.products.length > 0;

  return hasCoreSignal ? data : null;
}

export function formatCurrency(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function stripMarkdownArtifacts(line) {
  return normalizeText(
    line
      .replace(/^#+\s*/, "")
      .replace(/^\s*[•\-*]\s+/, "")
      .replace(/\*\*/g, "")
  );
}

function parseInlineKeyValue(line) {
  const cleaned = stripMarkdownArtifacts(line);
  const match = cleaned.match(/^([^:]{2,50}):\s*(.+)$/);
  if (!match) return null;
  return {
    label: normalizeText(match[1]),
    value: normalizeText(match[2]),
  };
}

function isProductHeading(line) {
  const cleaned = stripMarkdownArtifacts(line);
  return (
    /^\d+[\.)]\s+.+/.test(cleaned) ||
    /\([A-Z]{2,}(?:-[A-Z0-9]+)+\)[:\s]*$/.test(cleaned)
  );
}

function parseProductHeading(line) {
  // Strip trailing colon that product agent sometimes appends: "Product Name (ID):"
  const cleaned = stripMarkdownArtifacts(line).replace(/^\d+\.\s+/, "").replace(/:$/, "");
  const idMatch = cleaned.match(/\(([A-Z0-9-]+)\)\s*$/);
  return {
    title: normalizeText(cleaned.replace(/\(([A-Z0-9-]+)\)\s*$/, "")),
    productId: idMatch ? idMatch[1] : "",
  };
}

function parseProductBlock(lines) {
  if (!lines.length) return null;

  const { title, productId } = parseProductHeading(lines[0]);
  const attributes = [];
  const features = [];
  let description = "";
  let inFeatureSection = false;

  for (let index = 1; index < lines.length; index += 1) {
    const rawLine = lines[index];
    const cleaned = stripMarkdownArtifacts(rawLine);
    if (!cleaned) continue;

    if (!description && !/^[^:]{2,50}:/.test(cleaned) && !/^key features:?$/i.test(cleaned)) {
      description = cleaned;
      continue;
    }

    // Match both "Key Features:" and plain "Features:" section headers
    if (/^(?:key\s+)?features:?$/i.test(cleaned)) {
      inFeatureSection = true;
      continue;
    }

    const kv = parseInlineKeyValue(rawLine);
    if (kv) {
      attributes.push(kv);
      if (/key features?/i.test(kv.label) && kv.value) {
        features.push(kv.value);
      }
      inFeatureSection = false;
      continue;
    }

    if (inFeatureSection || /^\s*[•\-*]\s+/.test(rawLine)) {
      features.push(cleaned);
    }
  }

  if (!title) return null;

  // Promote "Description" attribute to the card's description field for cleaner display
  if (!description) {
    const descIndex = attributes.findIndex((a) => /^description$/i.test(a.label));
    if (descIndex !== -1) {
      description = attributes[descIndex].value;
      attributes.splice(descIndex, 1);
    }
  }

  return {
    title,
    productId,
    description,
    attributes,
    features,
  };
}

function isCtaLine(line) {
  const cleaned = stripMarkdownArtifacts(line).toLowerCase();
  if (!cleaned) return false;

  return (
    cleaned.startsWith("would you like") ||
    cleaned.startsWith("what would you like") ||
    cleaned.startsWith("what interests you") ||
    cleaned.startsWith("next steps") ||
    cleaned.startsWith("i can help you") ||
    cleaned.startsWith("i can help with") ||
    cleaned.startsWith("to proceed")
  );
}

export function parseProductAgentMessage(text) {
  const input = normalizeText(text);
  if (!input) return null;

  const lines = input.split("\n");
  const headingIndexes = [];

  lines.forEach((line, index) => {
    if (isProductHeading(line)) headingIndexes.push(index);
  });

  if (!headingIndexes.length) return null;

  let ctaStartIndex = -1;
  const firstHeading = headingIndexes[0];
  for (let index = firstHeading + 1; index < lines.length; index += 1) {
    if (isCtaLine(lines[index])) {
      ctaStartIndex = index;
      break;
    }
  }

  const productContentEnd = ctaStartIndex >= 0 ? ctaStartIndex : lines.length;

  const products = [];
  for (let i = 0; i < headingIndexes.length; i += 1) {
    const start = headingIndexes[i];
    const naturalEnd = i + 1 < headingIndexes.length ? headingIndexes[i + 1] : productContentEnd;
    const end = Math.min(naturalEnd, productContentEnd);
    if (start >= end) continue;
    const blockLines = lines.slice(start, end).map((line) => line.trimRight());
    const product = parseProductBlock(blockLines);
    if (product) products.push(product);
  }

  if (!products.length) return null;

  const intro = lines
    .slice(0, headingIndexes[0])
    .map((line) => line.trim())
    .filter(Boolean)
    .join(" ");

  const outroLines =
    ctaStartIndex >= 0
      ? lines
          .slice(ctaStartIndex)
          .map((line) => stripMarkdownArtifacts(line))
          .filter(Boolean)
      : [];

  return {
    intro,
    products,
    outroLines,
  };
}

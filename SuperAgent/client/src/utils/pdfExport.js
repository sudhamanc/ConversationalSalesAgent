import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";

const PAGE_MARGIN = 24;

function buildFilename() {
  const now = new Date();
  const stamp = now
    .toISOString()
    .replace(/[:]/g, "-")
    .replace(/\..+/, "")
    .replace("T", "_");
  return `superagent-chat-${stamp}.pdf`;
}

function createExportClone(element) {
  const wrapper = document.createElement("div");
  wrapper.style.position = "fixed";
  wrapper.style.left = "-100000px";
  wrapper.style.top = "0";
  wrapper.style.width = `${element.clientWidth}px`;
  wrapper.style.padding = "0";
  wrapper.style.margin = "0";
  wrapper.style.background = "#ffffff";
  wrapper.style.zIndex = "-1";

  const clone = element.cloneNode(true);
  clone.style.height = "auto";
  clone.style.maxHeight = "none";
  clone.style.overflow = "visible";
  clone.style.flex = "none";
  clone.style.background = "#ffffff";

  wrapper.appendChild(clone);
  document.body.appendChild(wrapper);

  return { wrapper, clone };
}

function normalizeExportClone(root) {
  const nodes = [root, ...root.querySelectorAll("*")];

  nodes.forEach((node) => {
    if (!(node instanceof HTMLElement)) return;

    node.style.animation = "none";
    node.style.transition = "none";

    if (
      node.classList.contains("chat-scroll") ||
      node.classList.contains("overflow-y-auto") ||
      node.classList.contains("overflow-hidden")
    ) {
      node.style.overflow = "visible";
      node.style.maxHeight = "none";
      node.style.height = "auto";
    }

    if (node.classList.contains("truncate") || node.classList.contains("line-clamp-2")) {
      node.style.whiteSpace = "normal";
      node.style.textOverflow = "clip";
      node.style.overflow = "visible";
      node.style.display = "block";
      node.style.webkitLineClamp = "unset";
      node.style.webkitBoxOrient = "initial";
    }
  });
}

function buildSessionLayout({ chatElement, journeyElement, cartElement, includeJourney, includeCart }) {
  if (!chatElement) {
    throw new Error("Chat container not available for export.");
  }

  const wrapper = document.createElement("div");
  wrapper.style.position = "fixed";
  wrapper.style.left = "-100000px";
  wrapper.style.top = "0";
  wrapper.style.background = "#ffffff";
  wrapper.style.padding = "0";
  wrapper.style.margin = "0";
  wrapper.style.zIndex = "-1";

  const row = document.createElement("div");
  row.style.display = "flex";
  row.style.alignItems = "flex-start";
  row.style.gap = "16px";
  row.style.background = "#ffffff";
  row.style.padding = "12px";

  const clonePane = (element, width) => {
    const pane = element.cloneNode(true);
    pane.style.width = `${width}px`;
    pane.style.maxHeight = "none";
    pane.style.height = "auto";
    pane.style.overflow = "visible";
    pane.style.flex = "none";
    pane.style.background = "#ffffff";
    return pane;
  };

  if (includeJourney && journeyElement) {
    row.appendChild(clonePane(journeyElement, journeyElement.clientWidth || 280));
  }

  row.appendChild(clonePane(chatElement, chatElement.clientWidth || 760));

  if (includeCart && cartElement) {
    row.appendChild(clonePane(cartElement, cartElement.clientWidth || 320));
  }

  wrapper.appendChild(row);
  document.body.appendChild(wrapper);

  normalizeExportClone(row);

  return { wrapper, clone: row };
}

function renderCanvasToPdf(canvas) {
  const pdf = new jsPDF({ orientation: "portrait", unit: "pt", format: "a4" });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();

  const contentWidth = pageWidth - PAGE_MARGIN * 2;
  const contentHeight = (canvas.height * contentWidth) / canvas.width;
  const imageData = canvas.toDataURL("image/png");

  let renderedHeight = 0;
  let pageIndex = 0;

  while (renderedHeight < contentHeight) {
    if (pageIndex > 0) {
      pdf.addPage();
    }

    const yOffset = PAGE_MARGIN - renderedHeight;
    pdf.addImage(imageData, "PNG", PAGE_MARGIN, yOffset, contentWidth, contentHeight);

    renderedHeight += pageHeight - PAGE_MARGIN * 2;
    pageIndex += 1;
  }

  pdf.save(buildFilename());
}

function canvasHasVisiblePixels(canvas) {
  if (!canvas || canvas.width <= 1 || canvas.height <= 1) return false;

  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) return false;

  const sampleX = Math.max(1, Math.floor(canvas.width / 24));
  const sampleY = Math.max(1, Math.floor(canvas.height / 24));

  for (let y = 0; y < canvas.height; y += sampleY) {
    for (let x = 0; x < canvas.width; x += sampleX) {
      const data = context.getImageData(x, y, 1, 1).data;
      if (data[3] > 0) {
        return true;
      }
    }
  }

  return false;
}

async function renderCloneToCanvas(clone) {
  const renderWidth = Math.max(clone.scrollWidth, clone.clientWidth, 1200);
  const renderHeight = Math.max(clone.scrollHeight, clone.clientHeight, 800);

  const baseOptions = {
    scale: 2,
    useCORS: true,
    backgroundColor: "#ffffff",
    windowWidth: renderWidth,
    windowHeight: renderHeight,
  };

  const attempts = [
    { ...baseOptions, foreignObjectRendering: false },
    { ...baseOptions, foreignObjectRendering: true },
  ];

  for (const attempt of attempts) {
    const canvas = await html2canvas(clone, attempt);
    if (canvasHasVisiblePixels(canvas)) {
      return canvas;
    }
  }

  throw new Error("Unable to render export content. Please retry export.");
}

export async function exportSessionToPdf(options) {
  const {
    chatElement,
    journeyElement = null,
    cartElement = null,
    includeJourney = false,
    includeCart = false,
  } = options || {};

  const { wrapper, clone } = buildSessionLayout({
    chatElement,
    journeyElement,
    cartElement,
    includeJourney,
    includeCart,
  });

  try {
    const canvas = await renderCloneToCanvas(clone);
    renderCanvasToPdf(canvas);
  } finally {
    document.body.removeChild(wrapper);
  }
}

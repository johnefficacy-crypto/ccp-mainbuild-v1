/**
 * Safe GFM markdown → HTML for question, option and explanation text
 * (REG-CORPUS-02). Two independent layers keep it safe:
 *
 *   1. marked is configured so raw HTML in the source is ESCAPED (shown as text,
 *      never interpreted).
 *   2. The output goes through a dedicated DOMPurify instance with a tight
 *      allowlist: text formatting, lists, tables, http(s) links, and the
 *      span/svg markup KaTeX emits. No img, no event handlers, no data-*;
 *      `style` survives on span/svg only (KaTeX positioning).
 *
 * Math is tokenised out FIRST (see mathSegments.js) so markdown never touches
 * it: each math segment becomes an opaque placeholder, the text is rendered as
 * markdown, then placeholders are swapped for `renderMath(tex, display)` output
 * (or the escaped source when no renderer is loaded) before sanitising.
 */
import { Marked } from "marked";
import DOMPurify from "dompurify";
import { splitMath } from "./mathSegments";

const escapeHtml = (s = "") =>
  String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

const marked = new Marked({
  gfm: true,
  breaks: true,
  async: false,
  renderer: {
    // Raw HTML (block or inline) is rendered as visible text, never as markup.
    html(token) {
      return escapeHtml(token.text ?? token.raw ?? "");
    },
  },
});

// Private-use code points: marked passes them through untouched and they cannot
// occur in authored text by accident.
const PH_OPEN = "\uE000";
const PH_CLOSE = "\uE001";
const PH_RE = /\uE000(\d+)\uE001/g;

const ALLOWED_TAGS = [
  "p", "br", "strong", "em", "b", "i", "del", "code", "pre", "blockquote", "hr",
  "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6",
  "table", "thead", "tbody", "tr", "th", "td", "div", "span", "a",
  // KaTeX (output: 'html') draws radicals, stretchy arrows and \cancel as SVG.
  "svg", "path", "line",
];
const ALLOWED_ATTR = [
  "class", "style", "align", "href", "title", "start", "colspan", "rowspan",
  "aria-hidden", "aria-label", "role",
  "xmlns", "width", "height", "viewBox", "preserveAspectRatio", "d",
  "x1", "x2", "y1", "y2", "stroke-width",
];
const STYLE_OK = new Set(["SPAN", "SVG"]);
const CLASS_OK = new Set(["SPAN", "SVG", "DIV", "TABLE"]);
const ALIGN_CLASS = { right: "text-right", center: "text-center", left: "text-left" };
const ELEMENT_CLASS = {
  P: "mb-2 last:mb-0",
  UL: "list-disc pl-5 mb-2 last:mb-0",
  OL: "list-decimal pl-5 mb-2 last:mb-0",
  TABLE: "min-w-full border-collapse text-sm",
  TH: "border border-gray-300 bg-gray-50 px-2 py-1 font-semibold",
  TD: "border border-gray-300 px-2 py-1",
  A: "underline",
  CODE: "font-mono rounded bg-gray-100 px-1",
};

let purifier = null;
function getPurifier() {
  if (purifier) return purifier;
  purifier = DOMPurify(typeof window !== "undefined" ? window : undefined);
  purifier.addHook("afterSanitizeAttributes", (node) => {
    const tag = (node.nodeName || "").toUpperCase();
    if (node.hasAttribute?.("style") && !STYLE_OK.has(tag)) node.removeAttribute("style");
    if (node.hasAttribute?.("class") && !CLASS_OK.has(tag)) node.removeAttribute("class");
    if (tag === "TH" || tag === "TD") {
      const align = (node.getAttribute("align") || "").toLowerCase();
      node.removeAttribute("align");
      node.setAttribute("class", `${ELEMENT_CLASS[tag]} ${ALIGN_CLASS[align] || "text-left"}`);
      return;
    }
    if (node.hasAttribute?.("align")) node.removeAttribute("align");
    if (tag === "A") {
      node.setAttribute("target", "_blank");
      node.setAttribute("rel", "noopener noreferrer nofollow");
    }
    if (ELEMENT_CLASS[tag] && tag !== "TABLE") node.setAttribute("class", ELEMENT_CLASS[tag]);
  });
  return purifier;
}

function sanitize(html) {
  return getPurifier().sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
    // DOMPurify checks EVERY non-safelisted attribute value against this, so it
    // must pass scheme-less values (align, d, width…) while allowing only the
    // http(s)/mailto schemes: DOMPurify's default shape minus the extra protocols.
    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z+.-]+(?:[^a-z+.\-:]|$))/i,
    ADD_ATTR: ["target"],
  });
}

// Markdown syntax that collides with arithmetic in quant stems: `5*4*3` would
// italicise the 4 and `~10 to ~20` would strike through. Escape both in text
// segments; genuine emphasis (`*x*`, `**Case**`) is unaffected.
function protectArithmetic(s) {
  return s.replace(/(\d)\s*\*(?=\s*\d)/g, (m) => m.replace("*", "\\*")).replace(/~/g, "\\~");
}

const BLOCK_TAG = /<(?:p|div|table|ul|ol|pre|blockquote|h[1-6]|hr)[\s>]/g;

/** Strip the wrapper when the whole output is exactly one paragraph. */
function unwrapSingleParagraph(html) {
  const trimmed = html.trim();
  if (!trimmed.startsWith("<p") || !trimmed.endsWith("</p>")) return html;
  const blocks = trimmed.match(BLOCK_TAG) || [];
  if (blocks.length !== 1) return html;
  return trimmed.replace(/^<p[^>]*>/, "").replace(/<\/p>$/, "");
}

/**
 * Render `text` to sanitised HTML.
 *   inline      — inline markdown only (no paragraphs/tables/lists); for options.
 *   renderMath  — (tex, display) => html; omitted → math shown as escaped source.
 * Returns `{ html, block }`; `block` is true when the result holds block markup.
 */
export function renderMarkdown(text, { inline = false, renderMath = null } = {}) {
  const segments = splitMath(typeof text === "string" ? text : "");
  const maths = [];
  let src = "";
  for (const seg of segments) {
    if (seg.type === "math") {
      src += `${PH_OPEN}${maths.length}${PH_CLOSE}`;
      maths.push(seg);
    } else {
      src += protectArithmetic(seg.value);
    }
  }

  let html = inline ? marked.parseInline(src) : marked.parse(src);
  html = html.replace(/<table>/g, '<div class="overflow-x-auto max-w-full my-2"><table class="' + ELEMENT_CLASS.TABLE + '">')
    .replace(/<\/table>/g, "</table></div>");
  html = html.replace(PH_RE, (_m, idx) => {
    const seg = maths[Number(idx)];
    if (!seg) return "";
    if (renderMath) {
      try {
        return renderMath(seg.value, seg.display);
      } catch {
        /* fall through to source */
      }
    }
    const d = seg.display ? "$$" : "$";
    return escapeHtml(`${d}${seg.value}${d}`);
  });

  let clean = sanitize(html);
  if (!inline) clean = unwrapSingleParagraph(clean);
  const block = !inline && (clean.match(BLOCK_TAG) || []).length > 0;
  return { html: clean, block };
}

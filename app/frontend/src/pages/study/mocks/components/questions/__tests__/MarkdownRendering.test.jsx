import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import MarkdownSafe from "../shared/MarkdownSafe";
import MathRenderer from "../shared/MathRenderer";
import { splitMath, hasMath } from "../shared/mathSegments";
import { renderMath } from "../shared/_katexRuntime";
import OptionList from "../shared/OptionList";
import MCQSingle from "../types/MCQSingle";
import MCQMulti from "../types/MCQMulti";

// Costing CST-020 stem, verbatim.
const CST_020 =
  "Monthly maintenance cost of a plant:\n\n| Month | Output (units) | Cost (₹) |\n|---|---:|---:|\n| Apr | 6,000 | 2,00,000 |\n| May | 4,000 | 1,56,000 |\n| Jun | 8,000 | 2,70,000 |\n| Jul | 9,000 | 2,66,000 |\n\nUsing the high–low method, the estimated cost at 7,500 units is:";

const FRACTION = "Cost per unit = $\\frac{2,70,000 - 1,56,000}{8,000 - 4,000}$";

const CURRENCY = [
  "The spot rate is ₹80/$. …",
  "₹84 per $; PPP holds",
  "costs ₹2,400 in India and $40 in the US",
  "US$450 bn, merchandise imports US$680 bn",
  "₹80/$ to ₹84/$",
  // Combinations that pair a plausible opener with a plausible closer.
  "The spot rate is ₹80/$. The forward rate is ₹84/$.",
  "It costs $40 in the US; the rate is ₹80/$.",
  "Prices: $40 and US$50.",
  "A literal \\$5 fee",
];

describe("splitMath delimiter rules", () => {
  test.each(CURRENCY)("currency is never math: %s", (s) => {
    expect(hasMath(s)).toBe(false);
    expect(splitMath(s).every((seg) => seg.type === "text")).toBe(true);
  });

  test("inline and display math are detected", () => {
    expect(splitMath("a $x^2$ b")).toEqual([
      { type: "text", value: "a " },
      { type: "math", value: "x^2", display: false },
      { type: "text", value: " b" },
    ]);
    expect(splitMath("$$\\frac{a}{b}$$")).toEqual([{ type: "math", value: "\\frac{a}{b}", display: true }]);
    expect(hasMath(FRACTION)).toBe(true);
  });

  test("closing $ followed by a digit does not close", () => {
    expect(hasMath("$x $5")).toBe(false);
    expect(hasMath("$x$5")).toBe(false);
  });
});

describe("MarkdownSafe GFM rendering", () => {
  test("CST-020 table renders 4 body rows with right-aligned numeric columns", () => {
    const { container } = render(<MarkdownSafe text={CST_020} />);
    const table = container.querySelector("table");
    expect(table).not.toBeNull();
    expect(table.parentElement.className).toContain("overflow-x-auto");
    const rows = table.querySelectorAll("tbody tr");
    expect(rows).toHaveLength(4);
    rows.forEach((row) => {
      const cells = row.querySelectorAll("td");
      expect(cells[0].className).toContain("text-left");
      expect(cells[1].className).toContain("text-right");
      expect(cells[2].className).toContain("text-right");
      expect(cells[1].hasAttribute("align")).toBe(false);
    });
    expect(table.querySelectorAll("thead th")[2].textContent).toBe("Cost (₹)");
    expect(container.textContent).toContain("Using the high–low method");
    expect(container.innerHTML).toMatchSnapshot();
  });

  test("bold, italic and line breaks", () => {
    const { container } = render(<MarkdownSafe text={"**Case — Alpha Ltd**\nline two *em*"} />);
    expect(container.querySelector("strong").textContent).toBe("Case — Alpha Ltd");
    expect(container.querySelector("em").textContent).toBe("em");
    expect(container.querySelector("br")).not.toBeNull();
    // Single paragraph → rendered inline, no <p> wrapper.
    expect(container.querySelector("p")).toBeNull();
  });

  test("arithmetic asterisks are not emphasis", () => {
    const { container } = render(<MarkdownSafe text="5*4*3 = 60" />);
    expect(container.querySelector("em")).toBeNull();
    expect(container.textContent).toBe("5*4*3 = 60");
  });

  test("inline mode renders no block elements (options)", () => {
    const { container } = render(<MarkdownSafe text={"**A** only\n\nsecond"} inline />);
    expect(container.querySelector("p")).toBeNull();
    expect(container.querySelector("strong")).not.toBeNull();
  });
});

describe("MarkdownSafe XSS", () => {
  const cases = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "[x](javascript:alert(1))",
    "| a | b |\n|---|---|\n| <b onmouseover=alert(1)>hi</b> | 2 |",
  ];

  test.each(cases)("no live markup from %s", (src) => {
    window.alert = jest.fn();
    const { container } = render(<MarkdownSafe text={src} />);
    expect(container.querySelector("script, img, b, iframe")).toBeNull();
    container.querySelectorAll("*").forEach((el) => {
      Array.from(el.attributes).forEach((attr) => {
        expect(attr.name.startsWith("on")).toBe(false);
        expect(/javascript:/i.test(attr.value)).toBe(false);
      });
    });
    expect(window.alert).not.toHaveBeenCalled();
  });

  test("raw HTML is shown as text", () => {
    const { container } = render(<MarkdownSafe text="<script>alert(1)</script>" />);
    expect(container.textContent).toContain("<script>alert(1)</script>");
    const cell = render(<MarkdownSafe text={cases[3]} />).container.querySelector("tbody td");
    expect(cell.textContent).toContain("<b onmouseover=alert(1)>");
  });
});

describe("Math rendering", () => {
  test("renderMath produces KaTeX HTML with a fraction", () => {
    const { container } = render(<MarkdownSafe text={FRACTION} renderMath={renderMath} />);
    const k = container.querySelector(".katex");
    expect(k).not.toBeNull();
    expect(container.querySelector(".mfrac")).not.toBeNull();
    expect(container.querySelector("[role='math']").getAttribute("aria-label")).toContain("\\frac");
    expect(container.textContent).toContain("Cost per unit =");
  });

  test("KaTeX radical SVG and positioning styles survive sanitising", () => {
    const { container } = render(<MarkdownSafe text="$\sqrt{2}$" renderMath={renderMath} />);
    expect(container.querySelector(".katex svg path").getAttribute("d")).toBeTruthy();
    expect(container.querySelector(".katex span[style]")).not.toBeNull();
  });

  test("MathRenderer lazy-loads KaTeX for real math", async () => {
    const { container } = render(<MathRenderer text={FRACTION} />);
    await waitFor(() => expect(container.querySelector(".katex .mfrac")).not.toBeNull());
  });

  test("math inside a table cell survives the markdown pass", () => {
    const src = "| k | v |\n|---|---:|\n| r | $\\frac{1}{2}$ |";
    const { container } = render(<MarkdownSafe text={src} renderMath={renderMath} />);
    expect(container.querySelector("td .katex .mfrac")).not.toBeNull();
  });

  test.each(CURRENCY)("currency renders with no KaTeX and $ visible: %s", async (s) => {
    const { container } = render(<MathRenderer text={s} />);
    // Even with the renderer present, nothing is treated as math.
    const direct = render(<MarkdownSafe text={s} renderMath={renderMath} />).container;
    expect(direct.querySelector(".katex")).toBeNull();
    expect(direct.textContent).toContain("$");
    expect(container.querySelector(".katex")).toBeNull();
    expect(container.textContent).toContain("$");
  });
});

describe("Question surfaces", () => {
  const options = [
    { id: "o1", option_text: "**₹2,53,000**", display_order: 1 },
    { id: "o2", option_text: "₹2,40,000", display_order: 2 },
  ];

  test("options render inline markdown without block paragraphs", () => {
    const { container } = render(<OptionList options={options} onSelect={() => {}} />);
    expect(container.querySelector("button strong + span strong").textContent).toBe("₹2,53,000");
    expect(container.querySelector("button p")).toBeNull();
  });

  const q = {
    id: "q1",
    question_type: "mcq_single",
    question_text: CST_020,
    options,
    correct_option_id: "o1",
    explanation: "Variable cost = **₹28.5** per unit.",
    common_trap: "Using the highest *cost* instead of the highest activity.",
  };

  test("common trap renders in review mode below the explanation", () => {
    render(<MCQSingle question={q} mode="review" showCorrect showExplanation onChange={() => {}} />);
    const trap = screen.getByTestId("question-common-trap");
    expect(trap).toHaveTextContent("Common trap");
    expect(trap).toHaveTextContent("Using the highest cost instead of the highest activity.");
    expect(trap.querySelector("em")).not.toBeNull();
  });

  test("common trap never renders during an active attempt", () => {
    render(<MCQSingle question={q} mode="attempt" onChange={() => {}} />);
    expect(screen.queryByTestId("question-common-trap")).toBeNull();
    render(<MCQMulti question={{ ...q, question_type: "msq" }} mode="attempt" onChange={() => {}} />);
    expect(screen.queryByTestId("question-common-trap")).toBeNull();
  });

  test("common trap renders in MCQMulti review", () => {
    render(<MCQMulti question={{ ...q, question_type: "msq" }} mode="review" showExplanation onChange={() => {}} />);
    expect(screen.getByTestId("question-common-trap")).toBeInTheDocument();
  });
});

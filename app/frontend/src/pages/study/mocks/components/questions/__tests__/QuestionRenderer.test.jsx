import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import QuestionRenderer from "../QuestionRenderer";

const q = { id:"q1", question_type:"mcq_single", question_text:"Pick one", options:[{id:"o1",option_index:"A",option_text:"One"},{id:"o2",option_index:"B",option_text:"<script>alert(1)</script>"}], correct_option_id:"o1", explanation:"ok" };

test("xss payload renders as text", ()=>{ const onChange=jest.fn(); render(<QuestionRenderer question={q} mode="attempt" value={{}} onChange={onChange} />); expect(screen.getByText("<script>alert(1)</script>")).toBeTruthy(); });

test("keyboard navigation and selection", ()=>{ const onChange=jest.fn(); render(<QuestionRenderer question={q} mode="attempt" value={{}} onChange={onChange} />); const first=screen.getByRole("button",{name:/A\./}); first.focus(); fireEvent.keyDown(first,{key:"2"}); expect(onChange).toHaveBeenCalled(); fireEvent.keyDown(first,{key:"Enter"}); expect(onChange).toHaveBeenCalled();});

// ── PYQ v2 PR-5/6: projected passage + printed option labels ──────────────────

test("renders a projected passage stimulus above the stem", ()=>{
  const pyq = { ...q, stimuli:[{ id:"s1", stimulus_type:"passage", content_text:"Read the following passage.", display_order:1 }] };
  render(<QuestionRenderer question={pyq} mode="attempt" value={{}} onChange={jest.fn()} />);
  expect(screen.getByTestId("question-stimuli")).toBeTruthy();
  expect(screen.getByText(/Read the following passage\./)).toBeTruthy();
  expect(screen.getByText("Passage")).toBeTruthy();
});

test("no stimuli block for a question without stimuli", ()=>{
  render(<QuestionRenderer question={q} mode="attempt" value={{}} onChange={jest.fn()} />);
  expect(screen.queryByTestId("question-stimuli")).toBeNull();
});

test("prefers projected option source_label over the letter", ()=>{
  const pyq = { ...q, options:[{ id:"o1", option_index:1, source_label:"(a)", option_text:"One" },{ id:"o2", option_index:2, source_label:"(b)", option_text:"Two" }] };
  render(<QuestionRenderer question={pyq} mode="attempt" value={{}} onChange={jest.fn()} />);
  expect(screen.getByRole("button",{name:/\(a\)/})).toBeTruthy();
  expect(screen.getByRole("button",{name:/\(b\)/})).toBeTruthy();
});

test("renders options in display_order, not array/option_index order", ()=>{
  // supplied out of printed order: (b) first in the array but display_order says (a) first
  const pyq = { ...q, options:[
    { id:"o2", option_index:2, display_order:2, source_label:"(b)", option_text:"Beta" },
    { id:"o1", option_index:1, display_order:1, source_label:"(a)", option_text:"Alpha" },
  ] };
  render(<QuestionRenderer question={pyq} mode="attempt" value={{}} onChange={jest.fn()} />);
  const labels = screen.getAllByRole("button").map((b)=>b.textContent);
  const aIdx = labels.findIndex((t)=>/\(a\)/.test(t));
  const bIdx = labels.findIndex((t)=>/\(b\)/.test(t));
  expect(aIdx).toBeGreaterThanOrEqual(0);
  expect(aIdx).toBeLessThan(bIdx); // (a) rendered before (b)
});

// ── PYQ v2 PR-11: media stimuli (image/chart/diagram) ─────────────────────────

test("renders a media stimulus as an image with alt text", ()=>{
  const pyq = { ...q, stimuli:[{ id:"m1", stimulus_type:"image", asset_url:"https://cdn.example/x.png", alt_text:"A Venn diagram of three sets", display_order:1 }] };
  render(<QuestionRenderer question={pyq} mode="attempt" value={{}} onChange={jest.fn()} />);
  const img = screen.getByTestId("question-stimulus-media-0");
  expect(img.tagName).toBe("IMG");
  expect(img.getAttribute("src")).toBe("https://cdn.example/x.png");
  expect(img.getAttribute("alt")).toBe("A Venn diagram of three sets");
  expect(screen.getByText("Image")).toBeTruthy();
});

test("falls back to alt text when a media stimulus has no asset url", ()=>{
  const pyq = { ...q, stimuli:[{ id:"m2", stimulus_type:"chart", alt_text:"Bar chart: sales by quarter", display_order:1 }] };
  render(<QuestionRenderer question={pyq} mode="attempt" value={{}} onChange={jest.fn()} />);
  expect(screen.queryByTestId("question-stimulus-media-0")).toBeNull(); // no <img>
  const fb = screen.getByTestId("question-stimulus-media-fallback-0");
  expect(fb.getAttribute("aria-label")).toBe("Bar chart: sales by quarter");
  expect(screen.getByText(/Bar chart: sales by quarter/)).toBeTruthy();
});

test("media stimulus does not render its content_text as markdown body", ()=>{
  const pyq = { ...q, stimuli:[{ id:"m3", stimulus_type:"diagram", asset_url:"https://cdn.example/d.png", alt_text:"flow", content_text:"raw-caption", display_order:1 }] };
  render(<QuestionRenderer question={pyq} mode="attempt" value={{}} onChange={jest.fn()} />);
  expect(screen.getByTestId("question-stimulus-media-0")).toBeTruthy();
  expect(screen.queryByText("raw-caption")).toBeNull();
});

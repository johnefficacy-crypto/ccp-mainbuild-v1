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

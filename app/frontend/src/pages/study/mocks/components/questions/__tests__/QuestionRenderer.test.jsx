import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import QuestionRenderer from "../QuestionRenderer";

const q = { id:"q1", question_type:"mcq_single", question_text:"Pick one", options:[{id:"o1",option_index:"A",option_text:"One"},{id:"o2",option_index:"B",option_text:"<script>alert(1)</script>"}], correct_option_id:"o1", explanation:"ok" };

test("xss payload renders as text", ()=>{ const onChange=jest.fn(); render(<QuestionRenderer question={q} mode="attempt" value={{}} onChange={onChange} />); expect(screen.getByText("<script>alert(1)</script>")).toBeTruthy(); });

test("keyboard navigation and selection", ()=>{ const onChange=jest.fn(); render(<QuestionRenderer question={q} mode="attempt" value={{}} onChange={onChange} />); const first=screen.getByRole("button",{name:/A\./}); first.focus(); fireEvent.keyDown(first,{key:"2"}); expect(onChange).toHaveBeenCalled(); fireEvent.keyDown(first,{key:"Enter"}); expect(onChange).toHaveBeenCalled();});

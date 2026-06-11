import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ExamListTable from "./ExamListTable";

const ITEMS = [
  {
    id: "e1", slug: "ssc-cgl", name: "SSC CGL", exam_type: "recruitment",
    is_active: true, syllabus_verified: 2, syllabus_pending: 1,
    verified_topic_count: 3, coverage_total: 5, high_yield_topic_count: 2,
    readiness_level: "ready", pyq_coverage_status: "covered",
  },
  {
    id: "e2", slug: "ibps-po", name: "IBPS PO", exam_type: "recruitment",
    is_active: false, syllabus_verified: 0, syllabus_pending: 1,
    verified_topic_count: 0, coverage_total: 0, high_yield_topic_count: 0,
    readiness_level: "not_ready", pyq_coverage_status: "none",
  },
];

function wrap(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

// ── table renders ──────────────────────────────────────────────────────────

test("renders rows for each item", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expect(screen.getByText("SSC CGL")).toBeInTheDocument();
  expect(screen.getByText("IBPS PO")).toBeInTheDocument();
});

test("renders empty state when no items and page is 0", () => {
  wrap(<ExamListTable items={[]} total_count={0} />);
  expect(screen.getByText(/no exams registered yet/i)).toBeInTheDocument();
});

// ── pagination footer ──────────────────────────────────────────────────────

test("renders pagination footer with range", () => {
  wrap(<ExamListTable items={ITEMS} page={0} pageSize={25} total_count={30} has_next offset={0} />);
  expect(screen.getByTestId("exam-intel-pagination")).toBeInTheDocument();
  expect(screen.getByTestId("exam-intel-range")).toHaveTextContent("1–2 of 30");
});

test("prev button disabled on first page", () => {
  wrap(<ExamListTable items={ITEMS} page={0} pageSize={25} total_count={30} has_next offset={0} />);
  expect(screen.getByTestId("exam-intel-prev")).toBeDisabled();
});

test("next button enabled when has_next is true", () => {
  wrap(<ExamListTable items={ITEMS} page={0} pageSize={25} total_count={30} has_next={true} offset={0} />);
  expect(screen.getByTestId("exam-intel-next")).not.toBeDisabled();
});

test("next button disabled when has_next is false", () => {
  wrap(<ExamListTable items={ITEMS} page={0} pageSize={25} total_count={2} has_next={false} offset={0} />);
  expect(screen.getByTestId("exam-intel-next")).toBeDisabled();
});

test("prev button enabled on page > 0", () => {
  wrap(<ExamListTable items={ITEMS} page={1} pageSize={25} total_count={30} has_next={false} offset={25} />);
  expect(screen.getByTestId("exam-intel-prev")).not.toBeDisabled();
});

test("clicking next calls onPageChange with page + 1", () => {
  const onChange = jest.fn();
  wrap(
    <ExamListTable
      items={ITEMS} page={0} pageSize={25} total_count={30}
      has_next={true} offset={0} onPageChange={onChange}
    />
  );
  fireEvent.click(screen.getByTestId("exam-intel-next"));
  expect(onChange).toHaveBeenCalledWith(1);
});

test("clicking prev calls onPageChange with page - 1", () => {
  const onChange = jest.fn();
  wrap(
    <ExamListTable
      items={ITEMS} page={2} pageSize={25} total_count={75}
      has_next={false} offset={50} onPageChange={onChange}
    />
  );
  fireEvent.click(screen.getByTestId("exam-intel-prev"));
  expect(onChange).toHaveBeenCalledWith(1);
});

// ── readiness columns preserved ────────────────────────────────────────────

test("readiness badge renders for each row", () => {
  wrap(<ExamListTable items={ITEMS} total_count={2} />);
  expect(screen.getByText("ready")).toBeInTheDocument();
  expect(screen.getByText("not ready")).toBeInTheDocument();
});

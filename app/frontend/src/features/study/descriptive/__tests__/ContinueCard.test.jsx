/**
 * The open draft, offered back.
 *
 * It is the single most likely thing an aspirant returns for, and it is the
 * one place a question appears with no subject chosen — so its label has to
 * carry the subject, which is the whole reason this surface got reworked.
 */
import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import ContinueCard from "../ContinueCard";
import { api } from "../../../../lib/api";

jest.mock("../../../../lib/api", () => ({ api: { get: jest.fn() } }));

const DRAFT = {
  items: [
    {
      id: "a-1",
      status: "draft",
      question: {
        id: "q-1",
        excerpt: "Examine the idea of sovereignty in a globalised order.",
        subject: "Political Science and International Relations",
        breadcrumb: { trail: [], source: "2019 · P1 · Q5(b) · 15 marks" },
      },
    },
  ],
};

beforeEach(() => {
  api.get.mockReset();
  api.get.mockResolvedValue(DRAFT);
});

test("shows the draft's excerpt and offers a resume", async () => {
  render(<ContinueCard onResume={jest.fn()} />);
  expect(await screen.findByTestId("descriptive-continue-excerpt")).toHaveTextContent(
    "Examine the idea of sovereignty",
  );
  expect(screen.getByTestId("descriptive-continue-resume")).toBeInTheDocument();
});

test("the breadcrumb names the subject, because nothing else here does", async () => {
  render(<ContinueCard onResume={jest.fn()} />);
  const crumb = await screen.findByTestId("descriptive-continue-crumb");
  expect(crumb).toHaveTextContent("Political Science and International Relations");
  expect(crumb).toHaveTextContent("2019 · P1 · Q5(b) · 15 marks");
});

test("it asks only for the open draft", async () => {
  render(<ContinueCard onResume={jest.fn()} />);
  await screen.findByTestId("descriptive-continue-excerpt");
  expect(api.get).toHaveBeenCalledWith(expect.stringContaining("status=draft"));
  expect(api.get).toHaveBeenCalledWith(expect.stringContaining("limit=1"));
});

test("resume hands back the question id", async () => {
  const onResume = jest.fn();
  render(<ContinueCard onResume={onResume} />);
  fireEvent.click(await screen.findByTestId("descriptive-continue-resume"));
  expect(onResume).toHaveBeenCalledWith("q-1");
});

test("no open draft renders nothing at all", async () => {
  api.get.mockResolvedValue({ items: [] });
  const { container } = render(<ContinueCard onResume={jest.fn()} />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(container).toBeEmptyDOMElement();
});

test("a failed read renders nothing rather than an error over the catalogue", async () => {
  /* It is a shortcut. A broken shortcut must not become the first thing an
     aspirant sees. */
  api.get.mockRejectedValue(new Error("boom"));
  const { container } = render(<ContinueCard onResume={jest.fn()} />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(container).toBeEmptyDOMElement();
});

test("a draft whose question could not be resolved renders nothing", async () => {
  api.get.mockResolvedValue({ items: [{ id: "a-1", status: "draft", question: {} }] });
  const { container } = render(<ContinueCard onResume={jest.fn()} />);
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(container).toBeEmptyDOMElement();
});

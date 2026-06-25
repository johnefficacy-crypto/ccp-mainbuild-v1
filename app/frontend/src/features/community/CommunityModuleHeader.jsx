import React from "react";
import { NavLink } from "react-router-dom";
import { FieldLabel } from "./ui";

const COMMUNITY_LINKS = [
  { to: "/app/community", label: "Discussions", end: false },
  { to: "/app/groups", label: "Groups", end: true },
  { to: "/app/partners", label: "Partners", end: true },
  { to: "/app/mentors", label: "Mentors", end: true },
  { to: "/app/resources", label: "Resources", end: true },
];

export default function CommunityModuleHeader() {
  return (
    <header className="mb-5 flex flex-col gap-4 rounded-2xl border border-border bg-white/65 p-4 shadow-sm sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <FieldLabel>Community</FieldLabel>
        <h1 className="mt-1 font-heading text-2xl font-semibold tracking-tight text-foreground">
          Discuss, study, and find support.
        </h1>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
          Exam-safe discussions, study groups, accountability partners, mentors, and moderated resources stay in one module.
        </p>
      </div>
      <nav aria-label="Community sections" className="flex gap-2 overflow-x-auto pb-1 sm:pb-0">
        {COMMUNITY_LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              `whitespace-nowrap rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
                isActive
                  ? "border-clay-500 bg-clay-500 text-white"
                  : "border-border bg-white/80 text-muted-foreground hover:border-clay-300 hover:text-foreground"
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}

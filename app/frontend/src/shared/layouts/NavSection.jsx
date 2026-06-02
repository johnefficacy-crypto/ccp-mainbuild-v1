import React, { useEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { ChevronDown } from "lucide-react";

export default function NavSection({ label, items = [], onItemClick, tone = "app", collapsed = false, collapsible = false, defaultOpen = true, testId }) {
  const adminTone = tone === "admin";
  const [open, setOpen] = useState(defaultOpen);
  const { pathname } = useLocation();
  // Track whether the user has manually toggled this section since the last
  // navigation so we don't re-open a section they explicitly closed.
  const manualRef = useRef(false);

  useEffect(() => {
    // Reset the manual-override flag on every navigation so the next
    // pathname change can auto-open again.
    manualRef.current = false;
  }, [pathname]);

  useEffect(() => {
    if (!collapsible || collapsed) return;
    if (manualRef.current) return;
    // Auto-open when any child route matches the current pathname.
    const matches = items.some((item) => {
      if (item.end) return pathname === item.to;
      return pathname === item.to || pathname.startsWith(`${item.to}/`);
    });
    if (matches) setOpen(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);
  const showLabel = !!label && !collapsed;
  const isCollapsible = collapsible && !collapsed;
  const visible = isCollapsible ? open : true;

  return (
    <div className={isCollapsible ? "mt-1" : ""}>
      {showLabel && (
        isCollapsible ? (
          <button
            type="button"
            onClick={() => { manualRef.current = true; setOpen((v) => !v); }}
            aria-expanded={open}
            data-testid={testId}
            className="nav-section flex items-center justify-between w-full select-none"
          >
            <span>{label}</span>
            <ChevronDown
              className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-0" : "-rotate-90"}`}
              strokeWidth={2}
              aria-hidden="true"
            />
          </button>
        ) : (
          <div className="nav-section">{label}</div>
        )
      )}
      {visible && (
        <div className="space-y-0.5">
          {items.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              onClick={onItemClick}
              data-testid={l.testId}
              title={collapsed ? l.label : l.description}
              className={({ isActive }) =>
                `nav-link ${adminTone ? "nav-link-admin" : ""} ${isActive ? "active" : ""} ${collapsed ? "justify-center" : ""}`
              }
            >
              <l.icon className="nav-glyph h-4 w-4 shrink-0" strokeWidth={1.8} />
              {!collapsed && <span className="truncate flex-1">{l.label}</span>}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

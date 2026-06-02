import React from "react";
import { Link, useLocation } from "react-router-dom";
import { getBreadcrumbs } from "../navigation/appBreadcrumbs";
import { useBreadcrumbLeafValue } from "../navigation/BreadcrumbLeafContext";

/**
 * Renders a quiet breadcrumb trail above page content for deep routes.
 * Returns null on shallow routes (D3 denylist) and unmapped paths.
 *
 * Markup:
 *   <nav aria-label="Breadcrumb">
 *     <ol>
 *       <li><Link>Ancestor</Link></li> ...
 *       <li aria-current="page">Leaf</li>
 *     </ol>
 *   </nav>
 *
 * Mobile: horizontally scrollable, no wrap.
 * Desktop: full trail, no scroll needed.
 */
export default function AppBreadcrumbs() {
  const { pathname } = useLocation();
  const leafOverride = useBreadcrumbLeafValue();
  const trail = getBreadcrumbs(pathname, leafOverride);

  if (!trail) return null;

  const { ancestors, leaf } = trail;

  return (
    <nav aria-label="Breadcrumb" className="mb-3">
      <ol className="flex items-center gap-1 overflow-x-auto scrollbar-none whitespace-nowrap text-sm text-muted-foreground">
        {ancestors.map((a) => (
          <li key={a.to} className="flex items-center gap-1 shrink-0">
            <Link
              to={a.to}
              className="hover:text-foreground transition-colors underline-offset-2 hover:underline"
            >
              {a.label}
            </Link>
            <span aria-hidden="true" className="select-none opacity-50">/</span>
          </li>
        ))}
        <li aria-current="page" className="shrink-0 text-foreground font-medium">
          {leaf}
        </li>
      </ol>
    </nav>
  );
}

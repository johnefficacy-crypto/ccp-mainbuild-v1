import { getBreadcrumbs } from "./appBreadcrumbs";

describe("app breadcrumbs", () => {
  it("renders nothing for a bare unmapped space (no resolved leaf)", () => {
    // A bare /app/community/:spaceId that never resolves (no leaf override) is
    // a shallow landing, not a deep route — it must not render a trail.
    expect(getBreadcrumbs("/app/community/upsc")).toBeNull();
    expect(getBreadcrumbs("/app/community/foo")).toBeNull();
  });

  it("uses full Community ancestry for deep discussion routes", () => {
    // A bare space shows a trail once it resolves to a real name (leaf override).
    expect(getBreadcrumbs("/app/community/upsc", "UPSC")).toEqual({
      ancestors: [{ label: "Community", to: "/app/community" }],
      leaf: "UPSC",
    });

    expect(getBreadcrumbs("/app/community/upsc/general")).toEqual({
      ancestors: [
        { label: "Community", to: "/app/community" },
        { label: "Space", to: "/app/community/upsc" },
      ],
      leaf: "Channel",
    });

    expect(getBreadcrumbs("/app/community/upsc/general/thread-1", "Mains PYQ doubt")).toEqual({
      ancestors: [
        { label: "Community", to: "/app/community" },
        { label: "Space", to: "/app/community/upsc" },
        { label: "Channel", to: "/app/community/upsc/general" },
      ],
      leaf: "Mains PYQ doubt",
    });
  });
});

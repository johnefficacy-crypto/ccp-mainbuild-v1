import { getBreadcrumbs } from "./appBreadcrumbs";

describe("app breadcrumbs", () => {
  it("uses full Community ancestry for deep discussion routes", () => {
    expect(getBreadcrumbs("/app/community/upsc")).toEqual({
      ancestors: [{ label: "Community", to: "/app/community" }],
      leaf: "Space",
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

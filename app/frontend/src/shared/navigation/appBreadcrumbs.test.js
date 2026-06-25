import { getBreadcrumbs } from "./appBreadcrumbs";

describe("app breadcrumbs", () => {
  it("uses Community as the ancestor for deep discussion routes", () => {
    expect(getBreadcrumbs("/app/community/upsc/general")).toEqual({
      ancestors: [{ label: "Community", to: "/app/community" }],
      leaf: "Channel",
    });

    expect(getBreadcrumbs("/app/community/upsc/general/thread-1", "Mains PYQ doubt")).toEqual({
      ancestors: [{ label: "Community", to: "/app/community" }],
      leaf: "Mains PYQ doubt",
    });
  });
});

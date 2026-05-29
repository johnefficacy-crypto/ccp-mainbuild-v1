/**
 * @deprecated Import from `shared/ui/core` or `shared/ui/heavy`.
 *
 * Backwards-compat policy: this barrel intentionally re-exports CORE only,
 * so accidental bare imports cannot drag heavy deps into the initial bundle.
 */
export * from "./core";

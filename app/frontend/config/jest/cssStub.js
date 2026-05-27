// Jest stub for package CSS side-effect imports (e.g. `react-day-picker/style.css`).
// react-day-picker v9 exposes its stylesheet only through the package `exports`
// map; react-scripts 5's jest resolver does not follow that subpath, so the
// import fails to resolve under `npm test` even though webpack builds it fine.
// The stylesheet has no runtime exports, so an empty module is a faithful stand-in.
module.exports = {};

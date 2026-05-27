import React, { Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import NotFound from "./pages/NotFound";
import { adminRouteElements } from "./routes/adminRoutes";
import { appRouteElements } from "./routes/appRoutes";
import { publicRouteElements } from "./routes/publicRoutes";
import { LoadingSkeleton } from "./shared/ui";

export default function App() {
  return (
    <Suspense fallback={<LoadingSkeleton />}>
      <Routes>
        {publicRouteElements}
        {appRouteElements}
        {adminRouteElements}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
import React, { Suspense, lazy } from "react";
import ChartSkeleton from "./ChartSkeleton";

const ChartCardImpl = lazy(() => import("./ChartCard.impl"));

export const ChartCard = (props) => (
  <Suspense fallback={<ChartSkeleton height={props.height} />}>
    <ChartCardImpl {...props} />
  </Suspense>
);

export default ChartCard;

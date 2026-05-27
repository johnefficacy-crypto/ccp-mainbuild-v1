import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../../../lib/api";
import MockAttemptShell from "./MockAttemptShell";
import TcsIonAttemptShell from "./TcsIonAttemptShell";

export default function AttemptShellRouter() {
  const { attemptId } = useParams();
  const [mode, setMode] = useState(null);

  useEffect(() => {
    (async () => {
      const data = await api.get(`/study/mocks/attempts/${attemptId}`);
      setMode(data?.template_interface_mode || data?.template_config?.interface_mode || "simple");
    })();
  }, [attemptId]);

  if (!mode) return <div>Loading…</div>;
  return mode === "tcs_ion" ? <TcsIonAttemptShell /> : <MockAttemptShell />;
}

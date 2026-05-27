import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import "react-day-picker/style.css";
import "./index.css";
import App from "./App";
// Policy: framer-motion imports are allowed only inside lazy-loaded route subtrees.
// Keep / and /login motion-free in initial bundles; do not import framer-motion from eagerly loaded modules.
import { AuthProvider } from "./lib/authContext";
import { queryClient } from "./shared/api/queryClient";
import { ToastProvider } from "./shared/ui/core";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);

import React from "react";
import { AlertTriangle } from "lucide-react";
import { Link, Outlet, useLocation } from "react-router-dom";

class ErrorBoundaryInner extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error, info) {
    if (process.env.NODE_ENV !== "production") console.error("Route render failed", error, info);
  }
  render() {
    if (this.state.hasError) {
      return <div className="soft-card rounded-2xl p-6 max-w-2xl mx-auto mt-8"><div className="inline-flex items-center gap-2 text-clay-700 font-semibold"><AlertTriangle className="h-4 w-4" /> Something went wrong on this page</div><p className="text-sm text-muted-foreground mt-2">We could not render this screen. Please go back to dashboard and retry.</p><Link to="/app" className="btn btn-primary mt-4 inline-flex">Back to dashboard</Link></div>;
    }
    return this.props.children;
  }
}

// Keying by location.key causes the class component to remount on every
// navigation, resetting hasError so a crash on one route can't poison another.
export default function RouteErrorBoundary() {
  const location = useLocation();
  return <ErrorBoundaryInner key={location.key}><Outlet /></ErrorBoundaryInner>;
}

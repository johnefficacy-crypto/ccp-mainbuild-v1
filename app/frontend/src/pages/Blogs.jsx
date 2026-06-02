import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

export default function Blogs() {
  const [items, setItems] = useState([]);
  const [loadError, setLoadError] = useState(false);
  useEffect(() => {
    api.get("/api/blogs")
      .then((d) => setItems(d.items || []))
      .catch(() => { setItems([]); setLoadError(true); });
  }, []);
  return <main className="container py-8">
    <h1 className="text-2xl font-bold">Career Copilot Blog</h1>
    <p className="text-sm text-muted-foreground">Exam discovery + eligibility + preparation action.</p>
    {loadError && (
      <div role="alert" className="mt-4 rounded-md border border-field-danger/40 bg-field-danger/10 px-4 py-3 text-[13px] text-field-danger">
        Could not load posts — check your connection and refresh.
      </div>
    )}
    <div className="stack mt-4" style={{ gap: 12 }}>
      {items.map((x) => <article key={x.id} className="card p-4">
        <h2 className="text-lg font-semibold"><Link to={`/blog/${x.slug}`}>{x.title}</Link></h2>
        <p className="text-sm">{x.excerpt}</p>
      </article>)}
    </div>
  </main>;
}

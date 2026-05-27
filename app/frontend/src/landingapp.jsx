// Career Copilot — landing page main app
// Sections: Hero, How it helps, Eligibility demo, Daily plan, Support, Trust, Exams, Pricing, FAQ, Footer
import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "./lib/authContext";
import {
  LogoMark,
  FloatCalendar, FloatBook, FloatClock,
  IconScan, IconCalendarFlip, IconClockSweep, IconChat,
  VerdictIcon,
  MiniBook, MiniPencil, MiniPaper, MiniBulb,
  SceneCommunity, SceneGroup, ScenePartner, SceneMentor, SceneResources, SceneShop,
  TrustFilterScene, ShieldCheck, ShieldQuestion,
} from "./landingart";
import "./landing.css";

// For `/app/*` deep links, send guests through signup with a `next` param so
// the CTA never dead-ends on a protected route; authed users go straight in.
function guestSafe(path, isAuthed) {
  if (isAuthed) return path;
  if (typeof path !== "string" || !path.startsWith("/app/")) return path;
  return `/signup?next=${encodeURIComponent(path)}`;
}

const prefersReduced = () => typeof window !== "undefined" && window.matchMedia
  && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// ---- Helpers ----
function useReveal() {
  const ref = useRef(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (prefersReduced() || typeof IntersectionObserver === "undefined") { setSeen(true); return; }
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } });
    }, { threshold: 0.18 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return [ref, seen];
}

function useScrolled(threshold = 40) {
  const [s, setS] = useState(false);
  useEffect(() => {
    const onScroll = () => setS(window.scrollY > threshold);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [threshold]);
  return s;
}

function rippleHandler(e) {
  if (prefersReduced()) return;
  const btn = e.currentTarget;
  const rect = btn.getBoundingClientRect();
  const r = document.createElement("span");
  r.className = "ripple";
  const size = Math.max(rect.width, rect.height);
  r.style.width = r.style.height = size + "px";
  r.style.left = (e.clientX - rect.left - size / 2) + "px";
  r.style.top  = (e.clientY - rect.top  - size / 2) + "px";
  btn.appendChild(r);
  setTimeout(() => r.remove(), 700);
}

function burstConfetti(originX, originY) {
  if (prefersReduced()) return;
  const colors = ["#E47A5A", "#5DA877", "#E0A640", "#6E9DD0", "#B3577A", "#2F7E7E"];
  const canvas = document.createElement("canvas");
  canvas.className = "confetti-canvas";
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  document.body.appendChild(canvas);
  const ctx = canvas.getContext("2d");
  const pieces = Array.from({ length: 60 }, () => ({
    x: originX, y: originY,
    vx: (Math.random() - 0.5) * 9,
    vy: -Math.random() * 9 - 3,
    g: 0.35,
    size: 4 + Math.random() * 4,
    color: colors[Math.floor(Math.random() * colors.length)],
    rot: Math.random() * Math.PI,
    vr: (Math.random() - 0.5) * 0.3,
    life: 60 + Math.random() * 30,
  }));
  let frame = 0;
  function tick() {
    frame++;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let alive = false;
    pieces.forEach(p => {
      if (p.life <= 0) return;
      alive = true;
      p.x += p.vx; p.y += p.vy; p.vy += p.g; p.rot += p.vr; p.life--;
      ctx.save();
      ctx.translate(p.x, p.y); ctx.rotate(p.rot);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
      ctx.restore();
    });
    if (alive && frame < 120) requestAnimationFrame(tick);
    else canvas.remove();
  }
  requestAnimationFrame(tick);
}

function Counter({ to, duration = 1100, suffix = "", trigger }) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!trigger) return;
    if (prefersReduced()) { setVal(to); return; }
    const start = performance.now();
    const tick = (t) => {
      const p = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(Math.round(to * eased));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [to, duration, trigger]);
  return <span>{val}{suffix}</span>;
}

// ---- Top nav ----
function Nav() {
  const scrolled = useScrolled(40);
  const auth = useAuth();
  const navigate = useNavigate();
  const startTarget = auth.isAuthed ? "/app" : "/signup";
  return (
    <nav className={"nav " + (scrolled ? "scrolled" : "")}>
      <div className="container nav-inner">
        <a href="#top" className="nav-logo">
          <LogoMark size={30} />
          <span>Career Copilot</span>
        </a>
        <div className="nav-links">
          <a href="#how">How it helps</a>
          <a href="#exams">Exams</a>
          <a href="#pricing">Pricing</a>
          <a href="#faq">FAQ</a>
        </div>
        <div className="nav-spacer" />
        <div className="nav-cta">
          <Link className="btn btn-ghost btn-sm" to="/login" onMouseDown={rippleHandler}>Log in</Link>
          <button className="btn btn-primary btn-sm" onMouseDown={rippleHandler} onClick={() => navigate(startTarget)}>
            Start free
          </button>
        </div>
      </div>
    </nav>
  );
}

// ---- Hero ----
function Hero() {
  const [mockSeenRef, mockSeen] = useReveal();
  const artRef = useRef(null);
  const auth = useAuth();
  const navigate = useNavigate();

  // Parallax on hero illustration
  useEffect(() => {
    if (prefersReduced()) return;
    const onScroll = () => {
      const el = artRef.current; if (!el) return;
      const y = window.scrollY;
      if (y > 600) return;
      el.style.transform = `translateY(${y * 0.12}px)`;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Headline words fade up with stagger
  const headline = "Find the right government exams.\nKnow what to study every day.";

  return (
    <header className="hero" id="top">
      <div className="container hero-grid">
        <div>
          <span className="eyebrow"><span className="dot"></span>For Indian government exam aspirants</span>
          <h1 className="hero-h">
            {headline.split("\n").map((line, li) => (
              <span key={li} style={{ display: "block" }}>
                {line.split(" ").map((w, i) => {
                  const isUnderline = (li === 1 && w === "every");
                  return (
                    <span key={i} className={"word" + (isUnderline ? " underline" : "")}
                          style={{ animationDelay: ((li * 6 + i) * 70 + 100) + "ms" }}>
                      {w}{i < line.split(" ").length - 1 ? " " : ""}
                    </span>
                  );
                })}
              </span>
            ))}
          </h1>
          <p className="hero-sub">
            Career Copilot helps you check which exams you can apply for, track important dates,
            follow a daily study plan, and get support when stuck.
          </p>
          <div className="hero-cta">
            <button className="btn btn-primary" onMouseDown={rippleHandler}
              onClick={(e) => {
                const r = e.currentTarget.getBoundingClientRect();
                burstConfetti(r.left + r.width / 2, r.top + r.height / 2);
                navigate(guestSafe("/app/eligibility", auth.isAuthed));
              }}>
              Check my eligibility <span className="arrow">→</span>
            </button>
            <button className="btn btn-secondary" onMouseDown={rippleHandler}
              onClick={() => navigate(guestSafe("/app/study/plan", auth.isAuthed))}>
              Start my study plan
            </button>
          </div>
          <div className="hero-meta">
            <span className="check">✓</span> Free to start. No credit card needed.
          </div>
        </div>

        <div className="hero-art" ref={artRef}>
          <div className="float float-1"><FloatCalendar /></div>
          <div className="float float-2"><FloatBook /></div>
          <div className="float float-3"><FloatClock /></div>

          <div className="mock" ref={mockSeenRef}>
            <div className="mock-dots"><i></i><i></i><i></i></div>
            <div className="mock-title">Your week at a glance</div>
            <div className="mock-cards">
              <div className="mcard">
                <div className="label">ELIGIBLE EXAMS</div>
                <div className="count"><Counter to={4} trigger={mockSeen} /></div>
                <div className="sub">SSC CGL, CHSL, RRB NTPC, Banking</div>
                <div className="corner">
                  <svg width="22" height="22" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#5DA877" /><path d="M7 12 l3 3 l7 -7" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </div>
              </div>
              <div className="mcard">
                <div className="label">UPCOMING DEADLINES</div>
                <div className="count"><Counter to={7} trigger={mockSeen} /></div>
                <div className="sub">Next: 28 May · Application close</div>
                <div className="corner">
                  <svg width="22" height="22" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="3" fill="#E0A640" /><rect x="3" y="5" width="18" height="5" rx="3" fill="#B58859" /></svg>
                </div>
              </div>
              <div className="mcard col2 plan">
                <div>
                  <div className="label">TODAY'S STUDY PLAN</div>
                  <div className="count" style={{ fontSize: 22, marginTop: 8 }}>
                    On track <span style={{ color: "#5DA877" }}>✓</span>
                  </div>
                  <div className="sub">3 of 4 sessions complete</div>
                </div>
                <div className="ticks">
                  <span className="tick done"></span>
                  <span className="tick done"></span>
                  <span className="tick done"></span>
                  <span className="tick"></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

// ---- How it helps ----
function HowItHelps() {
  const [ref, seen] = useReveal();
  const items = [
    { icon: <IconScan />, title: "Check eligibility", text: "Tell us your education, age, category, and state. We show exams you may apply for." },
    { icon: <IconCalendarFlip />, title: "Track deadlines", text: "Application dates, admit cards, results, documents, and reminders — all in one place." },
    { icon: <IconClockSweep />, title: "Study daily", text: "A clear daily plan based on your exam, available time, weak areas, and exam date." },
    { icon: <IconChat />, title: "Get support", text: "Ask doubts, join study groups, find a partner, use free resources, talk to a mentor." },
  ];
  return (
    <section className="section" id="how" ref={ref}>
      <div className="container">
        <div className={"reveal " + (seen ? "in" : "")}>
          <span className="kicker">How it helps</span>
          <h2 className="h">Four simple things you can do today.</h2>
          <p className="h-sub">No big lectures. No course bundles. Just the help you actually need to move forward.</p>
        </div>
        <div className="how-grid">
          {items.map((it, i) => (
            <div key={i} className={"how-card reveal " + (seen ? "in" : "")} style={{ transitionDelay: (i * 80 + 100) + "ms" }}>
              <div className="icon-wrap">{it.icon}</div>
              <h3>{it.title}</h3>
              <p>{it.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ---- Eligibility demo ----
function EligibilityDemo() {
  const [ref, seen] = useReveal();
  const cards = [
    { cls: "green", verdict: "You can apply", name: "SSC CGL", reason: "Your education, age, and category match this exam's requirements.", kind: "green" },
    { cls: "amber", verdict: "More information needed", name: "RBI Grade B", reason: "Please add your work experience and degree subject to confirm.", kind: "amber" },
    { cls: "red",   verdict: "You may not qualify", name: "State PSC", reason: "This exam requires domicile of a specific state. You can switch to another state's PSC.", kind: "red" },
  ];
  return (
    <section className="section" ref={ref} style={{ background: "linear-gradient(180deg, var(--cream) 0%, var(--cream-2) 100%)" }}>
      <div className="container">
        <div className={"reveal " + (seen ? "in" : "")}>
          <span className="kicker">See where you stand</span>
          <h2 className="h">Know where you stand before filling forms.</h2>
          <p className="h-sub">Answer a few short questions and we tell you, plainly, which exams are open to you and why.</p>
        </div>
        <div className="elig-cards">
          {cards.map((c, i) => (
            <div key={i} className={"elig-card " + c.cls + (seen ? " in" : "")}>
              <VerdictIcon kind={c.kind} />
              <div className="badge">
                {c.cls === "green" && <span>✓</span>}
                {c.cls === "amber" && <span>◐</span>}
                {c.cls === "red"   && <span>✕</span>}
                {c.verdict}
              </div>
              <div className="name">{c.name}</div>
              <div className="reason">{c.reason}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ---- Daily plan timeline ----
function DailyPlan() {
  const [ref, seen] = useReveal();
  const slots = [
    { time: "7:00 AM",  title: "Revise Polity",         tag: "30 min · book chapter 4",    art: <MiniBook />,   state: "done" },
    { time: "10:00 AM", title: "Practice Quant",        tag: "20 questions · time-trial",   art: <MiniPencil />, state: "done" },
    { time: "6:00 PM",  title: "Review mock mistakes",  tag: "Last weekend's mock",         art: <MiniPaper />,  state: "now" },
    { time: "9:00 PM",  title: "Quick revision",        tag: "Today's notes · 15 min",      art: <MiniBulb />,   state: "" },
  ];
  return (
    <section className="section" ref={ref}>
      <div className="container">
        <div className={"reveal " + (seen ? "in" : "")}>
          <span className="kicker">Today's plan</span>
          <h2 className="h">A clear plan for today.</h2>
          <p className="h-sub">Short blocks, one thing at a time. You always know what's next.</p>
        </div>
        <div className={"tl-wrap " + (seen ? "in" : "")} style={{ maxWidth: 640 }}>
          <div className="tl-line"></div>
          {slots.map((s, i) => (
            <div key={i} className={"tl-row " + s.state}>
              <div className="time">{s.time}</div>
              <div className="tl-dot"></div>
              <div className="tl-card">
                <div className="mini-ill">{s.art}</div>
                <div>
                  <div className="ttitle">{s.title}</div>
                  <div className="ttag">{s.tag}</div>
                </div>
                <div className="check-mark">{s.state === "done" ? "✓" : ""}</div>
              </div>
            </div>
          ))}
          <div className="tl-note">
            <svg width="20" height="20" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#E0A640" /><path d="M12 7 v6 M12 16 v1" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" /></svg>
            <span>Plans change when your exam date, progress, or available time changes.</span>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---- Support grid ----
function Support() {
  const [ref, seen] = useReveal();
  const items = [
    { scene: <SceneCommunity />,  title: "Community",            text: "Ask doubts and discuss exam preparation." },
    { scene: <SceneGroup />,      title: "Study Groups",         text: "Join small groups preparing for similar exams." },
    { scene: <ScenePartner />,    title: "Accountability Partner", text: "Pair with another aspirant and check in regularly." },
    { scene: <SceneMentor />,     title: "Mentors",              text: "Get guidance from experienced mentors." },
    { scene: <SceneResources />,  title: "Free Resources",       text: "Use notes, links, official PDFs, and study material." },
    { scene: <SceneShop />,       title: "Marketplace",          text: "Buy extra courses or notes only when you need them." },
  ];
  return (
    <section className="section" ref={ref} style={{ background: "var(--cream-2)" }}>
      <div className="container">
        <div className={"reveal " + (seen ? "in" : "")}>
          <span className="kicker">You are not alone</span>
          <h2 className="h">Prepare with people, not alone.</h2>
          <p className="h-sub">Friends to share doubts with, a partner to keep you accountable, and mentors when you need guidance.</p>
        </div>
        <div className="support-grid">
          {items.map((it, i) => (
            <div key={i} className={"s-card reveal " + (seen ? "in" : "")} style={{ transitionDelay: (i * 60 + 80) + "ms" }}>
              <div className="scene-wrap">{it.scene}</div>
              <div>
                <h3>{it.title}</h3>
                <p>{it.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ---- Trust ----
function Trust() {
  const [ref, seen] = useReveal();
  return (
    <section className="section" ref={ref}>
      <div className="container">
        <div className={"reveal " + (seen ? "in" : "")}>
          <span className="kicker">What you can trust</span>
          <h2 className="h">We separate official updates from rumours.</h2>
          <p className="h-sub">Official notices change your deadlines and plan. Anything we cannot confirm is shown separately and clearly.</p>
        </div>
        <div className="trust-wrap">
          <div className={"trust-illus reveal " + (seen ? "in" : "")}><TrustFilterScene /></div>
          <div className="trust-cards">
            <div className={"tcard official reveal " + (seen ? "in" : "")}>
              <ShieldCheck />
              <div className="glab">Green badge</div>
              <h3>Official update</h3>
              <p style={{ margin: 0, color: "var(--ink-2)" }}>Can update your deadlines and plan.</p>
            </div>
            <div className={"tcard unconf reveal " + (seen ? "in" : "")} style={{ transitionDelay: "120ms" }}>
              <ShieldQuestion />
              <div className="glab">Amber badge</div>
              <h3>Unconfirmed update</h3>
              <p style={{ margin: 0, color: "var(--ink-2)" }}>Shown separately until confirmed.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---- Exams covered ----
function Exams() {
  const [ref, seen] = useReveal();
  const pills = [
    { n: "UPSC",      tag: "solid",    count: "12 upcoming dates" },
    { n: "SSC",       tag: "solid",    count: "9 upcoming dates" },
    { n: "Banking",   tag: "solid",    count: "14 upcoming dates" },
    { n: "Railways",  tag: "solid",    count: "6 upcoming dates" },
    { n: "Defence",   tag: "solid",    count: "5 upcoming dates" },
    { n: "State PSC", tag: "outlined", count: "Limited support" },
    { n: "PSU",       tag: "outlined", count: "Limited support" },
  ];
  return (
    <section className="section" id="exams" ref={ref} style={{ background: "var(--cream-2)" }}>
      <div className="container">
        <div className={"reveal " + (seen ? "in" : "")}>
          <span className="kicker">Exams we cover</span>
          <h2 className="h">Prepare for exams like:</h2>
        </div>
        <div className="exam-pills">
          {pills.map((p, i) => (
            <span key={i} className={"epill " + p.tag + (seen ? " in" : "")} style={{ animationDelay: (i * 50 + 100) + "ms" }}>
              {p.tag === "outlined" && <span className="dot" />}
              {p.n}
              <span className="tip">{p.count}</span>
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

// ---- Pricing ----
function Pricing() {
  const [ref, seen] = useReveal();
  const auth = useAuth();
  const navigate = useNavigate();
  const plans = [
    { tier: "Starter", name: "Free", price: "₹0", per: "forever",
      bullets: ["Eligibility check", "Deadline tracker", "Community access", "Free resources library"],
      cta: "Start free", to: auth.isAuthed ? "/app" : "/signup" },
    { tier: "Most chosen", name: "Study Plan", price: "₹299", per: "per month",
      bullets: ["Everything in Free", "Daily study plan", "Revision schedule", "Mock test review", "Weekly report card"],
      cta: "Start 7-day trial", featured: true, to: guestSafe("/app/study/plan", auth.isAuthed) },
    { tier: "Premium", name: "Mentor", price: "₹999", per: "per month",
      bullets: ["Everything in Study Plan", "Plan review by a mentor", "1:1 mentor sessions", "Personal feedback"],
      cta: "Talk to us", to: guestSafe("/app/mentors", auth.isAuthed) },
  ];
  return (
    <section className="section" id="pricing" ref={ref}>
      <div className="container">
        <div className={"reveal " + (seen ? "in" : "")}>
          <span className="kicker">Pricing</span>
          <h2 className="h">Start free. Upgrade only when you need more.</h2>
          <p className="h-sub">Daily planning, mock correction, or mentor support — only when you actually need them.</p>
        </div>
        <div className="price-grid">
          {plans.map((p, i) => (
            <div key={i} className={"pcard " + (p.featured ? "featured " : "") + "reveal " + (seen ? "in" : "")}
                 style={{ transitionDelay: (i * 100 + 100) + "ms" }}>
              {p.featured && <div className="ribbon">Most chosen</div>}
              <div className="ptier">{p.tier}</div>
              <div className="pname">{p.name}</div>
              <div className="ppr"><span className="amt">{p.price}</span><span className="per">{p.per}</span></div>
              <ul>{p.bullets.map((b, k) => <li key={k}>{b}</li>)}</ul>
              <div className="pcta">
                <button className={"btn " + (p.featured ? "btn-primary" : "btn-secondary")} style={{ width: "100%" }}
                  onMouseDown={rippleHandler} onClick={() => navigate(p.to)}>{p.cta}</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ---- FAQ ----
function FAQ() {
  const [ref, seen] = useReveal();
  const items = [
    { q: "I just graduated. Where should I start?",
      a: "Tell us your degree, age, and state. We will show the exams you can apply for right now, with their next dates. From there, you can start a study plan in one tap." },
    { q: "Can I find exams based on my qualification?",
      a: "Yes. We match exams to your education, age, category, and state. You will see what fits — and what you can prepare for later." },
    { q: "Will this remind me about forms and dates?",
      a: "Yes. We track application start, application close, admit card, exam day, and result. You get a reminder before each one." },
    { q: "Can I use it for SSC, Banking, UPSC, or State PSC?",
      a: "Yes for SSC, Banking, UPSC, Railways, and Defence — fully supported. State PSC has limited support today and is expanding." },
    { q: "Is it free?",
      a: "Eligibility checks, deadline tracking, community, and free resources are free forever. Daily study plans and mentor support are paid." },
    { q: "Do I need a mentor?",
      a: "No. Most aspirants do well with the daily plan and community. A mentor helps if you are stuck, switching exams, or in your final 60 days." },
  ];
  return (
    <section className="section" id="faq" ref={ref}>
      <div className="container">
        <div className={"reveal " + (seen ? "in" : "")}>
          <span className="kicker">Common questions</span>
          <h2 className="h">Questions aspirants ask us.</h2>
        </div>
        <div className={"faq reveal " + (seen ? "in" : "")}>
          {items.map((it, i) => (
            <details key={i} className="fitem">
              <summary><span className="plus"></span>{it.q}</summary>
              <div className="fans">{it.a}</div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

// ---- Footer ----
function Footer() {
  return (
    <footer>
      <div className="container foot-row">
        <div className="nav-logo">
          <LogoMark size={26} />
          <span style={{ fontWeight: 700 }}>Career Copilot</span>
        </div>
        <div className="nav-spacer" />
        <div className="foot-links">
          <button type="button">About</button>
          <button type="button">Privacy</button>
          <button type="button">Terms</button>
          <button type="button">Contact</button>
        </div>
        <div style={{ width: "100%", textAlign: "center", paddingTop: 14, color: "var(--ink-4)", fontSize: 13 }}>
          © 2026 Career Copilot. Made for aspirants in India.
        </div>
      </div>
    </footer>
  );
}

// ---- Page ----
export default function Landing() {
  return (
    <div className="cc-landing">
      <Nav />
      <Hero />
      <HowItHelps />
      <EligibilityDemo />
      <DailyPlan />
      <Support />
      <Trust />
      <Exams />
      <Pricing />
      <FAQ />
      <Footer />
    </div>
  );
}

// Career Copilot — flat-vector illustrations
// Friendly, simple geometry. Round heads, soft shapes. No detailed faces.
// All <svg> elements get a viewBox + currentColor where possible.

// Logo mark
const LogoMark = ({ size = 30 }) => (
  <svg className="logo-mark" viewBox="0 0 40 40" width={size} height={size}>
    <circle cx="20" cy="20" r="18" fill="#2F7E7E" />
    <path d="M14 26 L14 14 L26 14 L26 22 L20 22 L17 26 Z" fill="#FBF4E6" />
    <circle cx="18" cy="18" r="1.4" fill="#2F7E7E" />
    <circle cx="22" cy="18" r="1.4" fill="#2F7E7E" />
  </svg>
);

// ===== Hero base illustration — girl at desk with laptop + boy with books =====
const HeroScene = () => (
  <svg viewBox="0 0 480 380" width="100%" style={{ maxWidth: 520 }}>
    {/* warm sun blob */}
    <circle cx="380" cy="80" r="46" fill="#FBE7C0" />
    {/* desk */}
    <rect x="40" y="290" width="400" height="10" rx="4" fill="#D2A87A" />
    <rect x="60" y="300" width="14" height="60" fill="#B58859" />
    <rect x="406" y="300" width="14" height="60" fill="#B58859" />

    {/* girl at desk */}
    <g transform="translate(110 130)">
      {/* chair back */}
      <rect x="-26" y="44" width="120" height="100" rx="14" fill="#2F7E7E" />
      {/* body */}
      <rect x="-8" y="60" width="84" height="100" rx="22" fill="#B3577A" />
      {/* arms toward laptop */}
      <rect x="56" y="120" width="40" height="14" rx="7" fill="#B3577A" />
      <rect x="-4" y="120" width="40" height="14" rx="7" fill="#B3577A" />
      {/* head */}
      <circle cx="34" cy="38" r="30" fill="#E8C39A" />
      {/* hair bun */}
      <path d="M4 30 Q4 4 34 4 Q64 4 64 30 Q64 22 50 18 Q46 12 34 12 Q22 12 18 18 Q4 22 4 30 Z" fill="#3A2A1F" />
      <circle cx="60" cy="14" r="8" fill="#3A2A1F" />
      {/* eyes */}
      <circle cx="24" cy="40" r="2.2" fill="#1F1A14" />
      <circle cx="44" cy="40" r="2.2" fill="#1F1A14" />
      {/* smile */}
      <path d="M28 48 Q34 54 40 48" stroke="#1F1A14" strokeWidth="2" fill="none" strokeLinecap="round" />
      {/* cheek */}
      <circle cx="18" cy="46" r="3" fill="#E47A5A" opacity="0.45" />
      <circle cx="50" cy="46" r="3" fill="#E47A5A" opacity="0.45" />
    </g>

    {/* laptop */}
    <g transform="translate(190 215)">
      <rect x="0" y="40" width="130" height="10" rx="3" fill="#7A6E5C" />
      <rect x="6" y="-2" width="118" height="44" rx="4" fill="#1F1A14" />
      <rect x="10" y="2" width="110" height="36" rx="2" fill="#5DA877" />
      {/* mini chart on screen */}
      <rect x="16" y="24" width="6" height="12" fill="#FBF4E6" />
      <rect x="26" y="18" width="6" height="18" fill="#FBF4E6" />
      <rect x="36" y="14" width="6" height="22" fill="#FBF4E6" />
      <rect x="46" y="20" width="6" height="16" fill="#FBF4E6" />
      <circle cx="100" cy="18" r="5" fill="#FBF4E6" />
      <path d="M97 18 L99 20 L103 16" stroke="#5DA877" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </g>

    {/* books stack on desk left */}
    <g transform="translate(54 250)">
      <rect x="0" y="20" width="60" height="14" rx="2" fill="#E47A5A" />
      <rect x="4" y="8"  width="56" height="14" rx="2" fill="#6E9DD0" />
      <rect x="2" y="-2" width="58" height="12" rx="2" fill="#E0A640" />
    </g>

    {/* coffee mug */}
    <g transform="translate(370 250)">
      <rect x="0" y="0" width="24" height="30" rx="3" fill="#FFFFFF" />
      <rect x="3" y="3" width="18" height="6" rx="1" fill="#2F7E7E" />
      <path d="M24 8 Q34 8 34 18 Q34 28 24 28" stroke="#FFFFFF" strokeWidth="3" fill="none" />
      {/* steam */}
      <path d="M8 -10 Q4 -16 8 -22" stroke="#A89C87" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.6">
        <animate attributeName="opacity" values="0.2;0.7;0.2" dur="3s" repeatCount="indefinite" />
      </path>
      <path d="M16 -8 Q20 -14 16 -20" stroke="#A89C87" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.6">
        <animate attributeName="opacity" values="0.6;0.2;0.6" dur="3s" repeatCount="indefinite" />
      </path>
    </g>

    {/* small boy with books, walking up to her */}
    <g transform="translate(330 170)">
      {/* body */}
      <rect x="6" y="60" width="48" height="60" rx="14" fill="#6E9DD0" />
      <rect x="14" y="120" width="14" height="36" rx="6" fill="#2F4858" />
      <rect x="32" y="120" width="14" height="36" rx="6" fill="#2F4858" />
      {/* arms holding books */}
      <rect x="0" y="80" width="60" height="14" rx="7" fill="#6E9DD0" />
      {/* book stack in arms */}
      <rect x="6" y="64" width="48" height="10" rx="2" fill="#E0A640" />
      <rect x="10" y="56" width="40" height="10" rx="2" fill="#5DA877" />
      {/* head */}
      <circle cx="30" cy="36" r="22" fill="#C49075" />
      {/* hair */}
      <path d="M10 32 Q10 14 30 14 Q50 14 50 32 Q50 22 30 22 Q14 22 10 32 Z" fill="#1F1A14" />
      {/* eyes */}
      <circle cx="22" cy="40" r="1.8" fill="#1F1A14" />
      <circle cx="38" cy="40" r="1.8" fill="#1F1A14" />
      {/* smile */}
      <path d="M24 46 Q30 50 36 46" stroke="#1F1A14" strokeWidth="1.6" fill="none" strokeLinecap="round" />
    </g>

    {/* tiny leaves */}
    <circle cx="36" cy="120" r="6" fill="#5DA877" />
    <circle cx="46" cy="116" r="4" fill="#5DA877" />
    <circle cx="40" cy="128" r="5" fill="#5DA877" />
  </svg>
);

// ===== Floating hero icons =====
const FloatCalendar = () => (
  <svg viewBox="0 0 60 60" width="56" height="56">
    <rect x="6" y="10" width="48" height="42" rx="6" fill="#FFFFFF" stroke="#1F1A14" strokeWidth="2" />
    <rect x="6" y="10" width="48" height="12" rx="6" fill="#E47A5A" />
    <rect x="14" y="4"  width="4" height="10" rx="2" fill="#1F1A14" />
    <rect x="42" y="4"  width="4" height="10" rx="2" fill="#1F1A14" />
    <rect x="14" y="28" width="6" height="6" rx="1" fill="#1F1A14" />
    <rect x="24" y="28" width="6" height="6" rx="1" fill="#5DA877" />
    <rect x="34" y="28" width="6" height="6" rx="1" fill="#1F1A14" />
    <rect x="44" y="28" width="4" height="6" rx="1" fill="#1F1A14" />
    <rect x="14" y="40" width="6" height="6" rx="1" fill="#1F1A14" />
    <rect x="24" y="40" width="6" height="6" rx="1" fill="#1F1A14" />
  </svg>
);

const FloatBook = () => (
  <svg viewBox="0 0 60 60" width="56" height="56">
    <path d="M8 14 Q20 8 30 12 Q40 8 52 14 L52 50 Q40 44 30 48 Q20 44 8 50 Z" fill="#6E9DD0" stroke="#1F1A14" strokeWidth="2" strokeLinejoin="round" />
    <path d="M30 12 L30 48" stroke="#1F1A14" strokeWidth="2" />
    <path d="M14 22 L24 20" stroke="#FFFFFF" strokeWidth="1.6" strokeLinecap="round" />
    <path d="M14 28 L24 26" stroke="#FFFFFF" strokeWidth="1.6" strokeLinecap="round" />
    <path d="M36 20 L46 22" stroke="#FFFFFF" strokeWidth="1.6" strokeLinecap="round" />
    <path d="M36 26 L46 28" stroke="#FFFFFF" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
);

const FloatClock = () => (
  <svg viewBox="0 0 60 60" width="56" height="56">
    <circle cx="30" cy="32" r="22" fill="#FFFFFF" stroke="#1F1A14" strokeWidth="2" />
    <rect x="26" y="6" width="8" height="6" rx="2" fill="#1F1A14" />
    <line x1="30" y1="32" x2="30" y2="18" stroke="#1F1A14" strokeWidth="2.4" strokeLinecap="round">
      <animateTransform attributeName="transform" type="rotate" from="0 30 32" to="360 30 32" dur="12s" repeatCount="indefinite" />
    </line>
    <line x1="30" y1="32" x2="40" y2="32" stroke="#E47A5A" strokeWidth="2.4" strokeLinecap="round">
      <animateTransform attributeName="transform" type="rotate" from="0 30 32" to="360 30 32" dur="60s" repeatCount="indefinite" />
    </line>
    <circle cx="30" cy="32" r="2.2" fill="#1F1A14" />
  </svg>
);

// ===== How-it-helps icons (animate on hover via CSS class hooks) =====
const IconScan = () => (
  <svg viewBox="0 0 64 64" width="44" height="44" className="i-scan">
    {/* profile card */}
    <rect x="8" y="14" width="40" height="40" rx="6" fill="#FFFFFF" stroke="#1F1A14" strokeWidth="2" />
    <circle cx="20" cy="26" r="5" fill="#2F7E7E" />
    <rect x="29" y="22" width="14" height="3" rx="1" fill="#1F1A14" />
    <rect x="29" y="28" width="10" height="3" rx="1" fill="#A89C87" />
    <rect x="13" y="38" width="30" height="3" rx="1" fill="#E0A640" />
    <rect x="13" y="44" width="22" height="3" rx="1" fill="#A89C87" />
    {/* magnifier */}
    <g className="scan-glass">
      <circle cx="42" cy="44" r="11" fill="rgba(228,122,90,0.18)" stroke="#1F1A14" strokeWidth="2" />
      <line x1="50" y1="52" x2="58" y2="60" stroke="#1F1A14" strokeWidth="3" strokeLinecap="round" />
    </g>
    <style>{`
      .i-scan .scan-glass { transform-origin: 42px 44px; }
      .how-card:hover .i-scan .scan-glass { animation: scanMove 1.6s ease-in-out infinite; }
      @keyframes scanMove {
        0%   { transform: translate(0,0); }
        25%  { transform: translate(-22px,-22px); }
        50%  { transform: translate(0,-22px); }
        75%  { transform: translate(-22px,0); }
        100% { transform: translate(0,0); }
      }
    `}</style>
  </svg>
);

const IconCalendarFlip = () => (
  <svg viewBox="0 0 64 64" width="44" height="44" className="i-cal">
    <rect x="8" y="14" width="48" height="42" rx="6" fill="#FFFFFF" stroke="#1F1A14" strokeWidth="2" />
    <rect x="8" y="14" width="48" height="12" rx="6" fill="#E47A5A" />
    <rect x="16" y="8" width="4" height="10" rx="2" fill="#1F1A14" />
    <rect x="44" y="8" width="4" height="10" rx="2" fill="#1F1A14" />
    <g className="cal-page">
      <rect x="12" y="30" width="40" height="22" rx="3" fill="#FBF4E6" stroke="#1F1A14" strokeWidth="1.5" />
      <text x="32" y="48" fontSize="14" fontWeight="700" textAnchor="middle" fill="#1F1A14" fontFamily="Inter, sans-serif">14</text>
    </g>
    <style>{`
      .i-cal .cal-page { transform-origin: 32px 30px; }
      .how-card:hover .i-cal .cal-page { animation: pageFlip 1.6s ease-in-out infinite; }
      @keyframes pageFlip {
        0%, 100% { transform: rotateX(0); }
        50%      { transform: rotateX(70deg); }
      }
    `}</style>
  </svg>
);

const IconClockSweep = () => (
  <svg viewBox="0 0 64 64" width="44" height="44" className="i-clock">
    <circle cx="32" cy="34" r="22" fill="#FFFFFF" stroke="#1F1A14" strokeWidth="2" />
    <rect x="28" y="8" width="8" height="6" rx="2" fill="#1F1A14" />
    <line x1="32" y1="34" x2="32" y2="22" stroke="#1F1A14" strokeWidth="2.6" strokeLinecap="round" className="hourhand" />
    <line x1="32" y1="34" x2="44" y2="34" stroke="#E47A5A" strokeWidth="2.6" strokeLinecap="round" className="minhand" />
    <circle cx="32" cy="34" r="2.2" fill="#1F1A14" />
    <style>{`
      .i-clock .minhand { transform-origin: 32px 34px; }
      .how-card:hover .i-clock .minhand { animation: sweep 2s linear infinite; }
      @keyframes sweep { from { transform: rotate(0); } to { transform: rotate(360deg); } }
    `}</style>
  </svg>
);

const IconChat = () => (
  <svg viewBox="0 0 64 64" width="44" height="44" className="i-chat">
    <path d="M10 18 Q10 10 18 10 L46 10 Q54 10 54 18 L54 34 Q54 42 46 42 L26 42 L16 50 L18 42 Q10 42 10 34 Z"
          fill="#FFFFFF" stroke="#1F1A14" strokeWidth="2" strokeLinejoin="round" />
    <circle cx="22" cy="26" r="3" fill="#5DA877" className="dot d1" />
    <circle cx="32" cy="26" r="3" fill="#5DA877" className="dot d2" />
    <circle cx="42" cy="26" r="3" fill="#5DA877" className="dot d3" />
    <style>{`
      .how-card:hover .i-chat .dot { animation: chatDot 1.2s ease-in-out infinite; }
      .how-card:hover .i-chat .d2 { animation-delay: 0.15s; }
      .how-card:hover .i-chat .d3 { animation-delay: 0.3s; }
      @keyframes chatDot { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-3px); } }
    `}</style>
  </svg>
);

// ===== Eligibility ID-card icons =====
const VerdictIcon = ({ kind }) => {
  if (kind === "green") return (
    <svg viewBox="0 0 64 64" width="56" height="56">
      <rect x="6" y="10" width="52" height="44" rx="8" fill="#D5EBDB" stroke="#1F1A14" strokeWidth="2" />
      <circle cx="20" cy="26" r="6" fill="#5DA877" />
      <rect x="32" y="22" width="20" height="3" rx="1" fill="#1F1A14" />
      <rect x="32" y="29" width="14" height="3" rx="1" fill="#7A6E5C" />
      <circle cx="42" cy="44" r="9" fill="#5DA877" />
      <path d="M37.5 44 L41 47.5 L47 41" stroke="#FFFFFF" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"
        strokeDasharray="14" strokeDashoffset="14">
        <animate attributeName="stroke-dashoffset" to="0" dur="600ms" begin="200ms" fill="freeze" />
      </path>
    </svg>
  );
  if (kind === "amber") return (
    <svg viewBox="0 0 64 64" width="56" height="56">
      <rect x="6" y="10" width="52" height="44" rx="8" fill="#FBE7C0" stroke="#1F1A14" strokeWidth="2" />
      <circle cx="20" cy="26" r="6" fill="#E0A640" />
      <rect x="32" y="22" width="20" height="3" rx="1" fill="#1F1A14" />
      <rect x="32" y="29" width="14" height="3" rx="1" fill="#7A6E5C" />
      <circle cx="42" cy="44" r="9" fill="#E0A640" />
      <text x="42" y="48" fontSize="13" fontWeight="800" textAnchor="middle" fill="#FFFFFF" fontFamily="Inter, sans-serif">?</text>
    </svg>
  );
  return (
    <svg viewBox="0 0 64 64" width="56" height="56">
      <rect x="6" y="10" width="52" height="44" rx="8" fill="#F6D5D5" stroke="#1F1A14" strokeWidth="2" />
      <circle cx="20" cy="26" r="6" fill="#C95C5C" />
      <rect x="32" y="22" width="20" height="3" rx="1" fill="#1F1A14" />
      <rect x="32" y="29" width="14" height="3" rx="1" fill="#7A6E5C" />
      <circle cx="42" cy="44" r="9" fill="#C95C5C" />
      <path d="M38 40 L46 48 M46 40 L38 48" stroke="#FFFFFF" strokeWidth="3" strokeLinecap="round"
        strokeDasharray="14" strokeDashoffset="14">
        <animate attributeName="stroke-dashoffset" to="0" dur="600ms" begin="200ms" fill="freeze" />
      </path>
    </svg>
  );
};

// ===== Timeline mini icons =====
const MiniBook = () => (
  <svg viewBox="0 0 40 40" width="36" height="36">
    <rect x="6" y="8" width="14" height="24" rx="2" fill="#6E9DD0" stroke="#1F1A14" strokeWidth="1.5" />
    <rect x="20" y="8" width="14" height="24" rx="2" fill="#E47A5A" stroke="#1F1A14" strokeWidth="1.5" />
    <line x1="20" y1="10" x2="20" y2="30" stroke="#1F1A14" strokeWidth="1.5" />
    <line x1="9" y1="14" x2="17" y2="14" stroke="#FFFFFF" strokeWidth="1.3" strokeLinecap="round" />
    <line x1="9" y1="18" x2="17" y2="18" stroke="#FFFFFF" strokeWidth="1.3" strokeLinecap="round" />
    <line x1="23" y1="14" x2="31" y2="14" stroke="#FFFFFF" strokeWidth="1.3" strokeLinecap="round" />
    <line x1="23" y1="18" x2="31" y2="18" stroke="#FFFFFF" strokeWidth="1.3" strokeLinecap="round" />
  </svg>
);
const MiniPencil = () => (
  <svg viewBox="0 0 40 40" width="36" height="36">
    <rect x="6" y="22" width="22" height="6" transform="rotate(-30 6 22)" fill="#E0A640" stroke="#1F1A14" strokeWidth="1.5" />
    <polygon points="3,28 11,29 6,33" fill="#1F1A14" />
    <rect x="22" y="14" width="6" height="6" transform="rotate(-30 22 14)" fill="#E47A5A" stroke="#1F1A14" strokeWidth="1.5" />
  </svg>
);
const MiniPaper = () => (
  <svg viewBox="0 0 40 40" width="36" height="36">
    <rect x="8" y="6" width="22" height="28" rx="2" fill="#FFFFFF" stroke="#1F1A14" strokeWidth="1.5" />
    <line x1="12" y1="14" x2="26" y2="14" stroke="#A89C87" strokeWidth="1.5" strokeLinecap="round" />
    <line x1="12" y1="20" x2="26" y2="20" stroke="#C95C5C" strokeWidth="1.5" strokeLinecap="round" />
    <line x1="12" y1="26" x2="22" y2="26" stroke="#A89C87" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);
const MiniBulb = () => (
  <svg viewBox="0 0 40 40" width="36" height="36">
    <path d="M20 6 Q10 6 10 16 Q10 22 14 26 L14 30 L26 30 L26 26 Q30 22 30 16 Q30 6 20 6 Z" fill="#E0A640" stroke="#1F1A14" strokeWidth="1.5" />
    <rect x="14" y="30" width="12" height="4" rx="1" fill="#7A6E5C" />
    <line x1="20" y1="2" x2="20" y2="5" stroke="#1F1A14" strokeWidth="1.5" strokeLinecap="round" />
    <line x1="32" y1="14" x2="35" y2="14" stroke="#1F1A14" strokeWidth="1.5" strokeLinecap="round" />
    <line x1="5"  y1="14" x2="8"  y2="14" stroke="#1F1A14" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

// ===== Support card scenes — 6 friendly mini-illustrations =====
const SceneCommunity = () => (
  <svg viewBox="0 0 64 64" width="52" height="52" className="scene">
    <path d="M8 14 Q8 8 14 8 L36 8 Q42 8 42 14 L42 24 Q42 30 36 30 L20 30 L14 36 L15 30 Q8 30 8 24 Z"
          fill="#FFFFFF" stroke="#1F1A14" strokeWidth="2" />
    <path d="M22 24 Q22 18 28 18 L48 18 Q54 18 54 24 L54 34 Q54 40 48 40 L34 40 L40 46 L38 40 Q22 40 22 34 Z"
          fill="#6E9DD0" stroke="#1F1A14" strokeWidth="2" />
    <circle cx="18" cy="19" r="1.6" fill="#1F1A14" />
    <circle cx="24" cy="19" r="1.6" fill="#1F1A14" />
    <circle cx="30" cy="19" r="1.6" fill="#1F1A14" />
  </svg>
);

const SceneGroup = () => (
  <svg viewBox="0 0 64 64" width="52" height="52" className="scene">
    <ellipse cx="32" cy="48" rx="22" ry="4" fill="#E0A640" opacity="0.6" />
    <rect x="14" y="40" width="36" height="6" rx="2" fill="#E0A640" />
    {/* left figure */}
    <circle cx="16" cy="26" r="6" fill="#C49075" />
    <rect x="10" y="32" width="12" height="10" rx="3" fill="#B3577A" />
    {/* center figure */}
    <circle cx="32" cy="22" r="7" fill="#E8C39A" />
    <rect x="25" y="28" width="14" height="13" rx="3" fill="#2F7E7E" />
    {/* right figure */}
    <circle cx="48" cy="26" r="6" fill="#C49075" />
    <rect x="42" y="32" width="12" height="10" rx="3" fill="#6E9DD0" />
    {/* book on table */}
    <rect x="26" y="44" width="12" height="3" fill="#FBF4E6" stroke="#1F1A14" strokeWidth="1" />
  </svg>
);

const ScenePartner = () => (
  <svg viewBox="0 0 64 64" width="52" height="52" className="scene">
    {/* left fig */}
    <circle cx="18" cy="22" r="7" fill="#E8C39A" />
    <rect x="11" y="28" width="14" height="20" rx="4" fill="#E47A5A" />
    {/* right fig */}
    <circle cx="46" cy="22" r="7" fill="#C49075" />
    <rect x="39" y="28" width="14" height="20" rx="4" fill="#2F7E7E" />
    {/* arms raised toward each other */}
    <rect x="24" y="22" width="10" height="4" rx="2" fill="#E8C39A" transform="rotate(-20 24 22)" />
    <rect x="30" y="22" width="10" height="4" rx="2" fill="#C49075" transform="rotate(20 40 22)" />
    {/* spark */}
    <circle cx="32" cy="18" r="2.2" fill="#E0A640" />
    <line x1="32" y1="10" x2="32" y2="13" stroke="#E0A640" strokeWidth="2" strokeLinecap="round" />
    <line x1="26" y1="14" x2="28" y2="16" stroke="#E0A640" strokeWidth="2" strokeLinecap="round" />
    <line x1="38" y1="14" x2="36" y2="16" stroke="#E0A640" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

const SceneMentor = () => (
  <svg viewBox="0 0 64 64" width="52" height="52" className="scene">
    {/* board */}
    <rect x="32" y="6" width="28" height="22" rx="2" fill="#2F4858" stroke="#1F1A14" strokeWidth="1.5" />
    <line x1="36" y1="14" x2="56" y2="14" stroke="#FBF4E6" strokeWidth="1.5" strokeLinecap="round" />
    <line x1="36" y1="20" x2="50" y2="20" stroke="#FBF4E6" strokeWidth="1.5" strokeLinecap="round" />
    {/* figure */}
    <circle cx="18" cy="22" r="8" fill="#C49075" />
    {/* grad cap */}
    <rect x="10" y="14" width="16" height="3" fill="#1F1A14" />
    <polygon points="18,8 28,14 18,17 8,14" fill="#1F1A14" />
    <path d="M26 12 L30 16" stroke="#E47A5A" strokeWidth="1.6" />
    <circle cx="30" cy="16" r="1.6" fill="#E47A5A" />
    {/* body */}
    <rect x="10" y="30" width="16" height="22" rx="4" fill="#B3577A" />
    {/* arm pointing */}
    <rect x="22" y="30" width="20" height="4" rx="2" fill="#C49075" />
  </svg>
);

const SceneResources = () => (
  <svg viewBox="0 0 64 64" width="52" height="52" className="scene">
    <rect x="8"  y="34" width="48" height="10" rx="2" fill="#E47A5A" stroke="#1F1A14" strokeWidth="1.5" />
    <rect x="12" y="22" width="40" height="10" rx="2" fill="#6E9DD0" stroke="#1F1A14" strokeWidth="1.5" />
    <rect x="16" y="10" width="32" height="10" rx="2" fill="#E0A640" stroke="#1F1A14" strokeWidth="1.5" />
    <line x1="20" y1="15" x2="42" y2="15" stroke="#1F1A14" strokeWidth="1" />
    <line x1="16" y1="27" x2="46" y2="27" stroke="#1F1A14" strokeWidth="1" />
    <line x1="12" y1="39" x2="50" y2="39" stroke="#1F1A14" strokeWidth="1" />
    <rect x="20" y="46" width="24" height="8" rx="2" fill="#FFFFFF" stroke="#1F1A14" strokeWidth="1.5" />
    <text x="32" y="52" fontSize="6" textAnchor="middle" fontWeight="700" fill="#1F1A14" fontFamily="Inter, sans-serif">FREE</text>
  </svg>
);

const SceneShop = () => (
  <svg viewBox="0 0 64 64" width="52" height="52" className="scene">
    <path d="M30 8 L52 8 L56 14 L34 36 Q31 39 28 36 L8 16 Q5 13 8 10 Z" fill="#B3577A" stroke="#1F1A14" strokeWidth="2" strokeLinejoin="round" />
    <circle cx="44" cy="18" r="3" fill="#FBF4E6" stroke="#1F1A14" strokeWidth="1.5" />
    <rect x="28" y="46" width="14" height="10" rx="2" fill="#FFFFFF" stroke="#1F1A14" strokeWidth="1.5" />
    <line x1="32" y1="50" x2="38" y2="50" stroke="#1F1A14" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

// ===== Trust illustrations =====
const TrustFilterScene = () => (
  <svg viewBox="0 0 320 200" width="100%" style={{ maxWidth: 320 }}>
    {/* scroll */}
    <rect x="120" y="10" width="80" height="40" rx="6" fill="#FFFFFF" stroke="#1F1A14" strokeWidth="2" />
    <line x1="130" y1="22" x2="190" y2="22" stroke="#A89C87" strokeWidth="2" strokeLinecap="round" />
    <line x1="130" y1="30" x2="180" y2="30" stroke="#A89C87" strokeWidth="2" strokeLinecap="round" />
    <line x1="130" y1="38" x2="170" y2="38" stroke="#A89C87" strokeWidth="2" strokeLinecap="round" />
    {/* funnel */}
    <polygon points="100,70 220,70 180,110 140,110" fill="#FBE7C0" stroke="#1F1A14" strokeWidth="2" />
    {/* drops */}
    <circle cx="155" cy="60" r="3" fill="#5DA877" />
    <circle cx="165" cy="60" r="3" fill="#E0A640" />
    {/* trays */}
    <rect x="40"  y="130" width="100" height="50" rx="8" fill="#D5EBDB" stroke="#1F1A14" strokeWidth="2" />
    <rect x="180" y="130" width="100" height="50" rx="8" fill="#FBE7C0" stroke="#1F1A14" strokeWidth="2" />
    <text x="90"  y="160" fontSize="12" fontWeight="700" textAnchor="middle" fill="#1F1A14" fontFamily="Inter, sans-serif">Official</text>
    <text x="230" y="160" fontSize="12" fontWeight="700" textAnchor="middle" fill="#1F1A14" fontFamily="Inter, sans-serif">Unconfirmed</text>
    <text x="90"  y="174" fontSize="10" textAnchor="middle" fill="#5DA877" fontFamily="Inter, sans-serif">✓</text>
    <text x="230" y="174" fontSize="10" textAnchor="middle" fill="#E0A640" fontFamily="Inter, sans-serif">?</text>
    {/* falling pieces */}
    <rect x="80" y="118" width="20" height="6" rx="1" fill="#5DA877">
      <animate attributeName="y" values="118;125;118" dur="3s" repeatCount="indefinite" />
    </rect>
    <rect x="220" y="118" width="20" height="6" rx="1" fill="#E0A640">
      <animate attributeName="y" values="118;125;118" dur="3s" begin="1s" repeatCount="indefinite" />
    </rect>
  </svg>
);

const ShieldCheck = () => (
  <svg viewBox="0 0 80 80" width="56" height="56" className="shield">
    <path d="M40 6 L66 16 L66 38 Q66 62 40 74 Q14 62 14 38 L14 16 Z" fill="#5DA877" stroke="#1F1A14" strokeWidth="2" />
    <path d="M28 40 L37 49 L54 32" stroke="#FFFFFF" strokeWidth="4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const ShieldQuestion = () => (
  <svg viewBox="0 0 80 80" width="56" height="56" className="shield">
    <circle cx="40" cy="40" r="32" fill="#E0A640" stroke="#1F1A14" strokeWidth="2" />
    <text x="40" y="52" fontSize="34" fontWeight="800" textAnchor="middle" fill="#FFFFFF" fontFamily="Inter, sans-serif">?</text>
  </svg>
);

Object.assign(window, {
  LogoMark, HeroScene,
  FloatCalendar, FloatBook, FloatClock,
  IconScan, IconCalendarFlip, IconClockSweep, IconChat,
  VerdictIcon,
  MiniBook, MiniPencil, MiniPaper, MiniBulb,
  SceneCommunity, SceneGroup, ScenePartner, SceneMentor, SceneResources, SceneShop,
  TrustFilterScene, ShieldCheck, ShieldQuestion,
});

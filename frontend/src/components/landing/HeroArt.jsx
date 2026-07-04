// Bespoke vector hero illustration — no stock art. A satellite observes a
// stylised India landmass while weather systems, reservoirs and an AI risk
// graph converge over it. Built entirely in SVG/CSS so it renders crisp at
// any size and animates with pure CSS (respects prefers-reduced-motion).

const RISK_NODES = [
  { x: 368, y: 240, r: "low", delay: "0s" },   // North India (Delhi/Punjab)
  { x: 592, y: 400, r: "med", delay: "0.4s" },  // East India (Bihar/Jharkhand)
  { x: 272, y: 368, r: "low", delay: "0.9s" },  // West India (Rajasthan)
  { x: 432, y: 400, r: "high", delay: "0.2s" }, // Central India (Madhya Pradesh)
  { x: 528, y: 528, r: "med", delay: "1.3s" },  // East Coast (Odisha/Andhra)
  { x: 400, y: 656, r: "high", delay: "0.6s" }, // South-Central (Telangana/Karnataka)
  { x: 336, y: 528, r: "low", delay: "1.6s" },  // West-Southwest (Maharashtra)
  { x: 432, y: 784, r: "med", delay: "1s" },   // South India (Tamil Nadu)
];

const RISK_COLOR = {
  low: "#00e5a8",
  med: "#ffc857",
  high: "#ff6a6a",
};

const EDGES = [
  [0, 1],
  [0, 2],
  [1, 3],
  [1, 4],
  [2, 3],
  [2, 6],
  [3, 4],
  [3, 5],
  [5, 6],
  [5, 7],
  [4, 7],
];

export default function HeroArt() {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[560px] select-none">
      {/* ambient glow field */}
      <div className="absolute inset-0 rounded-full bg-[radial-gradient(closest-side,rgba(0,200,255,0.16),transparent_70%)]" />
      <div className="animate-spin-slower absolute inset-6 rounded-full border border-dashed border-white/10" />
      <div className="animate-spin-slow absolute inset-16 rounded-full border border-white/10" />

      <svg
        viewBox="0 0 1024 1024"
        className="relative h-full w-full drop-shadow-[0_0_60px_rgba(0,200,255,0.15)]"
        role="img"
        aria-label="Satellite observing India with AI-modelled weather and drought-risk overlays"
      >
        <defs>
          <radialGradient id="glow" cx="50%" cy="50%" r="60%">
            <stop offset="0%" stopColor="#0e2540" />
            <stop offset="100%" stopColor="#08111f" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="edgeGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#00c8ff" stopOpacity="0" />
            <stop offset="50%" stopColor="#00c8ff" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#00e5a8" stopOpacity="0" />
          </linearGradient>
          <filter id="softBlur" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="12" />
          </filter>
        </defs>

        <rect x="0" y="0" width="1024" height="1024" fill="url(#glow)" />

        {/* terrain grid plane */}
        <g className="mask-fade-b" opacity="0.35">
          {Array.from({ length: 15 }).map((_, i) => (
            <line
              key={`h${i}`}
              x1="50"
              y1={50 + i * 66}
              x2="974"
              y2={50 + i * 66}
              stroke="#2dd4ff"
              strokeWidth="1.2"
            />
          ))}
          {Array.from({ length: 15 }).map((_, i) => (
            <line
              key={`v${i}`}
              x1={50 + i * 66}
              y1="50"
              x2={50 + i * 66}
              y2="974"
              stroke="#2dd4ff"
              strokeWidth="1.2"
            />
          ))}
        </g>

        {/* Transparent India Map Image background */}
        <image
          href="/india.png"
          x="0"
          y="0"
          width="1024"
          height="1024"
          className="opacity-75"
        />

        {/* weather system — cyclonic swirl, in Arabian Sea (lower left-ish) */}
        <g className="animate-spin-slower origin-[150px_680px]" opacity="0.55">
          <path
            d="M150 630 A50 50 0 1 1 100 680"
            fill="none"
            stroke="#00c8ff"
            strokeWidth="3.5"
            strokeLinecap="round"
          />
          <path
            d="M150 645 A35 35 0 1 1 115 680"
            fill="none"
            stroke="#7fe6ff"
            strokeWidth="2.4"
            strokeLinecap="round"
            opacity="0.7"
          />
        </g>

        {/* rainfall streaks, over Bay of Bengal (lower right-ish) */}
        <g stroke="#00c8ff" strokeWidth="3" strokeLinecap="round" opacity="0.5">
          <line x1="780" y1="650" x2="760" y2="690" className="animate-pulse-soft" />
          <line x1="810" y1="660" x2="790" y2="700" className="animate-pulse-soft" style={{ animationDelay: "0.3s" }} />
          <line x1="840" y1="650" x2="820" y2="690" className="animate-pulse-soft" style={{ animationDelay: "0.6s" }} />
        </g>

        {/* heatwave lines, west-central (Rajasthan/Gujarat) */}
        <g stroke="#ffc857" strokeWidth="3" fill="none" opacity="0.55" className="animate-drift">
          <path d="M220 380 q15 -15 30 0 t30 0 t30 0" />
          <path d="M220 398 q15 -15 30 0 t30 0 t30 0" opacity="0.6" />
        </g>

        {/* reservoir mark, south-west */}
        <g transform="translate(320,680)" opacity="0.85">
          <path d="M-20 8 q20 -22 40 0 q-20 14 -40 0 Z" fill="#00e5a8" opacity="0.5" />
          <circle r="4.5" fill="#00e5a8" className="animate-pulse-soft" />
        </g>

        {/* neural risk graph */}
        <g strokeWidth="2" fill="none">
          {EDGES.map(([a, b], i) => {
            const A = RISK_NODES[a];
            const B = RISK_NODES[b];
            return (
              <line
                key={i}
                x1={A.x}
                y1={A.y}
                x2={B.x}
                y2={B.y}
                stroke="url(#edgeGrad)"
                strokeDasharray="10 16"
                className="animate-dash"
              />
            );
          })}
        </g>
        <g>
          {RISK_NODES.map((n, i) => (
            <g key={i} transform={`translate(${n.x} ${n.y})`}>
              <circle r="15" fill={RISK_COLOR[n.r]} opacity="0.18" className="animate-pulse-soft" style={{ animationDelay: n.delay }} />
              <circle r="5.5" fill={RISK_COLOR[n.r]} />
            </g>
          ))}
        </g>

        {/* satellite orbit */}
        <g className="origin-[512px_512px] animate-spin-slow">
          <g transform="translate(512,112)">
            <rect x="-12" y="-6" width="24" height="12" rx="3" fill="#eaf2fb" />
            <rect x="-36" y="-2.8" width="20" height="5.6" fill="#00c8ff" />
            <rect x="16" y="-2.8" width="20" height="5.6" fill="#00c8ff" />
            <circle r="20" fill="#00c8ff" opacity="0.16" filter="url(#softBlur)" />
          </g>
        </g>
      </svg>
    </div>
  );
}

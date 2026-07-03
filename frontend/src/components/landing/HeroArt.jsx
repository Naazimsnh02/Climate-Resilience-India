// Bespoke vector hero illustration — no stock art. A satellite observes a
// stylised India landmass while weather systems, reservoirs and an AI risk
// graph converge over it. Built entirely in SVG/CSS so it renders crisp at
// any size and animates with pure CSS (respects prefers-reduced-motion).

const RISK_NODES = [
  { x: 205, y: 95, r: "low", delay: "0s" },
  { x: 265, y: 130, r: "med", delay: "0.4s" },
  { x: 150, y: 165, r: "low", delay: "0.9s" },
  { x: 230, y: 220, r: "high", delay: "0.2s" },
  { x: 300, y: 210, r: "med", delay: "1.3s" },
  { x: 190, y: 300, r: "high", delay: "0.6s" },
  { x: 140, y: 260, r: "low", delay: "1.6s" },
  { x: 205, y: 380, r: "med", delay: "1s" },
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
        viewBox="0 0 420 460"
        className="relative h-full w-full drop-shadow-[0_0_60px_rgba(0,200,255,0.15)]"
        role="img"
        aria-label="Satellite observing India with AI-modelled weather and drought-risk overlays"
      >
        <defs>
          <radialGradient id="glow" cx="50%" cy="42%" r="60%">
            <stop offset="0%" stopColor="#0e2540" />
            <stop offset="100%" stopColor="#08111f" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="landFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#132a44" />
            <stop offset="100%" stopColor="#0d1c30" />
          </linearGradient>
          <linearGradient id="edgeGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#00c8ff" stopOpacity="0" />
            <stop offset="50%" stopColor="#00c8ff" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#00e5a8" stopOpacity="0" />
          </linearGradient>
          <filter id="softBlur" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="6" />
          </filter>
        </defs>

        <rect x="0" y="0" width="420" height="460" fill="url(#glow)" />

        {/* terrain grid plane */}
        <g className="mask-fade-b" opacity="0.35">
          {Array.from({ length: 11 }).map((_, i) => (
            <line
              key={`h${i}`}
              x1="20"
              y1={60 + i * 34}
              x2="400"
              y2={60 + i * 34}
              stroke="#2dd4ff"
              strokeWidth="0.6"
            />
          ))}
          {Array.from({ length: 13 }).map((_, i) => (
            <line
              key={`v${i}`}
              x1={20 + i * 32}
              y1="60"
              x2={20 + i * 32}
              y2="400"
              stroke="#2dd4ff"
              strokeWidth="0.6"
            />
          ))}
        </g>

        {/* weather system — cyclonic swirl, upper left */}
        <g className="animate-spin-slower origin-[95px_110px]" opacity="0.55">
          <path
            d="M95 70 A40 40 0 1 1 55 110"
            fill="none"
            stroke="#00c8ff"
            strokeWidth="2.4"
            strokeLinecap="round"
          />
          <path
            d="M95 82 A28 28 0 1 1 67 110"
            fill="none"
            stroke="#7fe6ff"
            strokeWidth="1.6"
            strokeLinecap="round"
            opacity="0.7"
          />
        </g>

        {/* rainfall streaks, upper right over Bay of Bengal */}
        <g stroke="#00c8ff" strokeWidth="2" strokeLinecap="round" opacity="0.5">
          <line x1="336" y1="66" x2="326" y2="90" className="animate-pulse-soft" />
          <line x1="352" y1="72" x2="342" y2="98" className="animate-pulse-soft" style={{ animationDelay: "0.3s" }} />
          <line x1="368" y1="66" x2="358" y2="92" className="animate-pulse-soft" style={{ animationDelay: "0.6s" }} />
        </g>

        {/* heatwave lines, west-central */}
        <g stroke="#ffc857" strokeWidth="2" fill="none" opacity="0.55" className="animate-drift">
          <path d="M50 250 q10 -10 20 0 t20 0 t20 0" />
          <path d="M50 262 q10 -10 20 0 t20 0 t20 0" opacity="0.6" />
        </g>

        {/* stylised India landmass */}
        <path
          d="M205 30 L255 55 L295 100 L312 155 L288 220 L260 285 L235 345 L205 410
             L178 345 L152 285 L122 220 L98 155 L112 100 L150 55 Z"
          fill="url(#landFill)"
          stroke="#00c8ff"
          strokeOpacity="0.55"
          strokeWidth="1.4"
        />
        <ellipse cx="228" cy="432" rx="10" ry="15" fill="url(#landFill)" stroke="#00c8ff" strokeOpacity="0.4" strokeWidth="1" />

        {/* reservoir mark, south-west */}
        <g transform="translate(150,340)" opacity="0.85">
          <path d="M-14 6 q14 -16 28 0 q-14 10 -28 0 Z" fill="#00e5a8" opacity="0.5" />
          <circle r="3" fill="#00e5a8" className="animate-pulse-soft" />
        </g>

        {/* neural risk graph */}
        <g strokeWidth="1" fill="none">
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
                strokeDasharray="6 10"
                className="animate-dash"
              />
            );
          })}
        </g>
        <g>
          {RISK_NODES.map((n, i) => (
            <g key={i} transform={`translate(${n.x} ${n.y})`}>
              <circle r="9" fill={RISK_COLOR[n.r]} opacity="0.18" className="animate-pulse-soft" style={{ animationDelay: n.delay }} />
              <circle r="3.4" fill={RISK_COLOR[n.r]} />
            </g>
          ))}
        </g>

        {/* satellite orbit */}
        <g className="origin-[210px_150px] animate-spin-slow">
          <g transform="translate(210,26)">
            <rect x="-6" y="-3" width="12" height="6" rx="1.5" fill="#eaf2fb" />
            <rect x="-18" y="-1.4" width="10" height="2.8" fill="#00c8ff" />
            <rect x="8" y="-1.4" width="10" height="2.8" fill="#00c8ff" />
            <circle r="10" fill="#00c8ff" opacity="0.16" filter="url(#softBlur)" />
          </g>
        </g>
      </svg>
    </div>
  );
}

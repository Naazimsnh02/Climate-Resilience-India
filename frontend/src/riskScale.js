export const RISK_BANDS = [
  { key: "critical", label: "Critical", min: 70, var: "--risk-critical", hex: "#ef4444" },
  { key: "high", label: "High", min: 50, var: "--risk-high", hex: "#f97316" },
  { key: "moderate", label: "Moderate", min: 30, var: "--risk-moderate", hex: "#eab308" },
  { key: "low", label: "Low", min: 0, var: "--risk-low", hex: "#22c55e" },
];

export function riskBand(score) {
  if (score == null) return null;
  return RISK_BANDS.find((b) => score >= b.min) ?? RISK_BANDS[RISK_BANDS.length - 1];
}

export function riskColorVar(score) {
  const band = riskBand(score);
  return band ? `var(${band.var})` : "var(--text-dim)";
}

// Fixed hex palette for contexts (e.g. Leaflet's SVG renderer) that don't
// reliably resolve CSS custom properties across themes/browsers.
export function riskColorHex(score) {
  const band = riskBand(score);
  return band ? band.hex : "#94a3b8";
}

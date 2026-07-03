// Lightweight client-side heuristics that turn the risk model's outputs into
// suggested next actions. Not a model prediction - just a readable summary of
// the same thresholds a triage analyst would apply by eye.
export function getRecommendedActions(risk, signals) {
  const actions = [];
  const score = risk?.risk_score;
  const daysToCritical = risk?.days_to_critical_reservoir;
  const soilMoisture = signals?.soil_moisture_pct?.value;
  const reservoirPct = signals?.reservoir_pct_full?.value;

  if (score != null && score >= 70) {
    actions.push({ icon: "🚚", label: "Deploy water tankers", priority: "high" });
  } else if (reservoirPct != null && reservoirPct < 25) {
    actions.push({ icon: "🚚", label: "Pre-position water tankers", priority: "medium" });
  }

  if (soilMoisture != null && soilMoisture < 35) {
    actions.push({ icon: "🌾", label: "Promote millet / short-duration crops", priority: score >= 60 ? "high" : "medium" });
  }

  if (daysToCritical != null && daysToCritical < 180) {
    actions.push({ icon: "⏳", label: "Issue delay-sowing advisory", priority: daysToCritical < 90 ? "high" : "medium" });
  }

  actions.push({ icon: "🛠️", label: "Activate MGNREGA works", priority: "low" });

  return actions.slice(0, 4);
}

export const PRIORITY_LABELS = {
  high: "High Priority",
  medium: "Medium Priority",
  low: "Low Priority",
};

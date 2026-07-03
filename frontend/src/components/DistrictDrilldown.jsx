import { useEffect, useState } from "react";
import { getDistrict } from "../api";
import { riskBand, riskColorVar } from "../riskScale";
import { getRecommendedActions, PRIORITY_LABELS } from "../recommendedActions";
import { useAppState } from "../context/AppState";

function formatNum(val, decimals = 2) {
  if (val == null) return "—";
  const num = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(num)) return val;
  return num.toFixed(decimals);
}

function formatDate(dateStr) {
  if (!dateStr) return "—";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch (e) {
    return dateStr;
  }
}

function MetricCard({ label, value, unit, sub, gaugePct, gaugeColor }) {
  return (
    <div className="metric-card">
      <span className="metric-card__label">{label}</span>
      <div className="metric-card__value-row">
        <span className="metric-card__value">{value}</span>
        {unit && <span className="metric-card__unit">{unit}</span>}
      </div>
      {gaugePct != null && (
        <div className="gauge-track">
          <div
            className="gauge-track__fill"
            style={{ width: `${Math.min(100, Math.max(0, gaugePct))}%`, background: gaugeColor }}
          />
        </div>
      )}
      {sub && <span className="metric-card__sub">{sub}</span>}
    </div>
  );
}

export default function DistrictDrilldown({ districtId, onOpenChat }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { openChat } = useAppState();

  useEffect(() => {
    if (!districtId) return;
    setLoading(true);
    setError(null);
    getDistrict(districtId)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [districtId]);

  if (!districtId) {
    return <div className="drilldown drilldown--empty">Click a district on the map to see its profile.</div>;
  }
  if (loading) return <div className="drilldown">Loading…</div>;
  if (error) return <div className="drilldown drilldown--error">Error: {error}</div>;
  if (!data) return null;

  const { risk, signals } = data;
  const band = riskBand(risk.risk_score);
  const actions = getRecommendedActions(risk, signals);

  function askAiAboutDistrict() {
    if (onOpenChat) onOpenChat();
    openChat("triage", `Explain why ${data.name}, ${data.state} is at risk and what I should do about it.`);
  }

  return (
    <div className="drilldown">
      <div className="drilldown__heading-row">
        <div>
          <h2>{data.name}, {data.state}</h2>
          <p className="drilldown__crops">
            {data.flagged_belt && <span className="badge">Flagged belt</span>} Kharif crops: {data.primary_kharif_crops || "—"}
          </p>
        </div>
        {band && <span className={`risk-pill risk-pill--${band.key}`}>{band.label}</span>}
      </div>

      <div className="district-cards__grid">
        <MetricCard
          label="Risk score"
          value={risk.risk_score != null ? risk.risk_score.toFixed(1) : "—"}
          unit="/ 100"
          gaugePct={risk.risk_score}
          gaugeColor={riskColorVar(risk.risk_score)}
        />
        <MetricCard
          label="Days to critical reservoir"
          value={formatNum(risk.days_to_critical_reservoir, 0)}
          sub={risk.days_to_critical_reservoir != null && risk.days_to_critical_reservoir < 180 ? "Critical < 180 days" : null}
        />
        <MetricCard
          label="Reservoir capacity"
          value={formatNum(signals.reservoir_pct_full.value, 1)}
          unit="%"
          gaugePct={signals.reservoir_pct_full.value}
          gaugeColor="var(--accent)"
          sub={signals.reservoir_pct_full.as_of ? `as of ${formatDate(signals.reservoir_pct_full.as_of)}` : null}
        />
        <MetricCard
          label="Rainfall (30d)"
          value={formatNum(signals.precip_mm_30d.value, 1)}
          unit="mm"
          sub={signals.precip_mm_30d.as_of ? `as of ${formatDate(signals.precip_mm_30d.as_of)}` : null}
        />
        <MetricCard
          label="NDVI"
          value={formatNum(signals.ndvi.value, 3)}
          gaugePct={signals.ndvi.value != null ? Math.max(0, Math.min(1, signals.ndvi.value)) * 100 : null}
          gaugeColor="var(--risk-low)"
          sub={signals.ndvi.as_of ? `as of ${formatDate(signals.ndvi.as_of)}` : null}
        />
        <MetricCard
          label="Soil moisture"
          value={formatNum(signals.soil_moisture_pct.value, 1)}
          unit="%"
          gaugePct={signals.soil_moisture_pct.value}
          gaugeColor="var(--accent)"
          sub={signals.soil_moisture_pct.as_of ? `as of ${formatDate(signals.soil_moisture_pct.as_of)}` : null}
        />
      </div>

      <p className="drilldown__model-version">
        Model: {risk.model_version || "—"} · as of {formatDate(risk.date)}
      </p>

      {risk.top_feature_attributions?.length > 0 && (
        <>
          <h3>Why this score</h3>
          <ul className="attribution-list">
            {risk.top_feature_attributions.map((a, i) => {
              const formattedAttr = a.attribution != null ? (a.attribution > 0 ? "+" : "") + formatNum(a.attribution, 3) : "";
              const rising = a.attribution > 0;
              return (
                <li key={i} className="attribution-row">
                  <code style={{ fontSize: "12.5px", padding: "2px 6px" }}>{a.feature}</code>
                  <span className={rising ? "attribution-row__value--up" : "attribution-row__value--down"}>{formattedAttr}</span>
                </li>
              );
            })}
          </ul>
        </>
      )}

      <h3>Recommended actions</h3>
      <div className="action-cards">
        {actions.map((a, i) => (
          <div className="action-card" key={i}>
            <span className="action-card__icon">{a.icon}</span>
            <span className="action-card__label">{a.label}</span>
            <span className={`action-card__priority action-card__priority--${a.priority}`}>{PRIORITY_LABELS[a.priority]}</span>
          </div>
        ))}
      </div>

      <button className="drilldown__ask-ai" onClick={askAiAboutDistrict}>
        ✨ Ask AI Copilot about {data.name}
      </button>
    </div>
  );
}

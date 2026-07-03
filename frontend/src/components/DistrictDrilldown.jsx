import { useEffect, useState } from "react";
import { getDistrict } from "../api";

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
    
    // Check if it has a time component
    if (dateStr.includes("T") || dateStr.includes(":")) {
      return date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      }) + " " + date.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      });
    }
    
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch (e) {
    return dateStr;
  }
}

const FEATURE_LABELS = {
  precip_mm_30d: "Rainfall (30-day)",
  groundwater_stress_score: "Groundwater Stress",
  soil_moisture_pct: "Soil Moisture",
  feels_like_c: "Feels Like Temp",
  ndvi: "Vegetation Index (NDVI)",
  reservoir_pct_full: "Reservoir capacity",
};

function getFeatureLabel(feature) {
  return FEATURE_LABELS[feature] || feature;
}

function Signal({ label, value, unit = "", asOf, extra, decimals = 1 }) {
  // If the value is a number, format it nicely
  const numericValue = typeof value === "string" ? parseFloat(value) : value;
  const formattedValue = !isNaN(numericValue) && typeof numericValue === "number"
    ? formatNum(numericValue, decimals)
    : value;

  return (
    <div className="signal-row">
      <span className="signal-row__label">{label}</span>
      <span className="signal-row__value">
        {formattedValue != null ? `${formattedValue}${unit}` : "—"}
        {extra}
      </span>
      <span className="signal-row__asof">{asOf ? `as of ${formatDate(asOf)}` : "no data"}</span>
    </div>
  );
}

export default function DistrictDrilldown({ districtId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
    return <div className="drilldown drilldown--empty">Click a district on the map to see details.</div>;
  }
  if (loading) return <div className="drilldown">Loading…</div>;
  if (error) return <div className="drilldown drilldown--error">Error: {error}</div>;
  if (!data) return null;

  const { risk, signals } = data;

  return (
    <div className="drilldown">
      <h2>{data.name}, {data.state}</h2>
      {data.flagged_belt && <span className="badge">Flagged belt</span>}
      <p className="drilldown__crops">Kharif crops: {data.primary_kharif_crops || "—"}</p>

      <div className="risk-score-block">
        <div className="risk-score-block__number">{risk.risk_score != null ? risk.risk_score.toFixed(1) : "—"}</div>
        <div className="risk-score-block__label">Risk score (0-100)</div>
      </div>
      <p style={{ margin: "4px 0", fontSize: "14px" }}>
        <strong>Days to critical reservoir:</strong> {risk.days_to_critical_reservoir != null ? formatNum(risk.days_to_critical_reservoir, 1) : "—"}
      </p>
      <p style={{ margin: "4px 0", fontSize: "14px" }}>
        <strong>Rainfall deficit rank:</strong> {risk.rainfall_deficit_rank ?? "—"}
      </p>
      <p className="drilldown__model-version" style={{ marginTop: "12px" }}>
        Model: {risk.model_version || "—"} · as of {formatDate(risk.date)}
      </p>

      {risk.top_feature_attributions?.length > 0 && (
        <>
          <h3 style={{ marginTop: "20px", marginBottom: "8px", fontSize: "16px", fontWeight: "600" }}>Why this score</h3>
          <ul className="attribution-list" style={{ margin: "0 0 16px 0", paddingLeft: "20px" }}>
            {risk.top_feature_attributions.map((a, i) => {
              const formattedAttr = a.attribution != null ? (a.attribution > 0 ? "+" : "") + formatNum(a.attribution, 3) : "";
              return (
                <li key={i} style={{ marginBottom: "4px" }}>
                  <code style={{ fontSize: "13px", padding: "2px 4px" }}>{getFeatureLabel(a.feature)}</code>:{" "}
                  <strong style={{ color: a.attribution > 0 ? "#e11d48" : "#0d9488" }}>{formattedAttr}</strong>
                </li>
              );
            })}
          </ul>
        </>
      )}

      <h3 style={{ marginTop: "20px", marginBottom: "8px", fontSize: "16px", fontWeight: "600" }}>Underlying signals</h3>
      <div className="signal-list">
        <Signal label="Drought bulletin status" value={signals.drought_bulletin_status.value} asOf={signals.drought_bulletin_status.as_of} />
        <Signal
          label="Reservoir % full"
          value={signals.reservoir_pct_full.value}
          unit="%"
          asOf={signals.reservoir_pct_full.as_of}
          extra={signals.reservoir_pct_full.granularity ? ` (${signals.reservoir_pct_full.granularity})` : ""}
          decimals={2}
        />
        <Signal label="Groundwater trend" value={signals.groundwater_trend.value} asOf={signals.groundwater_trend.as_of} />
        <Signal label="Rainfall (30d, mm)" value={signals.precip_mm_30d.value} asOf={signals.precip_mm_30d.as_of} decimals={1} />
        <Signal label="NDVI" value={signals.ndvi.value} asOf={signals.ndvi.as_of} decimals={3} />
        <Signal label="Soil moisture" value={signals.soil_moisture_pct.value} unit="%" asOf={signals.soil_moisture_pct.as_of} decimals={2} />
        <Signal label="Temperature" value={signals.weather.temp_c} unit="°C" asOf={signals.weather.as_of} decimals={1} />
      </div>
    </div>
  );
}

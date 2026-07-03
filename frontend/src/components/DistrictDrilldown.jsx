import { useEffect, useState } from "react";
import { getDistrict } from "../api";

function Signal({ label, value, unit = "", asOf, extra }) {
  return (
    <div className="signal-row">
      <span className="signal-row__label">{label}</span>
      <span className="signal-row__value">
        {value != null ? `${value}${unit}` : "—"}
        {extra}
      </span>
      <span className="signal-row__asof">{asOf ? `as of ${asOf}` : "no data"}</span>
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
      <p>Days to critical reservoir: {risk.days_to_critical_reservoir ?? "—"}</p>
      <p>Rainfall deficit rank: {risk.rainfall_deficit_rank ?? "—"}</p>
      <p className="drilldown__model-version">Model: {risk.model_version || "—"} · as of {risk.date || "—"}</p>

      {risk.top_feature_attributions?.length > 0 && (
        <>
          <h3>Why this score</h3>
          <ul className="attribution-list">
            {risk.top_feature_attributions.map((a, i) => (
              <li key={i}>
                {a.feature ?? JSON.stringify(a)}: {a.attribution ?? ""}
              </li>
            ))}
          </ul>
        </>
      )}

      <h3>Underlying signals</h3>
      <div className="signal-list">
        <Signal label="Drought bulletin status" value={signals.drought_bulletin_status.value} asOf={signals.drought_bulletin_status.as_of} />
        <Signal
          label="Reservoir % full"
          value={signals.reservoir_pct_full.value}
          unit="%"
          asOf={signals.reservoir_pct_full.as_of}
          extra={signals.reservoir_pct_full.granularity ? ` (${signals.reservoir_pct_full.granularity})` : ""}
        />
        <Signal label="Groundwater trend" value={signals.groundwater_trend.value} asOf={signals.groundwater_trend.as_of} />
        <Signal label="Rainfall (30d, mm)" value={signals.precip_mm_30d.value} asOf={signals.precip_mm_30d.as_of} />
        <Signal label="NDVI" value={signals.ndvi.value} asOf={signals.ndvi.as_of} />
        <Signal label="Soil moisture" value={signals.soil_moisture_pct.value} unit="%" asOf={signals.soil_moisture_pct.as_of} />
        <Signal label="Temperature" value={signals.weather.temp_c} unit="°C" asOf={signals.weather.as_of} />
      </div>
    </div>
  );
}

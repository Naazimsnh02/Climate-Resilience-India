import { useMemo, useState } from "react";
import { riskBand, riskColorVar } from "../riskScale";
import { useAppState } from "../context/AppState";

export default function DistrictsPage() {
  const [search, setSearch] = useState("");
  const { districts, districtsError: error, selectDistrict } = useAppState();

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return districts
      .filter((d) => !q || d.name.toLowerCase().includes(q) || d.state.toLowerCase().includes(q))
      .slice()
      .sort((a, b) => (b.risk_score ?? -1) - (a.risk_score ?? -1));
  }, [districts, search]);

  return (
    <div className="districts-page">
      <div className="districts-page__head">
        <h1>Districts</h1>
        <input
          className="districts-page__search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search district or state…"
        />
      </div>
      {error && <div className="map-load-error">Failed to load districts: {error}</div>}
      <div className="districts-table-wrap">
        <table className="districts-table">
          <thead>
            <tr>
              <th>District</th>
              <th>State</th>
              <th>Risk score</th>
              <th>Status</th>
              <th>Flagged belt</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => {
              const band = riskBand(d.risk_score);
              return (
                <tr key={d.district_id} onClick={() => selectDistrict(d.district_id)}>
                  <td>{d.name}</td>
                  <td>{d.state}</td>
                  <td className="districts-table__risk" style={{ color: riskColorVar(d.risk_score) }}>
                    {d.risk_score != null ? d.risk_score.toFixed(1) : "—"}
                  </td>
                  <td>{band && <span className={`risk-pill risk-pill--${band.key}`}>{band.label}</span>}</td>
                  <td>{d.flagged_belt ? "Yes" : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import { riskColorVar } from "../riskScale";

const IconMapPin = (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="card-icon">
    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
    <circle cx="12" cy="10" r="3" />
  </svg>
);

const IconAlert = (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="card-icon">
    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

const IconGauge = (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="card-icon">
    <path d="M12 2a10 10 0 0 1 7.54 16.59" />
    <path d="M12 2a10 10 0 0 0-7.54 16.59" />
    <path d="M8.5 13a4 4 0 0 1 7 0" />
    <path d="m16 11-4 4" />
  </svg>
);

const IconFlag = (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="card-icon">
    <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
    <line x1="4" y1="22" x2="4" y2="15" />
  </svg>
);

function StatCard({ label, value, unit, note, gaugePct, gaugeColor, icon, iconBgClass, themeClass }) {
  return (
    <div className={`stat-card ${themeClass || ""}`}>
      {icon && (
        <div className={`stat-card__icon-container ${iconBgClass || ""}`}>
          {icon}
        </div>
      )}
      <div className="stat-card__content">
        <span className="stat-card__label">{label}</span>
        <div className="stat-card__value-row">
          <span className="stat-card__value">{value}</span>
          {unit && <span className="stat-card__unit">{unit}</span>}
        </div>
        {gaugePct != null ? (
          <div className="gauge-track">
            <div
              className="gauge-track__fill"
              style={{ width: `${Math.min(100, Math.max(0, gaugePct))}%`, background: gaugeColor }}
            />
          </div>
        ) : (
          note && <span className="stat-card__note">{note}</span>
        )}
      </div>
    </div>
  );
}

export default function StatStrip({ districts }) {
  const scored = districts.filter((d) => d.risk_score != null);
  const total = districts.length;
  const highRisk = scored.filter((d) => d.risk_score >= 50).length;
  const flagged = districts.filter((d) => d.flagged_belt).length;
  const avgRisk = scored.length
    ? scored.reduce((sum, d) => sum + d.risk_score, 0) / scored.length
    : null;

  const mostRecent = districts.reduce((latest, d) => {
    if (!d.date) return latest;
    return !latest || d.date > latest ? d.date : latest;
  }, null);
  const mostRecentLabel = mostRecent
    ? new Date(mostRecent).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : null;

  return (
    <div className="stat-strip">
      <StatCard
        label="Districts monitored"
        value={`${scored.length} / ${total}`}
        note="100% coverage"
        icon={IconMapPin}
        iconBgClass="icon-bg--purple"
        themeClass="stat-card--purple"
      />
      <StatCard
        label="High-risk districts"
        value={highRisk}
        note="Risk score 50+"
        gaugePct={total ? (highRisk / total) * 100 : 0}
        gaugeColor="var(--risk-high)"
        icon={IconAlert}
        iconBgClass="icon-bg--red"
        themeClass="stat-card--red"
      />
      <StatCard
        label="Avg. risk score"
        value={avgRisk != null ? avgRisk.toFixed(1) : "—"}
        unit="/ 100"
        gaugePct={avgRisk}
        gaugeColor={riskColorVar(avgRisk)}
        icon={IconGauge}
        iconBgClass="icon-bg--green"
        themeClass="stat-card--green"
      />
      <StatCard
        label="Flagged belts"
        value={flagged}
        note={mostRecentLabel ? `As of ${mostRecentLabel}` : "No scores yet"}
        icon={IconFlag}
        iconBgClass="icon-bg--blue"
        themeClass="stat-card--blue"
      />
    </div>
  );
}

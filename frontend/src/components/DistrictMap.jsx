import { Fragment } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { RISK_BANDS, riskColorHex } from "../riskScale";

export default function DistrictMap({ districts, selectedId, onSelect }) {
  const withCoords = districts.filter((d) => d.lat != null && d.lon != null);

  return (
    <>
      <MapContainer center={[20.5, 78.5]} zoom={5} className="district-map">
        <TileLayer
          attribution='&copy; OpenStreetMap contributors &copy; CARTO'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
        />
        {withCoords.map((d) => {
          const hasScore = d.risk_score != null;
          const color = riskColorHex(d.risk_score);
          const selected = d.district_id === selectedId;
          const radius = selected ? 12 : hasScore ? 8 : 4;
          return (
            <Fragment key={d.district_id}>
              {hasScore && (
                <CircleMarker
                  center={[d.lat, d.lon]}
                  radius={radius + 6}
                  pathOptions={{
                    stroke: false,
                    fillColor: color,
                    fillOpacity: 0.18,
                  }}
                  interactive={false}
                />
              )}
              <CircleMarker
                center={[d.lat, d.lon]}
                radius={radius}
                pathOptions={{
                  color: selected ? "#f8fafc" : "#0a1120",
                  weight: selected ? 3 : hasScore ? 1.5 : 1,
                  fillColor: color,
                  fillOpacity: hasScore ? 0.95 : 0.55,
                }}
                eventHandlers={{ click: () => onSelect(d.district_id) }}
              >
                <Tooltip>
                  <strong>{d.name}</strong>, {d.state}
                  <br />
                  Risk: {hasScore ? d.risk_score.toFixed(1) : "Not yet scored"}
                </Tooltip>
              </CircleMarker>
            </Fragment>
          );
        })}
      </MapContainer>
      <div className="map-legend">
        <span className="map-legend__title">Risk Level:</span>
        {[...RISK_BANDS].reverse().map((b) => (
          <span className="map-legend__item" key={b.key}>
            <span className="map-legend__dot" style={{ background: b.hex }} />
            {b.label}
          </span>
        ))}
      </div>
    </>
  );
}

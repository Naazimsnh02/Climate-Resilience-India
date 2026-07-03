import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { RISK_BANDS, riskColorHex } from "../riskScale";

export default function DistrictMap({ districts, selectedId, onSelect }) {
  const withCoords = districts.filter((d) => d.lat != null && d.lon != null);

  return (
    <>
      <MapContainer center={[20.5, 78.5]} zoom={5} className="district-map">
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {withCoords.map((d) => (
          <CircleMarker
            key={d.district_id}
            center={[d.lat, d.lon]}
            radius={d.district_id === selectedId ? 12 : 8}
            pathOptions={{
              color: d.district_id === selectedId ? "#0f172a" : riskColorHex(d.risk_score),
              fillColor: riskColorHex(d.risk_score),
              fillOpacity: 0.85,
              weight: d.district_id === selectedId ? 3 : 1,
            }}
            eventHandlers={{ click: () => onSelect(d.district_id) }}
          >
            <Tooltip>
              <strong>{d.name}</strong>, {d.state}
              <br />
              Risk: {d.risk_score != null ? d.risk_score.toFixed(1) : "—"}
            </Tooltip>
          </CircleMarker>
        ))}
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

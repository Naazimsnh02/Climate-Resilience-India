import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";

function riskColor(score) {
  if (score == null) return "#999999";
  if (score >= 70) return "#c0392b";
  if (score >= 50) return "#e67e22";
  if (score >= 30) return "#f1c40f";
  return "#27ae60";
}

export default function DistrictMap({ districts, selectedId, onSelect }) {
  const withCoords = districts.filter((d) => d.lat != null && d.lon != null);

  return (
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
            color: d.district_id === selectedId ? "#2c3e50" : riskColor(d.risk_score),
            fillColor: riskColor(d.risk_score),
            fillOpacity: 0.8,
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
  );
}

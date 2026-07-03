const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8080";

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export function getHealth() {
  return request("/health");
}

export function listDistricts() {
  return request("/api/districts");
}

export function getDistrict(districtId) {
  return request(`/api/districts/${encodeURIComponent(districtId)}`);
}

export function sendChat(agent, { message, sessionId, userId }) {
  return request(`/api/chat/${agent}`, {
    method: "POST",
    body: JSON.stringify({
      message,
      session_id: sessionId ?? null,
      user_id: userId ?? "anonymous",
    }),
  });
}

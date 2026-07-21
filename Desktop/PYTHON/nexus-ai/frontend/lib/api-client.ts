const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (email: string, password: string) =>
    request("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  uploadStatus: (jobId: string, token: string) =>
    request(`/api/v1/uploads/${jobId}/status`, { headers: { Authorization: `Bearer ${token}` } }),
};

import { Incident } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

export async function getIncidents(severity?: string): Promise<Incident[]> {
  const url = new URL(`${API_BASE}/api/v1/incidents`);
  if (severity) url.searchParams.set("severity", severity);
  try {
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    // Graceful fallback when backend is offline
    return [];
  }
}

export async function getIncident(id: string): Promise<Incident | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/incidents/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function createFixBranch(id: string): Promise<{ status: string; branch?: string; detail?: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/incidents/${id}/branch`, {
      method: "POST",
    });
    return await res.json();
  } catch (err) {
    return { status: "error", detail: String(err) };
  }
}

export async function getHealth(): Promise<{ status: string; database_type?: string; database?: string; ai_provider?: string } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

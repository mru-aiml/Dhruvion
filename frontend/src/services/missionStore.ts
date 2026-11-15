import type { MissionPlanResponse } from "../types";

/**
 * The backend keeps missions in memory, so the latest mission id is shared across
 * workspaces through sessionStorage. A stale id (backend restarted) simply causes
 * the dependent request to fail; callers should plan a new mission then.
 */
const KEY = "dhruvion.lastMission.v1";
const EVENT = "dhruvion:mission";

export function saveMission(mission: MissionPlanResponse): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(mission));
  } catch {
    // Storage can be unavailable in private mode; the app still works without it.
  }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: mission }));
}

export function loadMission(): MissionPlanResponse | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as MissionPlanResponse;
    return parsed && typeof parsed.mission_id === "string" ? parsed : null;
  } catch {
    return null;
  }
}

export function clearMission(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // ignore
  }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: null }));
}

export function subscribeMission(listener: (mission: MissionPlanResponse | null) => void): () => void {
  const handler = (event: Event) => listener((event as CustomEvent<MissionPlanResponse | null>).detail ?? null);
  window.addEventListener(EVENT, handler);
  return () => window.removeEventListener(EVENT, handler);
}

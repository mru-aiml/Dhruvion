import { api } from "./client";
import type {
  HealthResponse,
  Region,
  LayerMeta,
  TerrainQueryResponse,
  HazardsResponse,
  TargetsResponse,
  RouteOptimizeResponse,
  MissionPlanResponse,
  ReturnFeasibilityResponse,
  RerouteResponse,
  AssistantResponse,
  ReportResponse,
} from "../../types";

interface AuthMeResponse {
  authenticated: boolean;
  user?: { id: number; email: string; full_name: string | null; is_active: boolean };
}

interface AuthResponse {
  user?: { id: number; email: string; full_name: string | null; is_active: boolean };
}

export const endpoints = {
  health: () => api.get<HealthResponse>("/health").then((r) => r.data),
  regions: () => api.get<{ items: Region[] }>("/regions").then((r) => r.data),
  layers: (regionId: string) =>
    api.get<{ region_id: string; items: LayerMeta[] }>(`/layers?region_id=${encodeURIComponent(regionId)}`).then((r) => r.data),
  terrain: (regionId: string, x: number, y: number) =>
    api.get<TerrainQueryResponse>(`/terrain?region_id=${encodeURIComponent(regionId)}&x=${x}&y=${y}`).then((r) => r.data),
  hazards: (regionId: string) =>
    api.get<HazardsResponse>(`/hazards?region_id=${encodeURIComponent(regionId)}`).then((r) => r.data),
  targets: (regionId: string, params?: Record<string, string | number | boolean>) => {
    const q = new URLSearchParams({ region_id: regionId });
    if (params) Object.entries(params).forEach(([k, v]) => q.set(k, String(v)));
    return api.get<TargetsResponse>(`/targets?${q.toString()}`).then((r) => r.data);
  },
  routeOptimize: (body: unknown) => api.post<RouteOptimizeResponse>("/route/optimize", body).then((r) => r.data),
  missionPlan: (body: unknown) => api.post<MissionPlanResponse>("/mission/plan", body).then((r) => r.data),
  missionReturn: (body: unknown) => api.post<ReturnFeasibilityResponse>("/mission/return", body).then((r) => r.data),
  reroute: (body: unknown) => api.post<RerouteResponse>("/route/reroute", body).then((r) => r.data),
  assistantAsk: (body: unknown) => api.post<AssistantResponse>("/assistant/ask", body).then((r) => r.data),
  report: (body: unknown) => api.post<ReportResponse>("/mission/report", body).then((r) => r.data),
  authRegister: (body: unknown) => api.post<AuthResponse>("/auth/register", body).then((r) => r.data),
  authLogin: (body: unknown) => api.post<AuthResponse>("/auth/login", body).then((r) => r.data),
  authLogout: () => api.post("/auth/logout").then((r) => r.data),
  authMe: () => api.get<AuthMeResponse>("/auth/me").then((r) => r.data),
};

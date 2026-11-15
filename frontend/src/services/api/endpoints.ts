import { api } from "./client";
import type {
  AssistantHealthResponse,
  AssistantResponse,
  CoverageSummary,
  DatasetCatalogResponse,
  HealthResponse,
  ImageryResponse,
  LayerMeta,
  MissionPlanResponse,
  MissionRecord,
  MissionRouteCreateRequest,
  MissionRouteRecord,
  MissionCreateRequest,
  MissionUpdateRequest,
  RadiationResponse,
  Region,
  RemsResponse,
  RerouteResponse,
  ReportResponse,
  ReturnFeasibilityResponse,
  RouteOptimizeResponse,
  TargetsResponse,
  TerrainLayerPointResponse,
  TerrainProfileResponse,
  TerrainQueryResponse,
  HazardsResponse,
} from "../../types";

interface AuthMeResponse {
  authenticated: boolean;
  user?: { id: number; email: string; full_name: string | null; is_active: boolean };
}

interface AuthResponse {
  user?: { id: number; email: string; full_name: string | null; is_active: boolean };
}

const ASSISTANT_TIMEOUT_MS = 60000;

export const endpoints = {
  health: () => api.get<HealthResponse>("/health").then((r) => r.data),
  regions: () => api.get<{ items: Region[] }>("/regions").then((r) => r.data),
  layers: (regionId: string) =>
    api.get<{ region_id: string; items: LayerMeta[] }>(`/layers?region_id=${encodeURIComponent(regionId)}`).then((r) => r.data),
  datasets: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params ?? {});
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return api.get<DatasetCatalogResponse>(`/datasets${suffix}`).then((r) => r.data);
  },
  imagery: () => api.get<ImageryResponse>("/imagery").then((r) => r.data),
  terrain: (regionId: string, x: number, y: number) =>
    api.get<TerrainQueryResponse>(`/terrain?region_id=${encodeURIComponent(regionId)}&x=${x}&y=${y}`).then((r) => r.data),
  terrainLayer: (layer: "elevation" | "slope" | "roughness", regionId: string, x: number, y: number) =>
    api
      .get<TerrainLayerPointResponse>(
        `/terrain/${layer}?region_id=${encodeURIComponent(regionId)}&x=${x}&y=${y}`,
      )
      .then((r) => r.data),
  terrainCoverage: (regionId: string, x: number, y: number) =>
    api
      .get<TerrainLayerPointResponse>(
        `/terrain/coverage?region_id=${encodeURIComponent(regionId)}&x=${x}&y=${y}`,
      )
      .then((r) => r.data),
  terrainCoverageSummary: (regionId: string) =>
    api
      .get<CoverageSummary>(`/terrain/coverage/summary?region_id=${encodeURIComponent(regionId)}`)
      .then((r) => r.data),
  terrainProfile: (
    regionId: string,
    start: { x: number; y: number },
    end: { x: number; y: number },
    samples = 40,
  ) => {
    const q = new URLSearchParams({
      region_id: regionId,
      start_x: String(start.x),
      start_y: String(start.y),
      end_x: String(end.x),
      end_y: String(end.y),
      samples: String(samples),
    });
    return api.get<TerrainProfileResponse>(`/terrain/profile?${q.toString()}`).then((r) => r.data);
  },
  hazards: (regionId: string) =>
    api.get<HazardsResponse>(`/hazards?region_id=${encodeURIComponent(regionId)}`).then((r) => r.data),
  targets: (regionId: string, params?: Record<string, string | number | boolean>) => {
    const q = new URLSearchParams({ region_id: regionId });
    if (params) Object.entries(params).forEach(([k, v]) => q.set(k, String(v)));
    return api.get<TargetsResponse>(`/targets?${q.toString()}`).then((r) => r.data);
  },
  rems: (regionId = "gale_crater", sol?: number) => {
    const q = new URLSearchParams({ region_id: regionId });
    if (sol !== undefined) q.set("sol", String(sol));
    return api.get<RemsResponse>(`/environment/rems?${q.toString()}`).then((r) => r.data);
  },
  radiation: (regionId = "gale_crater", sol?: number) => {
    const q = new URLSearchParams({ region_id: regionId });
    if (sol !== undefined) q.set("sol", String(sol));
    return api.get<RadiationResponse>(`/environment/radiation?${q.toString()}`).then((r) => r.data);
  },
  routeOptimize: (body: unknown) => api.post<RouteOptimizeResponse>("/route/optimize", body).then((r) => r.data),
  missionPlan: (body: unknown) => api.post<MissionPlanResponse>("/mission/plan", body).then((r) => r.data),
  missions: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params ?? {});
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return api.get<MissionRecord[]>(`/missions${suffix}`).then((r) => r.data);
  },
  missionGet: (id: string) => api.get<MissionRecord>(`/missions/${encodeURIComponent(id)}`).then((r) => r.data),
  missionCreate: (body: MissionCreateRequest) => api.post<MissionRecord>("/missions", body).then((r) => r.data),
  missionUpdate: (id: string, body: MissionUpdateRequest) =>
    api.patch<MissionRecord>(`/missions/${encodeURIComponent(id)}`, body).then((r) => r.data),
  missionDelete: (id: string) => api.delete(`/missions/${encodeURIComponent(id)}`).then((r) => r.data),
  missionPlanRoute: (id: string, body?: unknown) =>
    api.post<MissionPlanResponse>(`/missions/${encodeURIComponent(id)}/plan`, body ?? {}).then((r) => r.data),
  missionReport: (id: string, body?: unknown) =>
    api.post<ReportResponse>(`/missions/${encodeURIComponent(id)}/report`, body ?? {}).then((r) => r.data),
  missionReportPdf: (id: string) =>
    api.get<Blob>(`/missions/${encodeURIComponent(id)}/report/pdf`, { responseType: "blob" }).then((r) => r.data),
  missionRoutes: (id: string) =>
    api.get<MissionRouteRecord[]>(`/missions/${encodeURIComponent(id)}/routes`).then((r) => r.data),
  missionRouteCreate: (id: string, body: MissionRouteCreateRequest) =>
    api.post<MissionRouteRecord>(`/missions/${encodeURIComponent(id)}/routes`, body).then((r) => r.data),
  missionReturn: (body: unknown) => api.post<ReturnFeasibilityResponse>("/mission/return", body).then((r) => r.data),
  reroute: (body: unknown) => api.post<RerouteResponse>("/route/reroute", body).then((r) => r.data),
  assistantAsk: (body: unknown) =>
    api.post<AssistantResponse>("/assistant/ask", body, { timeout: ASSISTANT_TIMEOUT_MS }).then((r) => r.data),
  assistantHealth: () => api.get<AssistantHealthResponse>("/assistant/health").then((r) => r.data),
  report: (body: unknown) => api.post<ReportResponse>("/mission/report", body).then((r) => r.data),
  authRegister: (body: unknown) => api.post<AuthResponse>("/auth/register", body).then((r) => r.data),
  authLogin: (body: unknown) => api.post<AuthResponse>("/auth/login", body).then((r) => r.data),
  authLogout: () => api.post("/auth/logout").then((r) => r.data),
  authMe: () => api.get<AuthMeResponse>("/auth/me").then((r) => r.data),
};

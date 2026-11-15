import { useEffect, useState } from "react";
import { Download, FileText, Loader2 } from "lucide-react";
import "leaflet/dist/leaflet.css";
import Panel from "../../components/common/Panel";
import { FeasibilityBadge, ProvenanceBadge } from "../../components/common/StatusBadge";
import StatusPill from "../../components/common/StatusPill";
import { endpoints } from "../../services/api/endpoints";
import { apiErrorMessage } from "../../services/api/client";
import { loadMission, saveMission } from "../../services/missionStore";
import { MOLA_ATTRIBUTION, MOLA_BASEMAP_URL, API_ORIGIN } from "../../components/map/mars";
import { MarsMap } from "../../components/map/MarsMap";
import { pushNotification } from "../../utils/notifications";
import type {
  CoverageSummary,
  MissionPlanResponse,
  RadDetectorSummary,
  RemsMeasurement,
  ReportResponse,
} from "../../types";

const REGION_ID = "gale_crater";
const DEFAULT_START = { lat: -4.5, lon: 137.2 };
const DEFAULT_DEST = { lat: -4.55, lon: 137.3 };
const DEFAULT_TIME_LIMIT = 600;

interface ReportEnvironment {
  availability?: string;
  sols?: number[];
  measurements?: Record<string, Record<string, RemsMeasurement>>;
  warnings?: string[];
  limitations?: string[];
}

interface ReportRadiation {
  availability?: string;
  sols?: number[];
  detectors?: Record<string, RadDetectorSummary>;
  unit?: string;
  warnings?: string[];
  limitations?: string[];
}

interface ReportContent {
  report_id?: string;
  generated_at?: string;
  mission?: MissionPlanResponse | null;
  terrain_coverage?: CoverageSummary | null;
  environment?: ReportEnvironment;
  radiation?: ReportRadiation;
  provenance?: string[];
  warnings?: string[];
  limitations?: string[];
}

export default function ReportsPage() {
  const [mission, setMission] = useState<MissionPlanResponse | null>(null);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [content, setContent] = useState<ReportContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        let current = loadMission();
        if (!current) {
          current = await planDefaultMission();
          saveMission(current);
        }

        let response: ReportResponse;
        try {
          response = await endpoints.report({ mission_id: current.mission_id, format: "json" });
        } catch {
          // The backend keeps missions in memory; a restart invalidates the stored id.
          const fresh = await planDefaultMission();
          saveMission(fresh);
          current = fresh;
          response = await endpoints.report({ mission_id: fresh.mission_id, format: "json" });
        }

        if (!active) return;
        setMission(current);
        setReport(response);
        setContent((response.content ?? null) as ReportContent | null);
      } catch (reason) {
        if (active) setError(apiErrorMessage(reason));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const exportReport = async () => {
    setExporting(true);
    setError(null);
    try {
      let current = mission ?? loadMission();
      if (!current) {
        current = await planDefaultMission();
        saveMission(current);
        setMission(current);
      }
      const response = report ?? (await endpoints.report({ mission_id: current.mission_id, format: "json" }));
      setReport(response);
      setContent((response.content ?? null) as ReportContent | null);
      if (response.download_url) {
        const link = document.createElement("a");
        link.href = API_ORIGIN + response.download_url;
        link.download = `dhruvion-report-${response.report_id}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
      setStatus(`Report ${response.report_id} · ${response.status}`);
      pushNotification(`Mission report exported: ${response.report_id}`, "/reports");
    } catch (reason) {
      setError(apiErrorMessage(reason));
    } finally {
      setExporting(false);
    }
  };

  const exportPdf = async () => {
    setExporting(true);
    setError(null);
    try {
      let current = mission ?? loadMission();
      if (!current) {
        current = await planDefaultMission();
        saveMission(current);
        setMission(current);
      }
      const blob = await endpoints.missionReportPdf(current.mission_id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `dhruvion-mission-report-${current.mission_id}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setStatus(`Mission report PDF generated for ${current.mission_id}`);
      pushNotification(`Mission report exported as PDF: ${current.mission_id}`, "/reports");
    } catch (reason) {
      setError(apiErrorMessage(reason));
    } finally {
      setExporting(false);
    }
  };

  const reportMission = content?.mission ?? mission;
  const route = reportMission?.route ?? null;
  const coverage = content?.terrain_coverage ?? null;
  const environment = content?.environment ?? null;
  const radiation = content?.radiation ?? null;
  const warnings = unique([...(content?.warnings ?? []), ...(report?.warnings ?? [])]);
  const limitations = content?.limitations ?? [];
  const provenance = content?.provenance ?? [];
  const dataSource = reportMission?.source?.name ?? coverage?.source?.name ?? null;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Mission Reports</h1>
          <p className="text-xs text-text-muted">
            Traceable summary assembled from the backend mission, terrain, environment and
            radiation services.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={exportPdf}
            disabled={exporting || loading}
            className="flex items-center gap-2 rounded-md bg-mars-orange px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {exporting ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            {exporting ? "Exporting…" : "Export report"}
          </button>
          <button
            onClick={exportReport}
            disabled={exporting || loading}
            className="flex items-center gap-2 rounded-md border border-line px-3 py-1.5 text-sm font-medium text-text-secondary disabled:opacity-50"
          >
            {exporting ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            Export JSON
          </button>
        </div>
      </div>

      {error && <div className="text-xs text-critical-red">{error}</div>}
      {loading && (
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <Loader2 size={14} className="animate-spin" /> Planning mission and assembling report…
        </div>
      )}
      {status && <div className="text-xs text-text-secondary">{status}</div>}

      {!loading && !reportMission && (
        <Panel title="Mission report">
          <p className="text-sm text-text-secondary">
            No mission is available. Plan a mission on the Route Planner screen, then return here to
            export its report.
          </p>
        </Panel>
      )}

      {reportMission && (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Panel title="Mission plan">
              <div className="flex flex-wrap items-center gap-2">
                <FeasibilityBadge status={reportMission.feasibility_status} />
                <StatusPill tone="derived" dot={false}>
                  {reportMission.route_strategy?.replace(/_/g, " ") ?? "balanced"}
                </StatusPill>
                <span className="text-[9px] uppercase tracking-[0.08em] text-text-muted">
                  {reportMission.mission_id}
                </span>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2">
                <ReportRow label="Region" value={reportMission.region_id ?? REGION_ID} />
                <ReportRow
                  label="Distance"
                  value={route ? `${(route.distance_m / 1000).toFixed(2)} km` : "unavailable"}
                />
                <ReportRow
                  label="Outbound"
                  value={fmtMin(reportMission.time_budget.outbound_min)}
                />
                <ReportRow
                  label="Exploration"
                  value={fmtMin(reportMission.time_budget.exploration_min)}
                />
                <ReportRow label="Return" value={fmtMin(reportMission.time_budget.return_min)} />
                <ReportRow label="Reserve" value={fmtMin(reportMission.time_budget.reserve_min)} />
                <ReportRow label="Total" value={fmtMin(reportMission.time_budget.total_min)} />
                <ReportRow label="Limit" value={fmtMin(reportMission.time_budget.limit_min)} />
              </dl>
              {reportMission.reasons.length > 0 && (
                <p className="mt-3 border-t border-line/50 pt-2.5 text-[11px] leading-relaxed text-text-secondary">
                  {reportMission.reasons.join(" ")}
                </p>
              )}
            </Panel>

            <Panel title="Selected exploration region">
              <div className="text-sm text-text-primary">
                Gale Crater · {REGION_ID.replace(/_/g, " ")}
              </div>
              <div className="mt-1 text-[11px] text-text-muted">
                Mars equirectangular (IAU:2015) · planetocentric coordinates · regional 463 m MOLA
                grid
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2">
                <ReportRow
                  label="Start"
                  value={formatCoord(reportMission.start)}
                />
                <ReportRow
                  label="Destination"
                  value={formatCoord(reportMission.destination)}
                />
                <ReportRow
                  label="Coverage"
                  value={
                    coverage
                      ? `${coverage.counts["1"] ?? 0} usable cells · ${coverage.counts["2"] ?? 0} elevation-only`
                      : "unavailable"
                  }
                />
                <ReportRow
                  label="Resolution"
                  value={coverage ? `${coverage.resolution_m.toFixed(0)} m/px` : "unavailable"}
                />
              </dl>
              <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-line/50 pt-2.5">
                {provenance.map((entry) => (
                  <ProvenanceBadge key={entry} status={entry} />
                ))}
                {dataSource && (
                  <span className="text-[10px] text-text-muted">{dataSource}</span>
                )}
              </div>
              <p className="mt-1.5 text-[10px] leading-relaxed text-text-muted">
                Regional terrain is not rover-scale trafficability and does not authorise a traverse.
              </p>
            </Panel>

            <Panel title="Route summary">
              {route && route.geometry?.coordinates?.length > 1 ? (
                <>
                  <div className="mb-2 h-32 overflow-hidden rounded-md border border-line">
                    <MarsMap
                      center={[-5.4, 137.4]}
                      zoom={6}
                      minZoom={0}
                      maxZoom={8}
                      scrollWheelZoom={false}
                      zoomControl={false}
                      attributionControl={false}
                      containerHeight="100%"
                      tileLayers={[
                        {
                          id: "mola_basemap",
                          url: MOLA_BASEMAP_URL,
                          attribution: MOLA_ATTRIBUTION,
                          maxZoom: 8,
                          tileSize: 256,
                          visible: true,
                        },
                      ]}
                      polylines={[
                        {
                          id: "route",
                          positions: route.geometry.coordinates.map(
                            ([lon, lat]) => [lat, lon] as [number, number],
                          ),
                          color: "#E56A3A",
                          weight: 3,
                          opacity: 1,
                          visible: true,
                        },
                      ]}
                      fitBounds={route.geometry.coordinates.map(
                        ([lon, lat]) => [lat, lon] as [number, number],
                      )}
                    />
                  </div>
                  <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
                    <ReportRow label="Strategy" value={route.strategy.replace(/_/g, " ")} />
                    <ReportRow
                      label="Distance"
                      value={`${(route.distance_m / 1000).toFixed(2)} km`}
                    />
                    <ReportRow
                      label="Duration"
                      value={fmtMin(route.estimated_duration_min)}
                    />
                    <ReportRow
                      label="Max slope"
                      value={
                        route.metrics?.max_slope_deg === null ||
                        route.metrics?.max_slope_deg === undefined
                          ? "unavailable"
                          : `${route.metrics.max_slope_deg}°`
                      }
                    />
                  </dl>
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <FeasibilityBadge status={route.feasibility_status} />
                    <span className="text-[10px] text-text-muted">{route.rationale}</span>
                  </div>
                </>
              ) : (
                <p className="text-sm text-text-muted">Route geometry is unavailable.</p>
              )}
            </Panel>

            <Panel title="Terrain analysis">
              {coverage ? (
                <>
                  <div className="space-y-1.5">
                    {(["1", "2", "0"] as const).map((key) => (
                      <div key={key} className="flex items-center justify-between gap-3 text-[11px]">
                        <span className="text-text-secondary">
                          {coverage.classes?.[key] ?? `Coverage class ${key}`}
                        </span>
                        <span className="tabular text-text-primary">
                          {coverage.counts[key] ?? 0} cells ·{" "}
                          {coverage.percentages[key] === undefined
                            ? "—"
                            : `${coverage.percentages[key]}%`}
                        </span>
                      </div>
                    ))}
                  </div>
                  <p className="mt-2 border-t border-line/50 pt-2 text-[10px] leading-relaxed text-text-muted">
                    Class 2 provides elevation only; slope and roughness are never reported as valid
                    there. Uncovered cells stay unavailable, never zero risk.
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <StatusPill tone="observed">MOLA elevation</StatusPill>
                    <StatusPill tone="derived">Derived slope/roughness</StatusPill>
                  </div>
                </>
              ) : (
                <p className="text-sm text-text-muted">
                  Terrain coverage summary unavailable from the backend.
                </p>
              )}
            </Panel>

            <Panel title="Environment · REMS">
              {environment && environment.availability !== "unavailable" ? (
                <>
                  <div className="text-[11px] text-text-muted">
                    Historical in-situ point measurements · Curiosity location ·{" "}
                    {environment.sols?.length
                      ? `sols ${environment.sols[0]}–${environment.sols[environment.sols.length - 1]}`
                      : "sols unavailable"}
                  </div>
                  <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2">
                    {environmentRows(environment).map((row) => (
                      <ReportRow
                        key={`${row.sol}-${row.label}`}
                        label={`${row.label} · sol ${row.sol}`}
                        value={row.value}
                      />
                    ))}
                  </dl>
                  <p className="mt-2 border-t border-line/50 pt-2 text-[10px] leading-relaxed text-text-muted">
                    Not live telemetry, not a forecast, and not spatially distributed across the
                    traverse.
                  </p>
                </>
              ) : (
                <p className="text-sm text-text-muted">
                  REMS data: {environment?.availability?.toUpperCase() ?? "UNAVAILABLE"}
                </p>
              )}
            </Panel>

            <Panel title="Radiation · RAD">
              {radiation && radiation.availability !== "unavailable" ? (
                <>
                  <div className="text-[11px] text-text-muted">
                    Detectors reported separately · {radiation.unit ?? "microGray / Hour"} ·{" "}
                    {radiation.sols?.length ? `sols ${radiation.sols.join(", ")}` : "sols unavailable"}
                  </div>
                  <div className="mt-2 space-y-2">
                    {Object.entries(radiation.detectors ?? {}).map(([key, detector]) => (
                      <div key={key} className="border-t border-line/40 pt-2 first:border-t-0 first:pt-0">
                        <div className="text-[11px] font-medium text-text-primary">
                          Detector {detector.detector || key}
                        </div>
                        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[10px] tabular text-text-secondary">
                          {Object.values(detector.sols ?? {}).map((sol) => (
                            <span key={sol.sol}>
                              Sol {sol.sol}: {sol.mean === null ? "—" : sol.mean.toFixed(3)}{" "}
                              {detector.unit}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="mt-2 border-t border-line/50 pt-2 text-[10px] leading-relaxed text-text-muted">
                    Historical detector point measurements. No route-specific radiation prediction is
                    made.
                  </p>
                </>
              ) : (
                <p className="text-sm text-text-muted">
                  RAD data: {radiation?.availability?.toUpperCase() ?? "UNAVAILABLE"}
                </p>
              )}
            </Panel>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Panel title="Assumptions and warnings">
              {reportMission.assumptions.length > 0 && (
                <>
                  <div className="text-[9px] uppercase tracking-[0.1em] text-text-muted">
                    Assumptions
                  </div>
                  <ul className="mt-1 list-disc space-y-0.5 pl-4 text-[11px] leading-relaxed text-text-secondary">
                    {reportMission.assumptions.slice(0, 4).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </>
              )}
              {warnings.length > 0 && (
                <>
                  <div className="mt-3 text-[9px] uppercase tracking-[0.1em] text-warning-amber">
                    Warnings
                  </div>
                  <ul className="mt-1 list-disc space-y-0.5 pl-4 text-[11px] leading-relaxed text-text-secondary">
                    {warnings.slice(0, 5).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </>
              )}
            </Panel>

            <Panel title="Limitations and data sources">
              {limitations.length > 0 && (
                <ul className="list-disc space-y-0.5 pl-4 text-[11px] leading-relaxed text-text-muted">
                  {limitations.slice(0, 4).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              )}
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line/50 pt-2.5">
                {provenance.map((entry) => (
                  <ProvenanceBadge key={entry} status={entry} />
                ))}
                <span className="text-[10px] text-text-secondary">
                  {dataSource ?? "Backend-derived"}
                </span>
              </div>
            </Panel>
          </div>
        </>
      )}

      <Panel title="Export feedback">
        <div className="flex items-center gap-2 text-sm">
          <FileText size={16} />
          <span>{status ?? "No export yet. Click Export report."}</span>
        </div>
        {report?.generated_at && (
          <div className="mt-1 text-[10px] text-text-muted">
            Report {report.report_id} generated {new Date(report.generated_at).toLocaleString()}
          </div>
        )}
      </Panel>
    </div>
  );
}

async function planDefaultMission(): Promise<MissionPlanResponse> {
  return endpoints.missionPlan({
    region_id: REGION_ID,
    start: { x: DEFAULT_START.lon, y: DEFAULT_START.lat, crs: "urn:ogc:def:crs:IAU2000::104905" },
    destination: { x: DEFAULT_DEST.lon, y: DEFAULT_DEST.lat, crs: "urn:ogc:def:crs:IAU2000::104905" },
    time_limit_min: DEFAULT_TIME_LIMIT,
    exploration_time_min: 30,
    reserve_time_min: 30,
    route_strategy: "balanced",
  });
}



function ReportRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[9px] uppercase tracking-[0.1em] text-text-muted">{label}</dt>
      <dd className="mt-0.5 truncate text-[11px] tabular text-text-secondary" title={value}>
        {value}
      </dd>
    </div>
  );
}

function environmentRows(environment: ReportEnvironment) {
  const rows: Array<{ sol: number; label: string; value: string }> = [];
  for (const [solKey, metrics] of Object.entries(environment.measurements ?? {})) {
    const sol = Number(solKey);
    for (const measurement of Object.values(metrics)) {
      if (measurement.mean === null || measurement.mean === undefined) continue;
      rows.push({
        sol,
        label: measurement.label || measurement.measurement,
        value: `${measurement.mean.toFixed(2)} ${measurement.unit}`,
      });
      if (rows.length >= 4) return rows;
    }
  }
  return rows;
}

function formatCoord(value: MissionPlanResponse["start"] | undefined): string {
  const x = value?.x;
  const y = value?.y;
  if (typeof x !== "number" || typeof y !== "number") return "unavailable";
  return `${x.toFixed(3)}°, ${y.toFixed(3)}°`;
}

function fmtMin(value: number | null | undefined): string {
  return value === null || value === undefined ? "unavailable" : `${value} min`;
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

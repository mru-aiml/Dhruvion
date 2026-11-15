import { useState } from "react";
import { Download, FileText } from "lucide-react";
import { MapContainer, TileLayer, Polyline } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const MarsCRS = L.extend({}, L.CRS, {
  code: "Mars:Equirectangular",
  projection: L.Projection.LonLat,
  transformation: new L.Transformation(1 / 180, 1, -1 / 180, 0.5),
}) as unknown as L.CRS;
import Panel from "../../components/common/Panel";
import { endpoints } from "../../services/api/endpoints";
import { pushNotification } from "../../utils/notifications";
import { apiErrorMessage } from "../../services/api/client";
import { SimulatedLabel, ProvenanceBadge } from "../../components/common/StatusBadge";

export default function ReportsPage() {
  const [status, setStatus] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const exportReport = async () => {
    setExporting(true);
    setError(null);
    try {
      const res = await endpoints.report({ mission_id: null, format: "json" });
      if (res.download_url) {
        const base = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api").replace(/\/api\/?$/, "");
        const link = document.createElement("a");
        link.href = base + res.download_url;
        link.download = `dhruvion-report-${res.report_id}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
      setStatus(`Report ${res.report_id} · ${res.status}`);
      pushNotification(`Mission report exported: ${res.report_id}`, "/reports");
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Mission Reports</h1>
          <p className="text-xs text-text-muted">Traceable mission summary</p>
        </div>
        <button onClick={exportReport} disabled={exporting} className="px-3 py-1.5 rounded-md bg-mars-orange text-white text-sm font-medium flex items-center gap-2">
          <Download size={14} /> {exporting ? "Exporting…" : "Export report"}
        </button>
      </div>

      {error && <div className="text-xs text-critical-red">{error} — showing simulated report.</div>}
      {status && <div className="text-xs text-text-secondary">{status}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel title="Mission objectives">
          <ul className="text-sm list-disc pl-4 text-text-secondary">
            <li>Traverse to Mount Sharp Outcrop and collect geological observations.</li>
            <li>Evaluate route feasibility within 240 min budget.</li>
          </ul>
        </Panel>
        <Panel title="Selected exploration region">
          <div className="text-sm">Gale Crater, Mars · configured Mars CRS (prototype)</div>
          <div className="text-xs text-text-muted mt-1">Availability: PARTIAL (SIMULATED)</div>
        </Panel>
        <Panel title="Route summary">
          <div className="h-32 rounded-md overflow-hidden border border-line mb-2">
            <MapContainer crs={MarsCRS} center={[-5.4, 137.4]} zoom={6} style={{ height: "100%", width: "100%", background: "#1a1510" }} zoomControl={false} attributionControl={false}>
              <TileLayer url="https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg" tileSize={256} maxZoom={8} />
              <Polyline positions={[[-5.45, 137.35], [-5.44, 137.37], [-5.42, 137.39], [-5.40, 137.41], [-5.38, 137.42]]} pathOptions={{ color: "#E56A3A", weight: 3 }} />
            </MapContainer>
          </div>
          <div className="text-sm">Strategy: Balanced · Distance: 3.05 km · Duration: 41 min (SIMULATED)</div>
          <div className="text-xs text-text-muted mt-1">Feasibility: FEASIBLE · SIMULATED geometry</div>
        </Panel>
        <Panel title="Terrain analysis">
          <div className="text-sm">Elevation: unavailable · Slope: unavailable · Roughness: unavailable</div>
          <div className="text-xs text-text-muted mt-1">Marked unavailable; not treated as low risk.</div>
        </Panel>
        <Panel title="Science targets visited">
          <div className="text-sm">Mount Sharp Outcrop (planned) · Channel Floor Deposit (visited, simulated)</div>
        </Panel>
        <Panel title="Estimated distance and duration">
          <div className="text-sm">Outbound 41 + Exploration 30 + Return 46 + Reserve 30 = 147 min ≤ 240 min</div>
        </Panel>
        <Panel title="Hazards encountered">
          <div className="text-sm">1 identified (SIMULATED) · No observed hazard data loaded.</div>
        </Panel>
        <Panel title="Emergency rerouting history">
          <div className="text-sm">Simulated blocked route scenario available on Emergency Navigation screen.</div>
        </Panel>
        <Panel title="Data sources used">
          <div className="flex flex-wrap gap-2">
            <ProvenanceBadge status="simulated" />
            <span className="text-xs text-text-secondary">Simulated catalog · Prototype visualization</span>
          </div>
        </Panel>
      </div>

      <Panel title="Export feedback">
        <div className="flex items-center gap-2 text-sm">
          <FileText size={16} />
          <span>{status ?? "No export yet. Click Export report."}</span>
          <SimulatedLabel />
        </div>
      </Panel>
    </div>
  );
}

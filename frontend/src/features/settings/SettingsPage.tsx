import { useEffect, useState } from "react";
import Panel from "../../components/common/Panel";

const DEFAULTS = { units: "metric", coordFormat: "xy", showSimLabels: true, reducedMotion: false };

export default function SettingsPage() {
  const [units, setUnits] = useState(DEFAULTS.units);
  const [coordFormat, setCoordFormat] = useState(DEFAULTS.coordFormat);
  const [showSimLabels, setShowSimLabels] = useState(DEFAULTS.showSimLabels);
  const [reducedMotion, setReducedMotion] = useState(DEFAULTS.reducedMotion);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("dhruvion.settings");
      if (raw) {
        const parsed = JSON.parse(raw);
        setUnits(parsed.units ?? DEFAULTS.units);
        setCoordFormat(parsed.coordFormat ?? DEFAULTS.coordFormat);
        setShowSimLabels(parsed.showSimLabels ?? DEFAULTS.showSimLabels);
        setReducedMotion(parsed.reducedMotion ?? DEFAULTS.reducedMotion);
      }
    } catch { /* ignore */ }
  }, []);

  const save = () => {
    localStorage.setItem("dhruvion.settings", JSON.stringify({ units, coordFormat, showSimLabels, reducedMotion }));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const reset = () => {
    setUnits(DEFAULTS.units);
    setCoordFormat(DEFAULTS.coordFormat);
    setShowSimLabels(DEFAULTS.showSimLabels);
    setReducedMotion(DEFAULTS.reducedMotion);
    localStorage.removeItem("dhruvion.settings");
  };

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Settings</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel title="Display preferences">
          <Toggle label="Show simulated labels" value={showSimLabels} onChange={setShowSimLabels} />
          <Toggle label="Respect reduced motion" value={reducedMotion} onChange={setReducedMotion} />
        </Panel>
        <Panel title="Units and coordinates">
          <div className="space-y-3">
            <div>
              <label className="text-micro text-text-muted">Units</label>
              <select value={units} onChange={(e) => setUnits(e.target.value)} className="mt-1 w-full bg-surface2 border border-line rounded-md px-2 py-1.5 text-sm">
                <option value="metric">Metric (m, km, min)</option>
                <option value="imperial">Imperial (ft, mi)</option>
              </select>
            </div>
            <div>
              <label className="text-micro text-text-muted">Coordinate format</label>
              <select value={coordFormat} onChange={(e) => setCoordFormat(e.target.value)} className="mt-1 w-full bg-surface2 border border-line rounded-md px-2 py-1.5 text-sm">
                <option value="xy">x, y (prototype grid)</option>
                <option value="latlon">Latitude, Longitude</option>
              </select>
            </div>
          </div>
        </Panel>
        <Panel title="Data / source preferences">
          <p className="text-sm text-text-secondary">
            Layer availability is determined by backend dataset catalog. Unavailable layers remain disabled. No controls for unsupported features are exposed.
          </p>
        </Panel>
        <div className="flex gap-2">
          <button onClick={save} className="px-4 py-2 rounded-md bg-mars-orange text-white text-sm font-medium">Save settings</button>
          <button onClick={reset} className="px-4 py-2 rounded-md border border-line text-sm hover:bg-surface2">Reset defaults</button>
          {saved && <span className="text-sm text-safe-green self-center">Saved</span>}
        </div>
      </div>
    </div>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-line/40 last:border-0">
      <span className="text-sm">{label}</span>
      <button
        onClick={() => onChange(!value)}
        className={`w-10 h-5 rounded-full border transition-colors ${value ? "bg-mars-orange border-mars-orange" : "bg-surface3 border-line"}`}
        aria-pressed={value}
      >
        <span className={`block w-4 h-4 rounded-full bg-white transform transition-transform ${value ? "translate-x-5" : "translate-x-0.5"}`} />
      </button>
    </div>
  );
}

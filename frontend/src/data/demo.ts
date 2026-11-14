// Simulated demo data used only when backend data is unavailable.
// All values here are labelled SIMULATED in the UI.

import type { LayerMeta, ScienceTarget, Region } from "../types";

export const DEMO_REGION: Region = {
  id: "gale_crater",
  name: "Gale Crater",
  body: "Mars",
  crs: "configured Mars CRS (prototype)",
  availability: "partial",
};

export const DEMO_LAYERS: LayerMeta[] = [
  { id: "optical_imagery", name: "Optical Imagery", layer_type: "raster", status: "observed", availability: "unavailable", units: null, warnings: ["No verified source loaded."] },
  { id: "mola_elevation", name: "Elevation / MOLA", layer_type: "raster", status: "observed", availability: "unavailable", units: "m", warnings: ["No verified source loaded."] },
  { id: "slope", name: "Slope Analysis", layer_type: "derived", status: "derived", availability: "unavailable", units: "deg", warnings: ["Derived from elevation; source unavailable."] },
  { id: "roughness", name: "Terrain Roughness", layer_type: "derived", status: "derived", availability: "unavailable", units: "index", warnings: ["Derived from elevation; source unavailable."] },
  { id: "themis_thermal", name: "THEMIS Thermal", layer_type: "raster", status: "observed", availability: "unavailable", units: "K", warnings: ["Optional extension; not loaded."] },
  { id: "science_targets", name: "Science Targets", layer_type: "vector", status: "simulated", availability: "partial", units: null, warnings: ["Simulated target set for demo."] },
  { id: "hazard_overlay", name: "Hazard Overlay", layer_type: "derived", status: "derived", availability: "unavailable", units: null, warnings: ["No hazard source loaded."] },
];

export const DEMO_TARGETS: ScienceTarget[] = [
  {
    id: "t1", name: "Mount Sharp Outcrop", feature_type: "sedimentary outcrop", geometry: { type: "Point", coordinates: [137.42, -5.38] },
    coordinate_crs: "prototype grid", priority: 0.9, description: "Layered sedimentary rock exposure.",
    interpretation: "May record ancient aqueous environments (interpretation).", provenance: ["simulated"], warnings: ["Simulated target."],
    distance_m: 1200, source_name: "Simulated catalog", visited: false,
  },
  {
    id: "t2", name: "Crater Rim Ridge", feature_type: "ridge", geometry: { type: "Point", coordinates: [137.55, -5.25] },
    coordinate_crs: "prototype grid", priority: 0.7, description: "Elevated rim segment.",
    interpretation: null, provenance: ["simulated"], warnings: ["Simulated target."],
    distance_m: 2400, source_name: "Simulated catalog", visited: false,
  },
  {
    id: "t3", name: "Channel Floor Deposit", feature_type: "channel deposit", geometry: { type: "Point", coordinates: [137.30, -5.52] },
    coordinate_crs: "prototype grid", priority: 0.6, description: "Fine-grained channel fill.",
    interpretation: "Possible fluvial origin (interpretation).", provenance: ["simulated"], warnings: ["Simulated target."],
    distance_m: 1800, source_name: "Simulated catalog", visited: true,
  },
];

export const DEMO_ROUTE_COORDS: [number, number][] = [
  [137.35, -5.45], [137.38, -5.42], [137.40, -5.40], [137.42, -5.38], [137.44, -5.36], [137.46, -5.34],
];

export const DEMO_TIMELINE = [
  { time: "08:12", event: "Mission plan drafted", category: "Planning", status: "completed" },
  { time: "08:45", event: "Route candidates calculated", category: "Route", status: "completed" },
  { time: "09:05", event: "Terrain layer review", category: "Terrain", status: "in progress" },
  { time: "09:30", event: "Science target selected", category: "Science", status: "planned" },
];

export const DEMO_ALERTS = [
  { severity: "Caution", message: "Slope data unavailable for north sector.", time: "09:10" },
  { severity: "Info", message: "Science target catalog is simulated.", time: "09:12" },
];

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  FlaskConical,
  Layers,
  Menu,
  Mountain,
  Play,
  Route as RouteIcon,
  Satellite,
  Siren,
  X,
} from "lucide-react";

type ViewId = "Mars Globe" | "Terrain" | "Elevation" | "Mission Data";
type VideoStatus = "loading" | "playing" | "poster" | "autoplay-blocked" | "error";
type DataStatus = "OBSERVED" | "DERIVED" | "SIMULATED" | "UNAVAILABLE";
type DisplayStatus = DataStatus | "LOADING";
type AssetStatus = "loading" | "loaded" | "error";

const TERRAIN_ASSET = "/assets/gale-ctx-mosaic.jpg";
const ELEVATION_ASSET = "/assets/gale-elevation-relief.jpg";

// Metadata mirrors scripts/build_landing_assets.py (NASA Mars Trek z8 mosaic).
const TERRAIN_META = {
  coverage: "135.18–139.22°E · 3.52–6.33°S",
  zoom: "8",
  resolution: "162.8 m/px",
  scaleBarWidth: "20.9%",
  scaleBarLabel: "50 km",
  widthKm: "239 km",
};

// Metadata mirrors the local MOLA MEGDR processing (NoData = 0 excluded).
const ELEVATION_META = {
  coverage: "135.5–139.5°E · 4.2–6.8°S",
  min: "−4,648 m",
  max: "+1,412 m",
  resolution: "463.06 m/px",
  scaleBarWidth: "20.8%",
  scaleBarLabel: "50 km",
};

const VIEWS: ViewId[] = ["Mars Globe", "Terrain", "Elevation", "Mission Data"];

type ViewConfig = {
  id: ViewId;
  label: string;
  title: string;
  description: string;
  status: DataStatus;
  rows: Array<[string, string]>;
  attribution: string;
  footnote: string;
};

const VIEW_CONFIG: Record<ViewId, ViewConfig> = {
  "Mars Globe": {
    id: "Mars Globe",
    label: "Mars Globe",
    title: "MARS GLOBE",
    description:
      "NASA Solar System Visualization of Mars rotating about its own axis, framed on the Gale Crater mission region. This is recorded planetary imagery, not live footage.",
    status: "OBSERVED",
    rows: [
      ["Region", "Gale Crater · 5.4°S, 137.8°E"],
      ["Planet radius", "3,390 km"],
      ["Surface gravity", "3.71 m/s²"],
      ["Visualization", "NASA SVS 30338"],
    ],
    attribution: "NASA SVS / JPL · public-domain visualization · not live footage",
    footnote: "NASA visualization · not live footage",
  },
  Terrain: {
    id: "Terrain",
    label: "Terrain",
    title: "SURFACE TERRAIN",
    description:
      "Observed CTX orbital imagery of Gale Crater and Aeolis Mons, composited from NASA Mars Trek tiles. This is panchromatic surface imagery, not a synthetic render or a chart.",
    status: "OBSERVED",
    rows: [
      ["Source", "CTX Block Adjacency mosaic"],
      ["Provider", "NASA Mars Trek / JPL"],
      ["Coverage", TERRAIN_META.coverage],
      ["Mosaic zoom", `${TERRAIN_META.zoom} · ${TERRAIN_META.resolution}`],
      ["Region width", TERRAIN_META.widthKm],
    ],
    attribution:
      "NASA Mars Trek · Gale_CTX_BlockAdj_dd · panchromatic CTX mosaic · display tint only",
    footnote: "NASA Mars Trek · observed CTX imagery",
  },
  Elevation: {
    id: "Elevation",
    label: "Elevation",
    title: "ELEVATION MODEL",
    description:
      "Hypsometric relief rendered from the project's local MOLA MEGDR crop. Elevation values are metres relative to the Mars datum; the 0 m NoData sentinel is excluded, never treated as zero elevation.",
    status: "DERIVED",
    rows: [
      ["Source", "MGS MOLA MEGDR (128 px/deg)"],
      ["Coverage", ELEVATION_META.coverage],
      ["Elevation", `${ELEVATION_META.min} to ${ELEVATION_META.max}`],
      ["Pixel size", ELEVATION_META.resolution],
      ["No-data", "0 m sentinel excluded"],
    ],
    attribution:
      "MGS MOLA MEGDR · NASA PDS Geosciences · hillshade and colour ramp are derived",
    footnote: "MOLA · derived rendering · not a raw plot",
  },
  "Mission Data": {
    id: "Mission Data",
    label: "Mission Data",
    title: "MISSION DATA",
    description:
      "Mission context for the Gale Crater prototype region. Science-target and hazard catalogues are not connected in this build, so they are reported as unavailable rather than estimated.",
    status: "SIMULATED",
    rows: [
      ["Region", "Gale Crater"],
      ["Objective", "Geological sampling"],
      ["Terrain layers", "8 available · 2 derived"],
      ["Science targets", "UNAVAILABLE"],
      ["Hazard catalogue", "UNAVAILABLE"],
      ["Route planning", "SIMULATED"],
    ],
    attribution:
      "Route candidates are simulated decision support, not certified traverse plans",
    footnote: "Static mission context · not live telemetry",
  },
};

const STATUS_TONE: Record<DisplayStatus, string> = {
  OBSERVED: "text-safe-green",
  DERIVED: "text-amber",
  SIMULATED: "text-cyan",
  UNAVAILABLE: "text-text-muted",
  LOADING: "text-warning-amber",
};

const VIDEO_LABEL: Record<VideoStatus, string> = {
  loading: "LOADING ROTATION…",
  playing: "NASA SVS · ROTATING MARS",
  poster: "POSTER FRAME",
  "autoplay-blocked": "AUTOPLAY BLOCKED · POSTER",
  error: "ANIMATION UNAVAILABLE · POSTER",
};

const NAV_ITEMS = [
  { id: "overview", label: "OVERVIEW" },
  { id: "capabilities", label: "CAPABILITIES" },
  { id: "how", label: "HOW IT WORKS" },
  { id: "technology", label: "TECHNOLOGY" },
  { id: "about", label: "ABOUT" },
];

const CAPABILITIES = [
  {
    label: "01 / TERRAIN",
    title: "Terrain Intelligence",
    description:
      "Explore elevation, slope and roughness derived from MOLA data, with NASA Mars Trek basemaps for regional context.",
    to: "/map",
    icon: Mountain,
  },
  {
    label: "02 / ROUTES",
    title: "Intelligent Route Planning",
    description:
      "Compare shortest, balanced and lowest-estimated-risk route candidates across the Gale Crater traverse region.",
    to: "/routes",
    icon: RouteIcon,
  },
  {
    label: "03 / SCIENCE",
    title: "Science Exploration",
    description:
      "Discover and evaluate potential geological science targets, then inspect the evidence behind each candidate.",
    to: "/science",
    icon: FlaskConical,
  },
  {
    label: "04 / EMERGENCY",
    title: "Emergency Navigation",
    description:
      "Explore simulated emergency rerouting scenarios when a planned traverse is obstructed.",
    to: "/emergency",
    icon: Siren,
  },
];

const WORKFLOW = [
  {
    step: "STEP 01",
    title: "Explore Martian Terrain",
    description:
      "Open the Gale Crater map and inspect NASA basemaps alongside local MOLA layers.",
  },
  {
    step: "STEP 02",
    title: "Analyze Terrain Conditions",
    description:
      "Read elevation, derived slope and roughness to understand traverse constraints.",
  },
  {
    step: "STEP 03",
    title: "Plan Mission Routes",
    description:
      "Compare shortest, balanced and safest-estimated route candidates on the same map.",
  },
  {
    step: "STEP 04",
    title: "Review Mission Decisions",
    description:
      "Check round-trip feasibility, hazard availability and simulated obstruction responses.",
  },
];

const TECH_GROUPS = [
  {
    label: "DATA SOURCES",
    icon: Satellite,
    items: ["NASA Mars Trek WMTS", "MGS MOLA MEGDR", "Derived slope and roughness"],
  },
  {
    label: "APPLICATION STACK",
    icon: Layers,
    items: ["React", "TypeScript", "Vite", "Tailwind CSS", "FastAPI"],
  },
  {
    label: "GEOSPATIAL PROCESSING",
    icon: Mountain,
    items: [
      "Local MOLA raster crops",
      "Slope and roughness derivation",
      "A* traversability search (limited coverage)",
    ],
  },
];

const DATA_STATES: Array<{ state: DataStatus; note: string }> = [
  { state: "OBSERVED", note: "Measured or recorded source data" },
  { state: "DERIVED", note: "Computed from observed layers" },
  { state: "SIMULATED", note: "Scenario or decision-support output" },
  { state: "UNAVAILABLE", note: "Not connected or outside coverage" },
];

function SectionHeading({ index, label }: { index: string; label: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-micro text-mars-orange">{index}</span>
      <span aria-hidden className="h-px w-8 bg-line" />
      <span className="text-micro text-text-muted">{label}</span>
    </div>
  );
}

function TelemetryPanel({
  view,
  status,
  statusNote,
}: {
  view: ViewConfig;
  status: DisplayStatus;
  statusNote?: string;
}) {
  return (
    <div className="panel w-full p-5">
      <div className="flex items-center justify-between gap-3">
        <span className="text-micro text-mars-orange">{view.title}</span>
        <span className={`text-micro ${STATUS_TONE[status]}`}>{status}</span>
      </div>
      {statusNote && (
        <p className="mt-2 border-l border-warning-amber/50 pl-2 text-[10px] leading-relaxed text-warning-amber/90">
          {statusNote}
        </p>
      )}
      <p className="mt-3 text-xs leading-relaxed text-text-secondary">
        {view.description}
      </p>
      <dl className="mt-4 space-y-2 border-t border-line/60 pt-3">
        {view.rows.map(([label, value]) => (
          <div key={label} className="flex items-start justify-between gap-4">
            <dt className="text-micro shrink-0 text-text-muted">{label}</dt>
            <dd className="text-right text-[11px] leading-snug text-text-secondary">
              {value}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 text-micro leading-relaxed text-text-muted normal-case tracking-normal">
        {view.attribution}
      </p>
    </div>
  );
}

function UnavailableView({ label }: { label: string }) {
  return (
    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 bg-[#120e0b] px-8 text-center">
      <span className="text-micro text-warning-amber">DATA UNAVAILABLE</span>
      <p className="max-w-xs text-[11px] leading-relaxed text-text-secondary">{label}</p>
    </div>
  );
}

function StatusChip({ status, note }: { status: DisplayStatus; note: string }) {
  return (
    <div className="inline-flex items-center gap-2 border border-line/80 bg-black/55 px-2 py-1 backdrop-blur-sm">
      <span
        aria-hidden
        className={`h-1.5 w-1.5 rounded-full ${
          status === "OBSERVED"
            ? "bg-safe-green"
            : status === "DERIVED"
              ? "bg-amber"
              : status === "SIMULATED"
                ? "bg-cyan"
                : status === "LOADING"
                  ? "bg-warning-amber"
                  : "bg-text-muted"
        }`}
      />
      <span className={`text-micro ${STATUS_TONE[status]}`}>{status}</span>
      <span aria-hidden className="h-2.5 w-px bg-line/80" />
      <span className="text-micro text-text-secondary">{note}</span>
    </div>
  );
}

function HudCorners({ tone = "border-mars-orange/60" }: { tone?: string }) {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-2 z-20">
      <span className={`absolute left-0 top-0 h-5 w-5 border-l border-t ${tone}`} />
      <span className={`absolute right-0 top-0 h-5 w-5 border-r border-t ${tone}`} />
      <span className={`absolute bottom-0 left-0 h-5 w-5 border-l border-b ${tone}`} />
      <span className={`absolute bottom-0 right-0 h-5 w-5 border-r border-b ${tone}`} />
    </div>
  );
}

function ScaleBar({
  width,
  label,
  className = "",
}: {
  width: string;
  label: string;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <div
        aria-hidden
        className="h-[5px] border-x border-b border-text-primary/80"
        style={{ width }}
      />
      <span className="text-micro leading-none text-text-primary/80">{label}</span>
    </div>
  );
}

function MissionDashboard({
  reliefFailed,
  onReliefError,
}: {
  reliefFailed: boolean;
  onReliefError: () => void;
}) {
  const modules: Array<{
    label: string;
    value: string;
    status: DisplayStatus;
    detail: string;
  }> = [
    {
      label: "MISSION REGION",
      value: "Gale Crater",
      status: "OBSERVED",
      detail: "5.4°S · 137.8°E",
    },
    {
      label: "MISSION OBJECTIVE",
      value: "Geological sampling",
      status: "SIMULATED",
      detail: "Traverse planning · prototype",
    },
    {
      label: "TERRAIN LAYERS",
      value: "8 available",
      status: "OBSERVED",
      detail: "5 basemaps · MOLA + 2 derived",
    },
    {
      label: "SCIENCE TARGETS",
      value: "Not connected",
      status: "UNAVAILABLE",
      detail: "No catalogue loaded",
    },
    {
      label: "HAZARD DATA",
      value: "Not connected",
      status: "UNAVAILABLE",
      detail: "No hazard catalogue loaded",
    },
    {
      label: "ROUTE PLANNING",
      value: "Simulated",
      status: "SIMULATED",
      detail: "A* limited to MOLA coverage",
    },
  ];

  return (
    <div className="hero-visual-in absolute inset-0 flex flex-col bg-[#0b0806]">
      <div className="flex items-center justify-between gap-3 border-b border-line/70 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-mars-orange" />
          <span className="text-micro text-text-primary">GALE CRATER / MISSION CONTROL</span>
        </div>
        <span className="text-micro text-cyan">SIMULATED · MIXED</span>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[0.92fr_1.08fr] gap-3 p-3">
        {/* Region map module */}
        <div className="relative min-h-0 overflow-hidden border border-line/70 bg-[#120d09]">
          {!reliefFailed ? (
            <img
              src={ELEVATION_ASSET}
              alt="MOLA hypsometric relief used as the Gale Crater mission-region context map"
              className="absolute inset-0 h-full w-full object-cover opacity-70"
              loading="lazy"
              onError={onReliefError}
            />
          ) : (
            <div aria-hidden className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,#4a1b18,#120d09_70%)]" />
          )}
          <div aria-hidden className="absolute inset-0 bg-[#0b0806]/35" />
          <div
            aria-hidden
            className="absolute inset-0 opacity-40"
            style={{
              backgroundImage:
                "linear-gradient(to right, rgba(240,107,61,0.22) 1px, transparent 1px), linear-gradient(to bottom, rgba(240,107,61,0.22) 1px, transparent 1px)",
              backgroundSize: "32px 32px",
            }}
          />
          <div
            aria-hidden
            className="absolute left-1/2 top-1/2 h-24 w-24 -translate-x-1/2 -translate-y-1/2 rounded-full border border-mars-orange/40"
          />
          <div
            aria-hidden
            className="absolute left-1/2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-mars-orange shadow-[0_0_16px_rgba(240,107,61,0.9)]"
          />
          <span aria-hidden className="absolute left-1/2 top-1/2 h-px w-32 -translate-x-1/2 bg-mars-orange/40" />
          <span aria-hidden className="absolute left-1/2 top-1/2 h-32 w-px -translate-y-1/2 bg-mars-orange/40" />

          <div className="absolute left-2 top-2">
            <StatusChip status="OBSERVED" note="MOLA RELIEF" />
          </div>
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/85 to-transparent px-3 pb-2.5 pt-8">
            <div className="text-micro text-mars-orange">MISSION REGION</div>
            <div className="mt-0.5 font-heading text-sm tracking-[0.16em]">GALE CRATER</div>
            <div className="text-micro text-text-secondary">5.4°S · 137.8°E · AEOLIS MONS</div>
          </div>
          <span aria-hidden className="absolute right-2 top-2 text-micro text-text-secondary/80">
            02
          </span>
        </div>

        {/* Data modules */}
        <div className="grid min-h-0 grid-cols-2 grid-rows-3 gap-2">
          {modules.map((module) => (
            <div
              key={module.label}
              className="flex min-w-0 flex-col justify-between border border-line/60 bg-surface1/80 p-1.5 sm:p-2"
            >
              <div className="flex items-start justify-between gap-1">
                <span className="min-w-0 break-words text-[8px] font-medium uppercase leading-tight tracking-[0.06em] text-text-muted sm:text-micro sm:tracking-[0.12em]">
                  {module.label}
                </span>
                <span
                  aria-hidden
                  className={`mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                    module.status === "OBSERVED"
                      ? "bg-safe-green"
                      : module.status === "DERIVED"
                        ? "bg-amber"
                        : module.status === "SIMULATED"
                          ? "bg-cyan"
                          : "bg-text-muted"
                  }`}
                />
              </div>
              <div className="min-w-0">
                <div
                  className={`truncate font-heading text-[12px] leading-tight sm:text-[13px] ${
                    module.status === "UNAVAILABLE" ? "text-text-muted" : "text-text-primary"
                  }`}
                >
                  {module.value}
                </div>
                <div className="mt-0.5 hidden truncate text-[9px] leading-tight text-text-secondary sm:block">
                  {module.detail}
                </div>
              </div>
              <div
                className={`truncate text-[8px] tracking-[0.06em] sm:text-[9px] sm:tracking-[0.1em] ${STATUS_TONE[module.status]}`}
              >
                {module.status}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line/70 px-4 py-2">
        <div className="flex flex-wrap items-center gap-3">
          {(["OBSERVED", "DERIVED", "SIMULATED", "UNAVAILABLE"] as DataStatus[]).map(
            (state) => (
              <span key={state} className="inline-flex items-center gap-1">
                <span
                  aria-hidden
                  className={`h-1 w-1 rounded-full ${
                    state === "OBSERVED"
                      ? "bg-safe-green"
                      : state === "DERIVED"
                        ? "bg-amber"
                        : state === "SIMULATED"
                          ? "bg-cyan"
                          : "bg-text-muted"
                  }`}
                />
                <span className={`text-[9px] tracking-[0.1em] ${STATUS_TONE[state]}`}>
                  {state}
                </span>
              </span>
            ),
          )}
        </div>
        <span className="text-[9px] tracking-[0.1em] text-text-muted">
          STATIC CONTEXT · NOT LIVE TELEMETRY
        </span>
      </div>
      <HudCorners tone="border-mars-orange/45" />
    </div>
  );
}

export default function LandingPage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [selectedView, setSelectedView] = useState<ViewId>("Mars Globe");
  const [terrainStatus, setTerrainStatus] = useState<AssetStatus>("loading");
  const [elevationStatus, setElevationStatus] = useState<AssetStatus>("loading");
  const [reliefFailed, setReliefFailed] = useState(false);
  const [videoFailed, setVideoFailed] = useState(false);
  const [videoStatus, setVideoStatus] = useState<VideoStatus>("loading");
  const [activeSection, setActiveSection] = useState("overview");
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActiveSection(entry.target.id);
        });
      },
      { rootMargin: "-45% 0px -50% 0px", threshold: 0 },
    );
    NAV_ITEMS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (selectedView !== "Mars Globe" || reduceMotion || videoFailed) return;
    const video = videoRef.current;
    if (!video) return;
    setVideoStatus("loading");
    const attempt = video.play();
    if (attempt && typeof attempt.catch === "function") {
      attempt.catch(() => setVideoStatus("autoplay-blocked"));
    }
  }, [selectedView, reduceMotion, videoFailed]);

  const scrollTo = useCallback(
    (id: string) => {
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({
          behavior: reduceMotion ? "auto" : "smooth",
          block: "start",
        });
      }
    },
    [reduceMotion],
  );

  const goToSection = (id: string) => {
    setMobileOpen(false);
    scrollTo(id);
  };

  const view = VIEW_CONFIG[selectedView];

  const stageStyle: CSSProperties = {
    height: "var(--stage-h)",
  };

  const globeStyle: CSSProperties = {
    width: "var(--globe)",
    height: "var(--globe)",
  };

  const panelStyle: CSSProperties = {
    width: "min(100%, calc(var(--stage-h) * 1.5))",
    height: "var(--stage-h)",
  };

  const globeWordStyle: CSSProperties = {
    fontSize: "min(calc(var(--globe) * 0.58), 24vw)",
    letterSpacing: "0.14em",
    marginRight: "-0.14em",
    color: "rgba(150, 145, 140, 0.17)",
    fontFamily: '"Space Grotesk", Inter, system-ui, sans-serif',
  };

  const videoLabel = reduceMotion
    ? "REDUCED MOTION · POSTER"
    : VIDEO_LABEL[videoStatus];

  const terrainDisplay: DisplayStatus =
    terrainStatus === "loaded"
      ? "OBSERVED"
      : terrainStatus === "loading"
        ? "LOADING"
        : "UNAVAILABLE";
  const elevationDisplay: DisplayStatus =
    elevationStatus === "loaded"
      ? "DERIVED"
      : elevationStatus === "loading"
        ? "LOADING"
        : "UNAVAILABLE";

  const activeStatus: DisplayStatus =
    selectedView === "Mars Globe"
      ? "OBSERVED"
      : selectedView === "Terrain"
        ? terrainDisplay
        : selectedView === "Elevation"
          ? elevationDisplay
          : "SIMULATED";

  const statusNote =
    selectedView === "Terrain" && terrainStatus === "error"
      ? "CTX mosaic asset could not be loaded."
      : selectedView === "Elevation" && elevationStatus === "error"
        ? "Derived MOLA relief asset could not be loaded."
        : undefined;

  return (
    <div className="min-h-screen bg-canvas text-text-primary">
      {/* ---------------------------------------------------------------- */}
      {/* Global navigation                                                */}
      {/* ---------------------------------------------------------------- */}
      <header className="sticky top-0 z-40 border-b border-line bg-canvas/85 backdrop-blur">
        <div className="lp-container flex h-16 items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-2.5" aria-label="DHRUVION home">
            <span className="flex h-7 w-7 items-center justify-center border border-mars-orange/70 text-xs font-bold text-mars-orange">
              D
            </span>
            <span className="font-heading text-sm tracking-[0.22em]">DHRUVION</span>
          </Link>

          <nav
            aria-label="Landing page sections"
            className="hidden items-center gap-5 lg:flex xl:gap-6"
          >
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => scrollTo(item.id)}
                aria-current={activeSection === item.id ? "true" : undefined}
                className={`text-[11px] tracking-[0.14em] transition-colors ${
                  activeSection === item.id
                    ? "text-mars-orange"
                    : "text-text-secondary hover:text-text-primary"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="hidden items-center gap-4 lg:flex">
            <Link
              to="/login"
              className="text-[11px] tracking-[0.14em] text-text-secondary transition-colors hover:text-text-primary"
            >
              SIGN IN
            </Link>
            <Link
              to="/overview"
              className="border border-mars-orange px-4 py-2 text-[11px] font-medium tracking-[0.12em] text-mars-orange transition-colors hover:bg-mars-orange hover:text-canvas"
            >
              LAUNCH MISSION CONTROL
            </Link>
          </div>

          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center border border-line text-text-secondary transition-colors hover:border-mars-orange/70 hover:text-text-primary lg:hidden"
            onClick={() => setMobileOpen((open) => !open)}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileOpen}
            aria-controls="landing-mobile-menu"
          >
            {mobileOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>

        {mobileOpen && (
          <div
            id="landing-mobile-menu"
            className="border-t border-line bg-surface1 lg:hidden"
          >
            <nav
              aria-label="Landing page sections"
              className="lp-container flex flex-col py-3"
            >
              {NAV_ITEMS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => goToSection(item.id)}
                  className="border-b border-line/60 py-3 text-left text-sm text-text-secondary last:border-b-0 hover:text-text-primary"
                >
                  {item.label}
                </button>
              ))}
              <div className="mt-4 flex flex-col gap-2 pb-3">
                <Link
                  to="/login"
                  onClick={() => setMobileOpen(false)}
                  className="border border-line px-4 py-2.5 text-center text-xs text-text-secondary"
                >
                  SIGN IN
                </Link>
                <Link
                  to="/overview"
                  onClick={() => setMobileOpen(false)}
                  className="border border-mars-orange px-4 py-2.5 text-center text-xs font-medium text-mars-orange"
                >
                  LAUNCH MISSION CONTROL
                </Link>
              </div>
            </nav>
          </div>
        )}
      </header>

      {/* ---------------------------------------------------------------- */}
      {/* Hero — Mars HUD                                                  */}
      {/* ---------------------------------------------------------------- */}
      <section
        aria-labelledby="landing-hero-title"
        data-hero
        className="lp-hero relative isolate overflow-hidden border-b border-line bg-[#050505]"
      >
        <div aria-hidden className="absolute inset-0 starfield opacity-70" />
        <div
          aria-hidden
          className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_45%,rgba(240,107,61,0.10),transparent_58%)]"
        />

        {/* HUD corner brackets */}
        <div aria-hidden className="absolute left-4 top-4 z-20 h-8 w-8 border-l border-t border-mars-orange/60" />
        <div aria-hidden className="absolute right-4 top-4 z-20 h-8 w-8 border-r border-t border-mars-orange/60" />
        <div aria-hidden className="absolute bottom-4 left-4 z-20 h-8 w-8 border-l border-b border-mars-orange/60" />
        <div aria-hidden className="absolute bottom-4 right-4 z-20 h-8 w-8 border-r border-b border-mars-orange/60" />

        <h1 id="landing-hero-title" className="sr-only">
          DHRUVION — Navigate Mars. Understand the Terrain. Protect Every Mission.
        </h1>

        <div className="lp-container relative py-8 lg:py-10">
          {/* Compact tab group below the desktop breakpoint */}
          <div
            role="group"
            aria-label="Hero visualization"
            className="mb-8 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:hidden"
          >
            {VIEWS.map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => setSelectedView(id)}
                aria-pressed={selectedView === id}
                className={`border px-2 py-2.5 text-[11px] tracking-[0.08em] transition-colors ${
                  selectedView === id
                    ? "border-mars-orange bg-mars-orange/10 text-mars-orange"
                    : "border-line text-text-secondary hover:border-mars-orange/60 hover:text-text-primary"
                }`}
              >
                {VIEW_CONFIG[id].label}
              </button>
            ))}
          </div>

          <div className="grid items-center gap-8 lg:grid-cols-[190px_minmax(0,1fr)_200px] lg:gap-5 xl:grid-cols-[230px_minmax(0,1fr)_250px] xl:gap-10">
            {/* Left — selectors + planetary data */}
            <aside className="relative z-20 hidden flex-col gap-2.5 lg:flex">
              <div className="mb-1 text-micro text-text-muted">VISUALIZATION</div>
              {VIEWS.map((id, index) => {
                const active = selectedView === id;
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setSelectedView(id)}
                    aria-pressed={active}
                    aria-label={`Show ${VIEW_CONFIG[id].label} visualization`}
                    data-view-selector={id}
                    className={`group flex items-center justify-between gap-2 border px-3 py-2.5 text-left transition-colors ${
                      active
                        ? "border-mars-orange bg-mars-orange/10 text-mars-orange"
                        : "border-line/80 text-text-secondary hover:border-amber/60 hover:text-text-primary"
                    }`}
                  >
                    <span className="flex min-w-0 items-center gap-2.5">
                      <span className={`text-micro ${active ? "text-mars-orange/70" : "text-text-muted"}`}>
                        0{index + 1}
                      </span>
                      <span className="truncate text-xs font-medium">{VIEW_CONFIG[id].label}</span>
                    </span>
                    <ArrowUpRight
                      size={12}
                      aria-hidden
                      className={`shrink-0 transition-opacity ${
                        active ? "opacity-100" : "opacity-0 group-hover:opacity-60"
                      }`}
                    />
                  </button>
                );
              })}

              <div className="mt-4 border border-line/80 bg-canvas/70 p-4">
                <div className="text-micro text-mars-orange">PLANETARY DATA</div>
                <dl className="mt-3 space-y-1.5">
                  {[
                    ["Radius", "3,390 km"],
                    ["Gravity", "3.71 m/s²"],
                    ["Moons", "Phobos, Deimos"],
                    ["Region", "Gale Crater"],
                  ].map(([label, value]) => (
                    <div key={label} className="flex items-center justify-between gap-3">
                      <dt className="text-micro text-text-muted">{label}</dt>
                      <dd className="text-[11px] text-text-secondary">{value}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-3 border-t border-line/60 pt-2 text-micro text-text-muted">
                  OBSERVED · NASA/JPL
                </div>
              </div>
            </aside>

            {/* Center — planet stage */}
            <div className="relative flex w-full flex-col items-center text-center">
              <div className="text-micro tracking-[0.3em] text-text-secondary">
                EXPLORE THE RED PLANET
              </div>

              <div
                className="relative mt-5 flex w-full shrink-0 items-center justify-center"
                style={stageStyle}
                data-globe-stage
              >
                {selectedView === "Mars Globe" ? (
                  <div className="relative" style={globeStyle}>
                    {/* Oversized MARS typography: centred on the globe axis, allowed to
                        extend beyond the globe on both sides, behind the planet. */}
                    <div
                      aria-hidden
                      className="pointer-events-none absolute inset-0 z-[1] flex items-center justify-center"
                    >
                      <span
                        data-mars-word
                        className="select-none whitespace-nowrap font-heading font-bold leading-none"
                        style={globeWordStyle}
                      >
                        MARS
                      </span>
                    </div>

                    {/* Restrained planet lighting */}
                    <div
                      aria-hidden
                      className="absolute -inset-10 z-0 rounded-full bg-[radial-gradient(circle,rgba(240,107,61,0.20),transparent_64%)] blur-2xl"
                    />

                    <div
                      data-globe-disc
                      className="relative z-10 h-full w-full overflow-hidden rounded-full border border-[#3a2a22] bg-[#0b0908] shadow-[0_0_70px_rgba(240,107,61,0.20)]"
                    >
                      {/* The SVS frame is 16:9 with the planet at ~68% of the frame
                          height. A uniform inner scale makes Mars fill ~90% of the
                          circular mask without stretching or rotating the planet. */}
                      <div
                        className="absolute inset-0 origin-center"
                        style={{ transform: "scale(1.317)" }}
                      >
                        <img
                          src="/videos/mars-poster.jpg"
                          alt="Poster frame of the NASA rotating Mars visualization"
                          className="absolute inset-0 h-full w-full object-cover"
                        />
                        {!reduceMotion && !videoFailed && (
                          <video
                            ref={videoRef}
                            className="absolute inset-0 h-full w-full object-cover"
                            autoPlay
                            muted
                            loop
                            playsInline
                            preload="auto"
                            poster="/videos/mars-poster.jpg"
                            aria-label="Rotating Mars globe visualization"
                            onPlaying={() => setVideoStatus("playing")}
                            onCanPlay={(event) => {
                              event.currentTarget
                                .play()
                                .catch(() => setVideoStatus("autoplay-blocked"));
                            }}
                            onPause={() => setVideoStatus("poster")}
                            onError={() => {
                              setVideoFailed(true);
                              setVideoStatus("error");
                            }}
                          >
                            <source src="/videos/mars-rotation.webm" type="video/webm" />
                          </video>
                        )}
                      </div>

                      <div
                        aria-hidden
                        className="pointer-events-none absolute inset-0 rounded-full shadow-[inset_0_0_36px_rgba(0,0,0,0.45),inset_0_0_2px_rgba(255,255,255,0.18)]"
                      />

                      <div className="absolute left-3 top-3">
                        <StatusChip status="OBSERVED" note="NASA SVS" />
                      </div>

                      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent px-3 pb-2.5 pt-8">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-micro text-text-secondary">{videoLabel}</span>
                          {!reduceMotion &&
                            (videoStatus === "autoplay-blocked" || videoStatus === "poster") && (
                              <button
                                type="button"
                                onClick={() => {
                                  const attempt = videoRef.current?.play();
                                  if (attempt && typeof attempt.catch === "function") {
                                    attempt.catch(() => setVideoStatus("autoplay-blocked"));
                                  }
                                }}
                                className="inline-flex items-center gap-1 border border-mars-orange/70 px-2 py-1 text-micro text-mars-orange transition-colors hover:bg-mars-orange hover:text-canvas"
                              >
                                <Play size={9} aria-hidden /> PLAY
                              </button>
                            )}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div
                    key={selectedView}
                    className="hero-visual-in relative overflow-hidden border border-mars-orange/40 bg-[#0b0806] shadow-[0_0_60px_rgba(240,107,61,0.16)]"
                    style={panelStyle}
                    data-visual-panel={selectedView}
                  >
                    {selectedView === "Terrain" && (
                      <>
                        {terrainStatus !== "error" && (
                          <img
                            src={TERRAIN_ASSET}
                            alt="NASA CTX panchromatic mosaic of Gale Crater and Aeolis Mons"
                            className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-500 ${
                              terrainStatus === "loaded" ? "opacity-100" : "opacity-60"
                            }`}
                            decoding="async"
                            onLoad={() => setTerrainStatus("loaded")}
                            onError={() => setTerrainStatus("error")}
                          />
                        )}
                        {terrainStatus === "error" && (
                          <UnavailableView label="Gale Crater CTX mosaic could not be loaded from the local asset. The observed terrain layer is unavailable; no substitute imagery is shown." />
                        )}
                        <div
                          aria-hidden
                          className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/45"
                        />
                        <div
                          aria-hidden
                          className="pointer-events-none absolute inset-0 opacity-[0.14]"
                          style={{
                            backgroundImage:
                              "linear-gradient(to right, rgba(240,107,61,0.5) 1px, transparent 1px), linear-gradient(to bottom, rgba(240,107,61,0.5) 1px, transparent 1px)",
                            backgroundSize: "64px 64px",
                          }}
                        />
                        <div className="absolute left-3 top-3">
                          <StatusChip status={terrainDisplay} note="NASA CTX" />
                        </div>
                        <div className="absolute right-3 top-3 text-right">
                          <div className="text-micro text-text-primary/90">GALE CRATER</div>
                          <div className="text-micro text-text-secondary">AEOLIS MONS</div>
                        </div>
                        <div className="absolute inset-x-4 bottom-4 flex items-end justify-between gap-4">
                          <div className="text-left">
                            <div className="text-micro text-mars-orange">SURFACE TERRAIN</div>
                            <div className="mt-1 text-micro text-text-secondary">
                              CTX MOSAIC · Z{TERRAIN_META.zoom} · {TERRAIN_META.resolution}
                            </div>
                            <div className="mt-0.5 text-micro text-text-muted">
                              {TERRAIN_META.coverage}
                            </div>
                          </div>
                          <ScaleBar
                            width={TERRAIN_META.scaleBarWidth}
                            label={TERRAIN_META.scaleBarLabel}
                            className="items-end text-right"
                          />
                        </div>
                        <HudCorners />
                      </>
                    )}

                    {selectedView === "Elevation" && (
                      <>
                        {elevationStatus !== "error" && (
                          <img
                            src={ELEVATION_ASSET}
                            alt="Hypsometric MOLA elevation relief of the Gale Crater region"
                            className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-500 ${
                              elevationStatus === "loaded" ? "opacity-100" : "opacity-60"
                            }`}
                            decoding="async"
                            onLoad={() => setElevationStatus("loaded")}
                            onError={() => setElevationStatus("error")}
                          />
                        )}
                        {elevationStatus === "error" && (
                          <UnavailableView label="The derived MOLA elevation relief could not be loaded. The local DEM product is unavailable; no substitute chart is shown." />
                        )}
                        <div
                          aria-hidden
                          className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/85 via-transparent to-black/40"
                        />
                        <div className="absolute left-3 top-3">
                          <StatusChip status={elevationDisplay} note="MOLA RELIEF" />
                        </div>
                        <div className="absolute right-3 top-3 text-right">
                          <div className="text-micro text-text-primary/90">HYPSOMETRIC RELIEF</div>
                          <div className="text-micro text-text-secondary">
                            DERIVED FROM MOLA
                          </div>
                        </div>
                        <div className="absolute inset-x-4 bottom-4 flex items-end justify-between gap-4">
                          <div className="max-w-[65%] text-left">
                            <div className="flex items-center justify-between gap-3">
                              <span className="text-micro text-mars-orange">ELEVATION (m)</span>
                              <span className="text-micro text-text-muted">NO-DATA EXCLUDED</span>
                            </div>
                            <div
                              aria-hidden
                              className="mt-1.5 h-2 w-full border border-white/15"
                              style={{
                                background:
                                  "linear-gradient(90deg,#2a0b2e,#4e102f,#7c1b2c,#a6312c,#c6512e,#de7c35,#eeb05c,#fae1a6)",
                              }}
                            />
                            <div className="mt-1 flex items-center justify-between gap-2 text-[9px] tracking-[0.08em] text-text-secondary">
                              <span>{ELEVATION_META.min}</span>
                              <span>0 m</span>
                              <span>{ELEVATION_META.max}</span>
                            </div>
                            <div className="mt-1 text-micro text-text-muted">
                              {ELEVATION_META.coverage}
                            </div>
                          </div>
                          <ScaleBar
                            width={ELEVATION_META.scaleBarWidth}
                            label={ELEVATION_META.scaleBarLabel}
                            className="items-end text-right"
                          />
                        </div>
                        <HudCorners />
                      </>
                    )}

                    {selectedView === "Mission Data" && (
                      <MissionDashboard
                        reliefFailed={reliefFailed}
                        onReliefError={() => setReliefFailed(true)}
                      />
                    )}
                  </div>
                )}
              </div>

              <div className="mt-6">
                <div className="font-heading text-base tracking-[0.2em] sm:text-lg">
                  TOUCH DOWN ON MARS
                </div>
                <div className="mx-auto mt-1.5 max-w-md text-micro leading-relaxed text-text-secondary">
                  TERRAIN INTELLIGENCE AND MISSION DECISION SUPPORT AWAIT.
                </div>
                <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
                  <Link
                    to="/overview"
                    className="inline-flex items-center gap-2 border border-mars-orange px-5 py-2.5 text-[11px] font-medium tracking-[0.12em] text-mars-orange transition-colors hover:bg-mars-orange hover:text-canvas"
                  >
                    LAUNCH MISSION CONTROL <ArrowRight size={13} aria-hidden />
                  </Link>
                  <button
                    type="button"
                    onClick={() => scrollTo("capabilities")}
                    className="inline-flex items-center gap-2 border border-line px-5 py-2.5 text-[11px] tracking-[0.12em] text-text-secondary transition-colors hover:border-amber/70 hover:text-text-primary"
                  >
                    DISCOVER CAPABILITIES
                  </button>
                </div>
              </div>

              {/* Telemetry below the globe on small screens */}
              <div className="mt-8 min-h-[360px] w-full max-w-md text-left lg:hidden">
                <TelemetryPanel view={view} status={activeStatus} statusNote={statusNote} />
              </div>
            </div>

            {/* Right — dynamic telemetry */}
            <aside
              className="relative z-20 hidden flex-col justify-center lg:flex lg:min-h-[600px] xl:min-h-0"
              data-telemetry
            >
              <TelemetryPanel view={view} status={activeStatus} statusNote={statusNote} />
              <p className="mt-3 text-right text-micro text-text-muted normal-case tracking-normal">
                {view.footnote}
              </p>
            </aside>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* Overview                                                         */}
      {/* ---------------------------------------------------------------- */}
      <section id="overview" className="scroll-mt-20 border-b border-line/70">
        <div className="lp-container py-14 md:py-20">
          <SectionHeading index="01" label="OVERVIEW" />
          <div className="mt-6 grid gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-start">
            <div>
              <h2 className="font-heading text-2xl font-semibold md:text-3xl">
                Mission Intelligence Platform
              </h2>
              <p className="mt-4 font-heading text-3xl leading-[1.1] md:text-5xl">
                Navigate Mars.
                <br />
                Understand the Terrain.
                <br />
                <span className="text-mars-orange">Protect Every Mission.</span>
              </p>
              <p className="mt-6 max-w-2xl text-sm leading-relaxed text-text-secondary md:text-base">
                DHRUVION is a map-first mission-planning prototype for exploring Martian
                terrain, identifying geological science targets, comparing surface traverse
                routes, evaluating outbound-and-return feasibility, and responding to
                simulated route obstructions.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link
                  to="/overview"
                  className="inline-flex items-center gap-2 border border-mars-orange px-5 py-2.5 text-[11px] font-medium tracking-[0.12em] text-mars-orange transition-colors hover:bg-mars-orange hover:text-canvas"
                >
                  EXPLORE MISSION CONTROL <ArrowRight size={13} aria-hidden />
                </Link>
                <button
                  type="button"
                  onClick={() => scrollTo("capabilities")}
                  className="inline-flex items-center gap-2 border border-line px-5 py-2.5 text-[11px] tracking-[0.12em] text-text-secondary transition-colors hover:border-amber/70 hover:text-text-primary"
                >
                  DISCOVER CAPABILITIES
                </button>
              </div>
            </div>

            <aside className="panel p-6">
              <div className="text-micro text-mars-orange">PROTOTYPE SCOPE</div>
              <dl className="mt-4 space-y-3">
                {[
                  ["Region", "Gale Crater, Mars"],
                  ["Basemap", "NASA Mars Trek WMTS"],
                  ["Elevation", "MGS MOLA MEGDR · 463 m/px"],
                  ["Workflow", "Map → terrain → routes → science → emergency"],
                ].map(([label, value]) => (
                  <div key={label} className="border-b border-line/50 pb-3 last:border-b-0 last:pb-0">
                    <dt className="text-micro text-text-muted">{label}</dt>
                    <dd className="mt-1 text-sm text-text-secondary">{value}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-4 text-xs leading-relaxed text-text-muted">
                Built for the NASA Space Apps Challenge — Interplanetary Survival Guide:
                Martian Map.
              </p>
            </aside>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* Capabilities                                                     */}
      {/* ---------------------------------------------------------------- */}
      <section id="capabilities" className="scroll-mt-20 border-b border-line/70">
        <div className="lp-container py-14 md:py-20">
          <SectionHeading index="02" label="CAPABILITIES" />
          <div className="mt-4 flex flex-col justify-between gap-3 md:flex-row md:items-end">
            <h2 className="font-heading text-2xl font-semibold md:text-3xl">
              Mission capabilities
            </h2>
            <p className="max-w-xl text-sm text-text-secondary">
              Four connected workspaces turn NASA-derived terrain data into traversable,
              inspectable mission decisions.
            </p>
          </div>

          <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            {CAPABILITIES.map((capability) => {
              const Icon = capability.icon;
              return (
                <Link
                  key={capability.to}
                  to={capability.to}
                  className="group flex h-full flex-col border border-line bg-surface1 p-5 transition-colors hover:border-mars-orange/70 hover:bg-surface2"
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-micro text-text-muted">{capability.label}</span>
                    <Icon size={17} aria-hidden className="shrink-0 text-mars-orange/80" />
                  </div>
                  <h3 className="mt-4 font-heading text-base leading-snug">
                    {capability.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                    {capability.description}
                  </p>
                  <span className="mt-5 flex items-center gap-1.5 text-micro text-mars-orange">
                    OPEN WORKSPACE <ArrowUpRight size={12} aria-hidden />
                  </span>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* How it works                                                     */}
      {/* ---------------------------------------------------------------- */}
      <section id="how" className="scroll-mt-20 border-b border-line/70">
        <div className="lp-container py-14 md:py-20">
          <SectionHeading index="03" label="HOW IT WORKS" />
          <div className="mt-4 flex flex-col justify-between gap-3 md:flex-row md:items-end">
            <h2 className="font-heading text-2xl font-semibold md:text-3xl">
              From terrain to decision
            </h2>
            <p className="max-w-xl text-sm text-text-secondary">
              A single flow from observed terrain layers to an explainable traverse
              recommendation.
            </p>
          </div>

          <div className="relative mt-8">
            <div
              aria-hidden
              className="absolute left-0 right-0 top-[22px] hidden h-px bg-gradient-to-r from-mars-orange/50 via-line to-transparent lg:block"
            />
            <ol className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            {WORKFLOW.map((item) => (
              <li
                key={item.step}
                className="relative border border-line bg-surface1 p-5"
              >
                <div className="flex items-center gap-3">
                  <span className="relative z-10 flex h-5 w-5 items-center justify-center rounded-full border border-mars-orange/70 bg-surface1">
                    <span className="h-1.5 w-1.5 rounded-full bg-mars-orange" />
                  </span>
                  <span className="text-micro text-text-muted">{item.step}</span>
                </div>
                <h3 className="mt-3 font-heading text-base">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                  {item.description}
                </p>
              </li>
            ))}
            </ol>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* Technology                                                       */}
      {/* ---------------------------------------------------------------- */}
      <section id="technology" className="scroll-mt-20 border-b border-line/70">
        <div className="lp-container py-14 md:py-20">
          <SectionHeading index="04" label="TECHNOLOGY" />
          <div className="mt-4 flex flex-col justify-between gap-3 md:flex-row md:items-end">
            <h2 className="font-heading text-2xl font-semibold md:text-3xl">
              Data and technology
            </h2>
            <p className="max-w-xl text-sm text-text-secondary">
              NASA-derived layers, local terrain processing and a deterministic routing
              service behind one map-first interface.
            </p>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {TECH_GROUPS.map((group) => {
              const Icon = group.icon;
              return (
                <div key={group.label} className="border border-line bg-surface1 p-5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-micro text-mars-orange">{group.label}</span>
                    <Icon size={16} aria-hidden className="text-text-muted" />
                  </div>
                  <ul className="mt-4 space-y-2">
                    {group.items.map((item) => (
                      <li key={item} className="flex items-start gap-2 text-sm text-text-secondary">
                        <span aria-hidden className="mt-[7px] h-1 w-1 shrink-0 bg-amber/80" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>

          <div className="mt-4 grid gap-4 border border-line bg-surface1 p-5 sm:grid-cols-2 lg:grid-cols-4">
            {DATA_STATES.map((state) => (
              <div key={state.state} className="flex flex-col gap-1">
                <span className={`text-micro ${STATUS_TONE[state.state]}`}>
                  {state.state}
                </span>
                <span className="text-xs leading-relaxed text-text-secondary">
                  {state.note}
                </span>
              </div>
            ))}
          </div>

          <p className="mt-4 text-xs leading-relaxed text-text-muted">
            Observed, derived, simulated and unavailable states are kept distinct. This is a
            prototype, not a certified safety system.
          </p>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* About                                                            */}
      {/* ---------------------------------------------------------------- */}
      <section id="about" className="scroll-mt-20 border-b border-line/70">
        <div className="lp-container py-14 md:py-20">
          <SectionHeading index="05" label="ABOUT" />
          <div className="mt-6 grid gap-10 lg:grid-cols-[1.1fr_0.9fr]">
            <div>
              <h2 className="font-heading text-2xl font-semibold md:text-3xl">
                About DHRUVION
              </h2>
              <p className="mt-4 max-w-2xl text-sm leading-relaxed text-text-secondary md:text-base">
                DHRUVION is a map-first mission-planning prototype built for the NASA Space
                Apps Challenge — Interplanetary Survival Guide: Martian Map. It turns
                NASA-derived planetary data into spatially understandable evidence and
                explainable planning recommendations for astronauts, mission operators and
                science planners.
              </p>
              <p className="mt-4 max-w-2xl text-sm leading-relaxed text-text-secondary">
                The interface is intentionally explicit about data provenance: observed,
                derived, simulated and unavailable data remain visually distinct throughout
                the mission workflow.
              </p>
            </div>

            <aside className="panel p-6">
              <div className="text-micro text-warning-amber">PROTOTYPE DISCLAIMER</div>
              <p className="mt-3 text-sm leading-relaxed text-text-secondary">
                DHRUVION is a hackathon decision-support demonstration. It is not a
                certified flight system, an autonomous vehicle controller, or a guarantee
                that any traverse is safe.
              </p>
              <p className="mt-3 text-sm leading-relaxed text-text-secondary">
                Emergency scenarios are simulated. Route planning is limited to the local
                MOLA coverage described above.
              </p>
            </aside>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* Footer                                                           */}
      {/* ---------------------------------------------------------------- */}
      <footer className="bg-[#060505]">
        <div className="lp-container py-12">
          <div className="grid gap-8 md:grid-cols-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center border border-mars-orange/70 text-[10px] font-bold text-mars-orange">
                  D
                </span>
                <span className="font-heading text-sm tracking-[0.22em]">DHRUVION</span>
              </div>
              <p className="mt-3 max-w-sm text-sm leading-relaxed text-text-secondary">
                AI-powered Martian Mission Intelligence Platform for terrain understanding,
                route planning and mission decision support.
              </p>
            </div>

            <div>
              <div className="text-micro text-text-muted">NAVIGATION</div>
              <div className="mt-3 flex flex-col items-start gap-2 text-sm text-text-secondary">
                {NAV_ITEMS.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => scrollTo(item.id)}
                    className="transition-colors hover:text-text-primary"
                  >
                    {item.label.charAt(0) + item.label.slice(1).toLowerCase()}
                  </button>
                ))}
                <Link to="/login" className="transition-colors hover:text-text-primary">
                  Sign In
                </Link>
              </div>
            </div>

            <div>
              <div className="text-micro text-text-muted">DATA SOURCES</div>
              <p className="mt-3 text-sm leading-relaxed text-text-secondary">
                NASA Mars Trek WMTS and MGS MOLA MEGDR data are referenced where used.
                NASA SVS imagery is used for the Mars visualization.
              </p>
              <p className="mt-3 text-xs leading-relaxed text-text-muted">
                Prototype and safety disclaimer: not a certified flight or navigation
                system.
              </p>
            </div>
          </div>

          <div className="mt-10 flex flex-col gap-2 border-t border-line/60 pt-5 text-micro text-text-muted sm:flex-row sm:items-center sm:justify-between">
            <span>© {new Date().getFullYear()} DHRUVION</span>
            <span>Gale Crater · Mars · terrain analysis · MOLA / CTX</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

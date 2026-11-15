import L from "leaflet";
import type { BoundsLatLon, LayerBounds } from "../../types";

/**
 * Prototype Mars equirectangular CRS used by every map in the dashboard.
 * Kept in one place so each workspace renders the same projection.
 * Web Mercator is never used for Mars overlays.
 */
export const MarsCRS = L.extend({}, L.CRS, {
  code: "Mars:Equirectangular",
  projection: L.Projection.LonLat,
  transformation: new L.Transformation(1 / 180, 1, -1 / 180, 0.5),
}) as unknown as L.CRS;

export const MARS_BOUNDS: L.LatLngBoundsExpression = [
  [-90, -180],
  [90, 180],
];

/** Fallback only: replaced by /api/regions metadata as soon as it loads. */
export const GALE_CENTER: L.LatLngExpression = [-5.4, 137.8];
export const GALE_BOUNDS: L.LatLngBoundsExpression = [
  [-7.0, 136.2],
  [-3.8, 139.4],
];

export const MOLA_BASEMAP_URL =
  "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg";

export const MOLA_ATTRIBUTION = "NASA Mars Trek / MGS MOLA";

export const LAYER_TILE_URLS: Record<string, string> = {
  mars_trek_mola_colorshade: MOLA_BASEMAP_URL,
  mola_roughness:
    "https://trek.nasa.gov/tiles/Mars/EQ/mola_roughness/1.0.0/default/default028mm/{z}/{y}/{x}.png",
  mars_mola_hrsc_blend:
    "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
  gale_ctx:
    "https://trek.nasa.gov/tiles/Mars/EQ/Gale_CTX_BlockAdj_dd/1.0.0/default/default028mm/{z}/{y}/{x}.png",
  viking_mdim:
    "https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
};

export const LAYER_MAX_ZOOM: Record<string, number> = {
  mola_roughness: 1,
  gale_ctx: 8,
};

export const API_ORIGIN = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api"
).replace(/\/api\/?$/, "");

/** Convert backend `bounds_latlon` metadata into Leaflet [[south, west], [north, east]]. */
export function toLeafletBounds(
  bounds?: BoundsLatLon | null,
): L.LatLngBoundsExpression | null {
  if (
    !bounds ||
    ![bounds.south, bounds.north, bounds.west, bounds.east].every((value) =>
      Number.isFinite(value),
    )
  ) {
    return null;
  }
  return [
    [bounds.south, bounds.west],
    [bounds.north, bounds.east],
  ];
}

/** Extract Leaflet bounds from either a layer `bounds` object or a raw lat/lon box. */
export function layerLeafletBounds(bounds: unknown): L.LatLngBoundsExpression | null {
  if (!bounds || typeof bounds !== "object") return null;
  const value = bounds as LayerBounds & BoundsLatLon;
  if (Array.isArray(value.leaflet_bounds) && value.leaflet_bounds.length === 2) {
    const [[south, west], [north, east]] = value.leaflet_bounds;
    if ([south, west, north, east].every((n) => Number.isFinite(n))) {
      return [
        [south, west],
        [north, east],
      ];
    }
  }
  return toLeafletBounds(value.bounds_latlon ?? (value as BoundsLatLon));
}

export function boundsCenter(bounds?: BoundsLatLon | null): L.LatLngExpression {
  if (
    !bounds ||
    ![bounds.south, bounds.north, bounds.west, bounds.east].every((value) =>
      Number.isFinite(value),
    )
  ) {
    return GALE_CENTER;
  }
  return [(bounds.south + bounds.north) / 2, (bounds.west + bounds.east) / 2];
}

/** Absolute URL for a backend-served overlay/static asset. */
export function assetUrl(path?: string | null): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_ORIGIN}${path.startsWith("/") ? path : `/${path}`}`;
}

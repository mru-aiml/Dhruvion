import { useEffect, useRef, useCallback, useState } from "react";
import { MapContainer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { LatLngExpression, LatLngBoundsExpression, Coords } from "leaflet";
import { MarsCRS, GALE_BOUNDS } from "./mars";

interface TileLayerConfig {
  id: string;
  url: string;
  attribution: string;
  maxZoom: number;
  tileSize?: number;
  opacity?: number;
  visible?: boolean;
}

interface ImageOverlayConfig {
  id: string;
  url: string;
  bounds: LatLngBoundsExpression;
  opacity: number;
  visible?: boolean;
}

interface MarkerConfig {
  id: string;
  position: LatLngExpression;
  icon: L.DivIcon;
  draggable?: boolean;
  onDragEnd?: (lat: number, lng: number) => void;
  title?: string;
  onClick?: () => void;
}

interface PolylineConfig {
  id: string;
  positions: LatLngExpression[];
  color: string;
  weight: number;
  opacity: number;
  dashArray?: string;
  visible?: boolean;
}

interface MapViewState {
  center: LatLngExpression;
  zoom: number;
}

interface MarsMapProps {
  /** Initial map center [lat, lon] */
  center?: LatLngExpression;
  /** Initial zoom level */
  zoom?: number;
  /** Minimum zoom */
  minZoom?: number;
  /** Maximum zoom */
  maxZoom?: number;
  /** Map container className */
  className?: string;
  /** Map container style */
  style?: React.CSSProperties;
  /** Tile layers to display */
  tileLayers?: TileLayerConfig[];
  /** Image overlays to display */
  imageOverlays?: ImageOverlayConfig[];
  /** Markers to display */
  markers?: MarkerConfig[];
  /** Polylines to display */
  polylines?: PolylineConfig[];
  /** Callback when map is ready */
  onMapReady?: (map: L.Map) => void;
  /** Callback when map view changes */
  onViewChange?: (view: MapViewState) => void;
  /** Callback when map is clicked */
  onMapClick?: (lat: number, lng: number) => void;
  /** Callback when pointer moves */
  onPointerMove?: (lat: number, lng: number) => void;
  /** Fit bounds to content (only applied on initial mount or when explicitly requested) */
  fitBounds?: LatLngBoundsExpression | LatLngExpression[] | null;
  /** Fit bounds options */
  fitBoundsOptions?: L.FitBoundsOptions;
  /** Disable zoom control */
  zoomControl?: boolean;
  /** Disable attribution control */
  attributionControl?: boolean;
  /** Disable scroll wheel zoom */
  scrollWheelZoom?: boolean;
  /** Explicit container height (required for stable rendering) */
  containerHeight?: string | number;
  /** Explicit container width */
  containerWidth?: string | number;
  /** Trigger fitBounds on demand (increment to re-trigger) */
  fitBoundsTrigger?: number;
}

/**
 * Custom TileLayer that handles NASA Mars Trek's {z}/{y}/{x} column/row ordering.
 * Standard Leaflet TileLayer expects {z}/{x}/{y} (column/row).
 * NASA Trek WMTS uses {z}/{y}/{x} (row/column).
 */
function NasaTileLayer({
  url,
  attribution,
  maxZoom,
  tileSize = 256,
  opacity = 1,
  visible = true,
}: TileLayerConfig) {
  const layerRef = useRef<L.TileLayer | null>(null);
  const map = useMap();

  useEffect(() => {
    if (!visible) {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
      return;
    }

    // Create a custom tile layer that swaps x/y for NASA Trek URLs
    const tileLayer = L.tileLayer(url, {
      attribution,
      maxZoom,
      tileSize,
      opacity,
    });

    // Override getTileUrl to swap x and y for NASA Trek
    (tileLayer as L.TileLayer & { getTileUrl: (coords: Coords) => string }).getTileUrl = function (coords: Coords) {
      const { x, y, z } = coords;
      // NASA Trek uses {z}/{y}/{x} - swap x and y
      // Access internal properties via type assertion
      const tl = this as unknown as { _url: string; options: Record<string, unknown> };
      return L.Util.template(tl._url, L.extend({ x: y, y: x, z }, tl.options));
    };

    tileLayer.addTo(map);
    layerRef.current = tileLayer;

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [map, url, attribution, maxZoom, tileSize, opacity, visible]);

  return null;
}

/**
 * Standard TileLayer for non-NASA sources (uses standard {z}/{x}/{y})
 */
function StandardTileLayer({
  url,
  attribution,
  maxZoom,
  tileSize = 256,
  opacity = 1,
  visible = true,
}: TileLayerConfig) {
  const layerRef = useRef<L.TileLayer | null>(null);
  const map = useMap();

  useEffect(() => {
    if (!visible) {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
      return;
    }

    const tileLayer = L.tileLayer(url, {
      attribution,
      maxZoom,
      tileSize,
      opacity,
    });

    tileLayer.addTo(map);
    layerRef.current = tileLayer;

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [map, url, attribution, maxZoom, tileSize, opacity, visible]);

  return null;
}

function ImageOverlayComponent({
  url,
  bounds,
  opacity = 1,
  visible = true,
}: ImageOverlayConfig) {
  const layerRef = useRef<L.ImageOverlay | null>(null);
  const map = useMap();

  useEffect(() => {
    if (!visible) {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
      return;
    }

    const overlay = L.imageOverlay(url, bounds, { opacity });
    overlay.addTo(map);
    layerRef.current = overlay;

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [map, url, bounds, opacity, visible]);

  return null;
}

function MarkerComponent({
  position,
  icon,
  draggable = false,
  onDragEnd,
  title,
  onClick,
}: MarkerConfig) {
  const markerRef = useRef<L.Marker | null>(null);
  const map = useMap();

  useEffect(() => {
    const marker = L.marker(position, { icon, draggable, title });
    
    if (draggable && onDragEnd) {
      marker.on("dragend", (e) => {
        const latlng = e.target.getLatLng();
        onDragEnd(latlng.lat, latlng.lng);
      });
    }
    
    if (onClick) {
      marker.on("click", onClick);
    }

    marker.addTo(map);
    markerRef.current = marker;

    return () => {
      if (markerRef.current) {
        map.removeLayer(markerRef.current);
        markerRef.current = null;
      }
    };
  }, [map, position, icon, draggable, onDragEnd, title, onClick]);

  return null;
}

function PolylineComponent({
  positions,
  color,
  weight,
  opacity,
  dashArray,
  visible = true,
}: PolylineConfig) {
  const layerRef = useRef<L.Polyline | null>(null);
  const map = useMap();

  useEffect(() => {
    if (!visible || positions.length < 2) {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
      return;
    }

    const polyline = L.polyline(positions, { color, weight, opacity, dashArray });
    polyline.addTo(map);
    layerRef.current = polyline;

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [map, positions, color, weight, opacity, dashArray, visible]);

  return null;
}

function MapEventHandlers({
  onMapClick,
  onPointerMove,
  onViewChange,
}: {
  onMapClick?: (lat: number, lng: number) => void;
  onPointerMove?: (lat: number, lng: number) => void;
  onViewChange?: (view: MapViewState) => void;
}) {
  const map = useMap();

  useEffect(() => {
    if (!onMapClick && !onPointerMove && !onViewChange) return;

    const clickHandler = (e: L.LeafletMouseEvent) => {
      onMapClick?.(e.latlng.lat, e.latlng.lng);
    };

    const moveHandler = (e: L.LeafletMouseEvent) => {
      onPointerMove?.(e.latlng.lat, e.latlng.lng);
    };

    const viewHandler = () => {
      onViewChange?.({
        center: [map.getCenter().lat, map.getCenter().lng],
        zoom: map.getZoom(),
      });
    };

    if (onMapClick) map.on("click", clickHandler);
    if (onPointerMove) map.on("mousemove", moveHandler);
    if (onViewChange) map.on("moveend zoomend", viewHandler);

    return () => {
      if (onMapClick) map.off("click", clickHandler);
      if (onPointerMove) map.off("mousemove", moveHandler);
      if (onViewChange) map.off("moveend zoomend", viewHandler);
    };
  }, [map, onMapClick, onPointerMove, onViewChange]);

  return null;
}

/**
 * Internal component to capture map instance and handle initial fitBounds
 */
function MapInitializer({
  onMapReady,
  fitBounds,
  fitBoundsOptions,
  fitBoundsTrigger,
}: {
  onMapReady?: (map: L.Map) => void;
  fitBounds?: LatLngBoundsExpression | LatLngExpression[] | null;
  fitBoundsOptions?: L.FitBoundsOptions;
  fitBoundsTrigger?: number;
}) {
  const map = useMap();
  const initialized = useRef(false);
  const fitBoundsApplied = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    onMapReady?.(map);

    if (fitBounds && !fitBoundsApplied.current) {
      fitBoundsApplied.current = true;
      const boundsArray = fitBounds as LatLngExpression[];
      if (boundsArray.length >= 2) {
        const latLngBounds = L.latLngBounds(
          boundsArray.map((coord: LatLngExpression) => {
            const [lat, lng] = coord as [number, number];
            return L.latLng(lat, lng);
          })
        );
        map.fitBounds(latLngBounds, { padding: [20, 20], maxZoom: 9, ...fitBoundsOptions });
      }
    }
  }, [map, onMapReady, fitBounds, fitBoundsOptions]);

  // Re-apply fitBounds when trigger changes (for explicit re-fitting)
  useEffect(() => {
    if (!fitBounds || fitBoundsTrigger === undefined) return;
    
    const boundsArray = fitBounds as LatLngExpression[];
    if (boundsArray.length >= 2) {
      const latLngBounds = L.latLngBounds(
        boundsArray.map((coord: LatLngExpression) => {
          const [lat, lng] = coord as [number, number];
          return L.latLng(lat, lng);
        })
      );
      map.fitBounds(latLngBounds, { padding: [20, 20], maxZoom: 9, ...fitBoundsOptions });
    }
  }, [fitBoundsTrigger, map, fitBounds, fitBoundsOptions]);

  return null;
}

/**
 * Main MarsMap component - stable, reusable map implementation
 * 
 * Key stability guarantees:
 * - MapContainer renders once with stable props (center, zoom only used for initial view)
 * - Layer/marker/polyline updates don't cause map remount
 * - Explicit container dimensions prevent collapse
 * - ResizeObserver handles container size changes
 * - fitBounds only applied on mount or explicit trigger
 */
export function MarsMap({
  center = (GALE_BOUNDS as [LatLngExpression, LatLngExpression])[0],
  zoom = 6,
  minZoom = 0,
  maxZoom = 8,
  className = "",
  style,
  tileLayers = [],
  imageOverlays = [],
  markers = [],
  polylines = [],
  onMapReady,
  onViewChange,
  onMapClick,
  onPointerMove,
  fitBounds = null,
  fitBoundsOptions,
  zoomControl = false,
  attributionControl = true,
  scrollWheelZoom = false,
  containerHeight = "100%",
  containerWidth = "100%",
  fitBoundsTrigger = 0,
}: MarsMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

  // Capture map instance from MapContainer
  const captureMap = useCallback((map: L.Map) => {
    mapInstanceRef.current = map;
    onMapReady?.(map);
  }, [onMapReady]);

  // Handle resize with ResizeObserver
  useEffect(() => {
    const element = mapContainerRef.current;
    if (!element) return;

    // Initial invalidateSize after mount
    const initialFrame = requestAnimationFrame(() => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.invalidateSize();
      }
    });

    // Set up ResizeObserver for future size changes
    resizeObserverRef.current = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setContainerSize({ width, height });
        if (mapInstanceRef.current && width > 0 && height > 0) {
          mapInstanceRef.current.invalidateSize();
        }
      }
    });

    resizeObserverRef.current.observe(element);

    return () => {
      cancelAnimationFrame(initialFrame);
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }
    };
  }, []);

  // Fallback: invalidateSize when container size becomes known
  useEffect(() => {
    if (containerSize.width > 0 && containerSize.height > 0 && mapInstanceRef.current) {
      mapInstanceRef.current.invalidateSize();
    }
  }, [containerSize.width, containerSize.height]);

  // Compute container style with explicit dimensions
  const containerStyle: React.CSSProperties = {
    height: typeof containerHeight === "number" ? `${containerHeight}px` : containerHeight,
    width: typeof containerWidth === "number" ? `${containerWidth}px` : containerWidth,
    background: "#14100c",
    ...style,
  };

  return (
    <div
      ref={mapContainerRef}
      className={`dhruvion-map-container ${className}`}
      style={containerStyle}
    >
      <MapContainer
        crs={MarsCRS}
        center={center}
        zoom={zoom}
        minZoom={minZoom}
        maxZoom={maxZoom}
        style={{ height: "100%", width: "100%" }}
        zoomControl={zoomControl}
        attributionControl={attributionControl}
        scrollWheelZoom={scrollWheelZoom}
      >
        <MapInitializer
          onMapReady={captureMap}
          fitBounds={fitBounds}
          fitBoundsOptions={fitBoundsOptions}
          fitBoundsTrigger={fitBoundsTrigger}
        />

        {tileLayers.map((layer) => {
          const isNasaTrek = layer.url.includes("trek.nasa.gov");
          return isNasaTrek ? (
            <NasaTileLayer key={layer.id} {...layer} />
          ) : (
            <StandardTileLayer key={layer.id} {...layer} />
          );
        })}

        {imageOverlays.map((overlay) => (
          <ImageOverlayComponent key={overlay.id} {...overlay} />
        ))}

        {markers.map((marker) => (
          <MarkerComponent key={marker.id} {...marker} />
        ))}

        {polylines.map((polyline) => (
          <PolylineComponent key={polyline.id} {...polyline} />
        ))}

        <MapEventHandlers
          onMapClick={onMapClick}
          onPointerMove={onPointerMove}
          onViewChange={onViewChange}
        />
      </MapContainer>
    </div>
  );
}

export default MarsMap;
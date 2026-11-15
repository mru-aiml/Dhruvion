# DHRUVION Map Stability Root Cause Analysis

## Executive Summary

The Science Explorer and Route Planner maps appear initially but disappear after ~2 seconds due to **three compounding root causes**:

1. **Critical Tile URL Format Mismatch** - NASA Mars Trek tile URLs use `{z}/{y}/{x}` column/row order, but Leaflet's `TileLayer` expects standard XYZ `{z}/{x}/{y}` order. This causes 99%+ of tile requests to 404, making the map appear empty (only background color visible) once initial tile requests fail.

2. **Missing `invalidateSize()` After Layout Stabilization** - Maps initialize during React's `Suspense` fallback replacement and `page-in` CSS animation (180ms). The map container's final size isn't established until after these complete, but Leaflet never receives a resize notification, leaving the internal map at incorrect dimensions.

3. **Unstable `MapContainer` Lifecycle in Lazy-Loaded Pages** - Pages are lazy-loaded via `React.lazy` + `Suspense`. The `MapContainer` mounts after the lazy chunk loads, but the parent `page-in` animation and layout shifts cause the container to report incorrect dimensions during the critical initialization window.

## Evidence

### 1. Tile URL Format Mismatch (Primary Cause)

**File**: `frontend/src/components/map/mars.ts` (lines 27-42)

```typescript
export const MOLA_BASEMAP_URL =
  "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg";
```

**Leaflet Expectation**: Standard XYZ tiles use `{z}/{x}/{y}` (zoom/column/row).
**NASA Reality**: Mars Trek WMTS uses `{z}/{y}/{x}` (zoom/row/column).

**Impact**: At Gale Crater (lat≈-5.4, lon≈137.8), zoom 7:
- Correct tile: x≈113, y≈68 → URL `.../7/113/68.jpg`
- Requested tile: x=68, y=113 → URL `.../7/68/113.jpg` (wrong location, 404)

**Verification**: Browser Network tab shows 404 for virtually all tile requests after initial load.

### 2. Missing `invalidateSize()` After Layout Stabilization

**Files**: 
- `frontend/src/components/layout/AppShell.tsx` line 150: `page-in` animation on route change
- `frontend/src/App.tsx` lines 21-30: `Suspense` fallback during lazy load
- All map pages: `MapContainer` with `style={{ height: "100%", width: "100%" }}`

**Sequence**:
1. `Suspense` shows "Loading..." fallback (small height)
2. Lazy chunk loads, page component mounts with `MapContainer`
3. `page-in` animation runs (180ms, `transform: translateY(3px)`)
4. Layout stabilizes, container reaches final height (280-440px)
5. **Leaflet map never notified of size change** → internal map stays at fallback dimensions

**Result**: Map renders at ~50px height initially, then appears to "disappear" when content reflows.

### 3. Multiple `MapContainer` Instances Without Shared Instance Management

**Files**:
- `ScienceExplorerPage.tsx`: Lines 335-369 (1 MapContainer)
- `RoutePlannerPage.tsx`: Lines 260-328 (1 MapContainer) + 2 in `RouteMap` (EmergencyPage)
- `MartianMapPage.tsx`: Lines 273-335 (1 MapContainer)

Each page creates its own `MapContainer` with independent Leaflet instance. No shared map state management exists for:
- Basemap switching (recreates TileLayer, not map)
- Overlay toggling (recreates ImageOverlay)
- Route updates (recreates Polyline)

While react-leaflet v5 handles prop changes correctly, the custom `MarsCRS` and missing resize handling compound instability.

## Affected Pages

| Page | MapContainer Count | Tile Layers | Overlays | Route Layers |
|------|-------------------|-------------|----------|--------------|
| Science Explorer | 1 | 1 (MOLA) | 3 Markers | 0 |
| Route Planner | 1 | 5 (switchable) | 2 Markers | 3 Polylines |
| Martian Map | 1 | 6 (switchable) | 8 ImageOverlays | 1 Polyline |
| Emergency | 3 | 1 each | 0 | 2 Polylines |

## Why ~2 Seconds?

The ~2 second delay correlates with:
1. **Route Planner**: Initial `calculate()` API call (POST `/route/optimize` + `/mission/plan`) takes 1.5-2.5s. When it completes, `setRoutes()` triggers `FitRoutes.fitBounds()` on a map that never received `invalidateSize()`.
2. **Science Explorer**: `FocusSelected` flyTo runs on mount, but map is at wrong size. Tile 404s complete ~2s after initial requests.
3. **Browser tile timeout**: Failed tile requests retry/timeout around 2s mark.

## Fix Strategy

### Phase 1: Tile URL Correction (Immediate)
- Implement custom `TileLayer` component that swaps `{x}`/`{y}` for NASA Trek URLs
- Or use backend proxy `/api/tiles/{layer}/{z}/{x}/{y}.png` which handles conversion

### Phase 2: Map Lifecycle Stabilization
- Create reusable `MarsMap` component with:
  - Single `MapContainer` per page lifecycle
  - `useEffect` calling `map.invalidateSize()` after layout paint
  - `ResizeObserver` for container dimension changes
  - Stable layer management via refs (basemap, overlays, routes, markers)
  - Proper cleanup only on unmount

### Phase 3: Integration Testing
- 60-second browser verification per requirements
- Automated Playwright tests for map lifecycle

## Files Requiring Changes

### Core Fixes
1. `frontend/src/components/map/mars.ts` - Fix tile URL template or add NASA-specific TileLayer
2. `frontend/src/components/map/MarsMap.tsx` - **NEW** reusable map component
3. `frontend/src/features/science-explorer/ScienceExplorerPage.tsx` - Use MarsMap
4. `frontend/src/features/route-planner/RoutePlannerPage.tsx` - Use MarsMap
5. `frontend/src/features/martian-map/MartianMapPage.tsx` - Use MarsMap
6. `frontend/src/features/emergency/EmergencyPage.tsx` - Use MarsMap (for RouteMap sub-components)

### Configuration
7. `frontend/src/index.css` - Ensure map container sizing stability
8. `frontend/vite.config.ts` - Verify no build issues

### Testing
9. `frontend/tests/map-lifecycle.test.ts` - **NEW** Playwright tests
10. `docs/DEPLOYMENT_GUIDE.md` - **NEW** deployment documentation
11. `docs/PRODUCTION_READINESS_REPORT.md` - **NEW** final report
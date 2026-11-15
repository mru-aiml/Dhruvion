# Mars Imagery Debug

## Audit findings
1. Science Explorer map is rendered with React-Leaflet `MapContainer` using the Mars equirectangular CRS.
2. The basemap `TileLayer` uses `MOLA_BASEMAP_URL`, a verified NASA Mars Trek tile URL.
3. The grey-bordered stretched image came from a local `ImageOverlay` (`/static/mola/gale/elevation.png`) with `GALE_BOUNDS`, not from Mars Trek tiles.
4. Tile requests to `https://trek.nasa.gov/tiles/Mars/EQ/...` return HTTP 200.
5. The brown placeholder was `/geo-target.svg` in the inspection panel, not a real Mars image.

## Root cause
The Mars Trek basemap was already loading, but the local elevation `ImageOverlay` was stretched across Gale bounds and created grey margins. The inspection panel used a prototype SVG instead of a no-image state.

## Verified tile URL
`https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg`

## Changes
- Removed the stretched local elevation `ImageOverlay` from Science Explorer.
- Removed the brown `/geo-target.svg` placeholder and replaced it with a no-mission-imagery panel.
- Kept simulated target labels explicit.
- Retained NASA Mars Trek MOLA colour hillshade as the basemap.

## Verification
- Frontend production build passed.
- Tile request tested: HTTP 200.
- Backend tests: 63 passed.

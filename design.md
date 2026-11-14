# DHRUVION --- UI Design Specification

> **Navigate Mars. Understand the Terrain. Protect Every Mission.**\
> Product: AI-powered Martian Mission Intelligence Platform\
> Design artifact: `design.md`

------------------------------------------------------------------------

## 1. Product vision

DHRUVION is a mission-control interface for astronauts and mission
operators planning and evaluating surface traverses on Mars. It combines
planetary cartography, terrain intelligence, scientific target
discovery, route planning, emergency navigation, and an AI mission
assistant.

The experience should feel like a credible aerospace operations
system---not a generic analytics dashboard, consumer space-tourism site,
or decorative sci-fi HUD. Every visual element should help an operator
understand the terrain, assess risk, or make a mission decision.

### Primary users

-   **Astronauts / field crew:** need fast, legible information while
    planning or executing a surface traverse.
-   **Mission operators:** need an overview of mission progress, route
    feasibility, hazards, and scientific objectives.
-   **Science planners:** need to inspect geological targets and
    understand the evidence behind their priority.

### Core product principles

1.  **Map-first:** the Martian surface is the primary workspace and
    should dominate the visual hierarchy.
2.  **Evidence before decoration:** show the source and confidence of
    terrain or science information.
3.  **Operational clarity:** distinguish safe, caution, critical,
    blocked, and simulated states consistently.
4.  **Progressive disclosure:** keep the default view calm; reveal
    detailed layers, metrics, and explanations when needed.
5.  **Honest telemetry:** never present fabricated values as live
    mission data.

------------------------------------------------------------------------

## 2. Visual direction

### Reference interpretation

The supplied references contribute four complementary visual ideas:

-   **Cinematic Mars imagery:** large, detailed planetary surfaces,
    dramatic sunlight, dark space, and restrained warm highlights.
-   **Premium aerospace interfaces:** compact navigation, precise
    labels, thin dividers, technical annotations, and structured data
    panels.
-   **Planetary editorial layouts:** bold planet imagery, large
    condensed headings, clear section hierarchy, and generous negative
    space.
-   **Futuristic instrumentation:** subtle orbital geometry, coordinate
    marks, reticles, telemetry rings, and restrained interface graphics.

Combine these into a single operational interface. Do not reproduce any
reference screen literally. Avoid decorative sci-fi elements that
compete with the map or make data harder to read.

### Overall mood

-   Scientific, precise, composed, and quietly futuristic.
-   Dark graphite surfaces with warm Mars-orange emphasis.
-   High-detail planetary terrain as the principal visual texture.
-   Thin technical lines and compact uppercase labels.
-   Warm white text rather than pure white wherever possible.
-   No excessive glow, neon, glassmorphism, purple AI gradients, or
    ornamental animation.

### Color tokens

  ------------------------------------------------------------------------
  Token                                          Hex Intended use
  --------------------- ---------------------------- ---------------------
  `canvas`                                 `#101216` App background

  `surface-1`                              `#191E25` Sidebar and primary
                                                     panels

  `surface-2`                              `#222832` Elevated cards and
                                                     popovers

  `surface-3`                              `#2B333E` Hover, selected, and
                                                     nested surfaces

  `mars-orange`                            `#E56A3A` Primary actions,
                                                     active navigation,
                                                     selected route

  `amber`                                  `#F4B544` Secondary emphasis
                                                     and caution

  `cyan`                                   `#55C7D9` Data overlays,
                                                     coordinates,
                                                     technical highlights

  `safe-green`                             `#65B88A` Safe / feasible
                                                     status

  `warning-amber`                          `#EAB45B` Warning status

  `critical-red`                           `#E45C5C` Critical hazard /
                                                     blocked state

  `text-primary`                           `#F3F1ED` Main text

  `text-secondary`                         `#9AA5B1` Supporting text

  `text-muted`                             `#687482` Tertiary labels and
                                                     disabled content

  `line`                                   `#343C47` Borders, separators,
                                                     chart grids
  ------------------------------------------------------------------------

**Color rules**

-   Orange is reserved for the primary action, selected route, active
    navigation, and key focus states.
-   Amber means caution, not success.
-   Red is reserved for critical risk, blocked routes, and emergency
    states.
-   Cyan is informational and should not imply safety.
-   Status must never be communicated by color alone; pair color with
    text and/or an icon.
-   Keep map overlays translucent enough to preserve terrain visibility.

### Typography

Use a clean modern sans-serif family such as **Inter**, **IBM Plex
Sans**, or **Manrope**. Use one family throughout the application, with
optional condensed styling for large mission headings.

  Style       Suggested size   Weight Usage
  --------- ---------------- -------- -------------------------------------
  Display          32--40 px      600 Screen title / mission heading
  H1               26--30 px      600 Main page title
  H2               18--22 px      600 Panel heading
  H3               14--16 px      600 Card title
  Body                 14 px      400 Main interface copy
  Small                12 px      400 Supporting descriptions
  Micro            10--11 px      500 Eyebrows, map annotations, metadata
  Metric           24--32 px      600 Mission values

-   Use uppercase micro-labels with modest letter spacing for technical
    metadata.
-   Use tabular numerals for coordinates, distances, durations,
    percentages, and telemetry.
-   Keep body copy comfortably readable; do not use tiny futuristic
    display fonts for essential information.

### Shape, spacing, and depth

-   Base spacing scale: 4, 8, 12, 16, 20, 24, 32, 40, 48 px.
-   Panel radius: 10--12 px.
-   Compact control radius: 6--8 px.
-   Pills: use only for status and compact filters.
-   Borders: 1 px solid `line`; use borders more often than heavy
    shadows.
-   Shadows: subtle and limited to floating panels above the map.
-   Avoid excessive card nesting. Prefer one clear panel surface with
    internal dividers.

------------------------------------------------------------------------

## 3. Application shell

### Desktop layout

Target a 1440 × 900 desktop viewport as the primary design baseline.

-   **Sidebar:** 232 px fixed width; collapses to an icon rail at
    narrower desktop widths.
-   **Top bar:** 64 px high across the content area.
-   **Main content:** fluid width, 24 px outer padding, 20--24 px panel
    gaps.
-   **Map workspace:** expands to fill available height; map should
    remain the dominant surface.
-   **Content scroll:** main content scrolls independently from the
    sidebar where practical.

### Sidebar navigation

Include:

1.  DHRUVION wordmark and compact orbital/planet mark.
2.  Mission Overview
3.  Martian Map
4.  Route Planner
5.  Science Explorer
6.  Emergency Navigation
7.  AI Mission Assistant
8.  Mission Reports
9.  Settings

**Behavior and styling**

-   Active item: subtle orange-tinted surface, orange left indicator,
    warm-white label.
-   Inactive items: secondary text and restrained line icons.
-   Group the primary mission workflows separately from Settings.
-   Add a compact mission-status footer at the bottom of the sidebar.
-   On tablet, collapse labels into a narrow icon rail with tooltips.
-   On mobile, use a drawer or bottom navigation for the
    highest-priority destinations.

### Top navigation bar

Display:

-   Current mission name and mission identifier.
-   Selected region: **Gale Crater, Mars**.
-   Mission status badge.
-   Data-source / synchronization state.
-   Notifications.
-   Operator / astronaut profile.

The top bar should remain quiet and compact. Do not fill it with
decorative controls.

### Global data provenance

Every data-bearing screen should make it possible to identify whether
information is:

-   **Observed:** sourced from a named mission dataset or instrument.
-   **Derived:** calculated from source observations or a model.
-   **Simulated:** demonstration telemetry or a prototype scenario.

Use small provenance badges and a consistent information tooltip. For
simulated data, use explicit labels such as `SIMULATED SCENARIO` or
`PROTOTYPE VISUALIZATION`.

------------------------------------------------------------------------

## 4. Screen specifications

## Screen 1 --- Mission Overview

**Purpose:** Give the operator an immediate understanding of mission
status, current location, progress, and next decision.

### Layout

-   Page heading with mission name, region, and status.
-   Large hero panel with a Mars terrain visualization and current
    traverse.
-   Compact metric strip.
-   Lower two-column area for activity, terrain intelligence, science
    recommendation, alerts, and mission briefing.

### Hero terrain panel

-   Use a cinematic but legible Mars surface image or terrain rendering.
-   Overlay base / habitat marker, astronaut location, planned route,
    target marker, and hazard zones.
-   Include a small coordinate readout and a `OPEN MARTIAN MAP` action.
-   Keep image annotations minimal and high contrast.
-   Label any illustrative terrain image as a prototype visualization if
    it is not a real geospatial layer.

### Mission metrics

Show:

-   Mission phase and progress.
-   Mission time remaining.
-   Planned route distance.
-   Estimated outbound duration.
-   Estimated return duration.
-   Terrain difficulty.
-   Identified hazards.
-   Available science targets.

Each metric card includes a concise label, prominent tabular value,
unit, and optional trend or status. Do not invent live telemetry; use
clearly labeled demonstration values in prototypes.

### Supporting panels

-   **Mission activity timeline:** timestamp, event, category, and
    status.
-   **Terrain intelligence:** slope, roughness, elevation change, and
    nearby hazard summary.
-   **Recommended exploration target:** target name, feature type,
    priority, distance, and reason for recommendation.
-   **Recent alerts:** severity, concise message, timestamp, and link to
    relevant screen.
-   **AI mission briefing:** short structured summary with evidence
    links and a `VIEW ANALYSIS` action.

------------------------------------------------------------------------

## Screen 2 --- Interactive Martian Map

**Priority:** Highest. This is the central product workspace.

**Purpose:** Let operators inspect Mars terrain, understand the spatial
relationship between hazards and targets, and plan or review a traverse.

### Layout

-   Map canvas fills approximately 70--80% of the available content
    area.
-   Compact top map toolbar for search, coordinate jump, map mode, and
    reset view.
-   Floating layer panel on one side.
-   Floating legend and selected-feature inspector on the opposite side.
-   Bottom coordinate / scale strip.
-   Keep controls over the map without obscuring important terrain.

### Map visual language

-   Use a realistic Mars basemap: rust, ochre, charcoal, and muted sand
    terrain.
-   Terrain should show craters, ridges, channels, slopes, and
    geological texture.
-   Never use Earth road maps, terrestrial labels, or Earth geography.
-   If exact imagery is unavailable, use a convincing terrain
    placeholder and visibly label it `PROTOTYPE VISUALIZATION`.
-   Use a restrained dark vignette only where it improves label
    readability.

### Spatial objects

  -----------------------------------------------------------------------
  Object                              Visual treatment
  ----------------------------------- -----------------------------------
  Base / habitat                      Stable geometric marker with label

  Astronaut location                  High-contrast position marker with
                                      heading / orientation

  Science target                      Cyan or warm-white scientific
                                      marker, numbered when clustered

  Planned route                       Mars-orange polyline

  Selected route                      Brighter orange line with subtle
                                      outer stroke

  Alternative route                   Cyan dashed polyline

  Hazard zone                         Translucent red polygon with
                                      boundary

  Restricted area                     Muted red hatch or dashed boundary

  Crater / geological feature         Small text label with leader line
  -----------------------------------------------------------------------

Use different line styles and symbols as well as color so the map
remains understandable for color-vision deficiencies.

### Map controls

-   Zoom in / out.
-   Reset / fit to mission.
-   Pan / recenter on astronaut.
-   Coordinate search / go to coordinate.
-   Scale indicator.
-   Optional north / orientation indicator.

### Layer panel

Provide independent toggles for:

1.  Optical imagery
2.  Elevation / MOLA
3.  Slope analysis
4.  Terrain roughness
5.  THEMIS thermal layer
6.  Science targets
7.  Hazard overlay

Each layer row includes an icon, name, toggle, and optional opacity
control. Include a `RESET LAYERS` action.

### Legend

Explain visible symbols and overlays:

-   Base / habitat
-   Astronaut
-   Planned route
-   Alternative route
-   Science target
-   Hazard zone
-   Restricted area

### Feature inspector

When a map feature is selected, show a compact panel with:

-   Feature name and type.
-   Coordinates.
-   Relevant elevation / slope / roughness data where available.
-   Provenance badge.
-   Risk or science priority.
-   Related action: inspect target, add to route, or view source.

### Map interaction states

-   Default mission view.
-   Layer enabled / disabled.
-   Feature selected.
-   Route selected.
-   Hazard selected.
-   Coordinate search result.
-   Loading / unavailable imagery.
-   No matching feature.
-   Prototype visualization / simulated data.

------------------------------------------------------------------------

## Screen 3 --- Route Planner

**Purpose:** Compare candidate walking routes and choose a route that
balances distance, terrain risk, and mission time.

### Layout

-   Page title and mission context.
-   Route-configuration panel.
-   Three route comparison cards.
-   Map preview showing the selected route.
-   Detailed route profile and feasibility summary.

### Route inputs

-   Start location selector.
-   Destination selector.
-   Mission time limit.
-   Maximum allowable terrain difficulty.
-   Mission objective selector.

Inputs should have clear labels, sensible defaults where known, and
helper text for units or constraints.

### Route options

Provide three comparable route cards:

**Shortest Route** - Minimum distance. - Estimated traversal duration. -
Terrain difficulty score. - Hazard count. - Return-to-base
feasibility. - `SELECT ROUTE` action.

**Safest Route** - Lower estimated terrain risk. - Avoids identified
hazard zones. - May require additional travel time. - Same metrics and
action as other cards.

**Balanced Route** - Trade-off between distance and terrain
difficulty. - Same metrics and action as other cards.

### Comparison behavior

-   Cards use consistent metric order and scale.
-   Selected card has a clear border and selected label.
-   Show the selected route on the map.
-   Include a legend for selected and alternative routes.
-   Provide a concise explanation of why a route ranks as shortest,
    safest, or balanced.
-   Return feasibility must be explicit: `FEASIBLE`, `CAUTION`, or
    `NOT FEASIBLE`, with a supporting reason.
-   Never imply a route is safe solely because it is the shortest.

------------------------------------------------------------------------

## Screen 4 --- Science Explorer

**Purpose:** Help science planners discover, compare, and add geological
targets to the mission.

### Layout

-   Search and filter row.
-   Target list or compact target cards.
-   Map / terrain preview.
-   Target inspection panel.

### Target list fields

Each target should display:

-   Target name.
-   Coordinates.
-   Geological feature type.
-   Scientific exploration priority.
-   Estimated distance from current location.
-   Relevant NASA mission or instrument.
-   Available scientific evidence.
-   Provenance / confidence indicator.

### Filters

-   Geological feature type.
-   Priority.
-   Distance range.
-   Evidence / instrument.
-   Visited vs. unvisited.

### Target inspection panel

Include:

-   Geological image or terrain preview.
-   Target name and coordinates.
-   Scientific context.
-   Available evidence and source.
-   Why the target is worth visiting.
-   Estimated traverse impact.
-   `ADD TO MISSION` action.

Use a clear distinction between observed geological features and
scientific interpretations.

------------------------------------------------------------------------

## Screen 5 --- Emergency Navigation

**Purpose:** Support fast, deliberate response when a planned route is
blocked or a terrain hazard changes mission feasibility.

### Visual tone

This screen should feel more serious and operational than the other
pages. Increase the prominence of status and decision information, but
do not use flashing effects or alarm-like decoration.

### Emergency scenario panel

Include:

-   Clearly labeled simulated blocked route, if not based on real
    mission data.
-   Terrain hazard alert and hazard type.
-   Remaining mission time.
-   Astronaut-to-base distance.
-   Alternative route availability.
-   Return feasibility status.

### Primary action

Use the exact action label:

**GENERATE SAFE ALTERNATIVE ROUTE**

The action must be visually prominent, keyboard accessible, and
protected against accidental activation if it triggers a consequential
workflow.

### After route generation

Show:

-   Original route marked as blocked.
-   Alternative route highlighted.
-   Changed distance and duration.
-   Reason for rerouting.
-   Mission feasibility assessment.
-   Evidence / data sources used.

Use a before-and-after route comparison. Explain trade-offs in plain
operational language. Clearly mark all simulated telemetry and emergency
scenarios.

### Status treatment

-   Blocked: critical red, explicit `BLOCKED` label.
-   Caution: amber, explicit `CAUTION` label.
-   Feasible: muted green, explicit `FEASIBLE` label.
-   Unknown: neutral gray, explicit `UNVERIFIED` label.

------------------------------------------------------------------------

## Screen 6 --- AI Mission Assistant

**Purpose:** Provide mission-aware recommendations backed by application
tools, geospatial data, and scientific evidence.

### Design direction

Do not design this as a generic chatbot. It is a **Mission Intelligence
Console** embedded in the workflow.

### Layout

-   Main conversation / analysis panel.
-   Mission context sidebar.
-   Suggested command chips.
-   Structured result cards.
-   Visible tool and data activity.

### Example astronaut queries

-   "Find the safest route to the geological target."
-   "Can I reach this target and return before my mission time expires?"
-   "Which nearby geological formations are worth investigating?"
-   "An obstacle has blocked my current path. Find an alternative."

### Mission context sidebar

Show relevant current context:

-   Mission and region.
-   Current location.
-   Mission time remaining.
-   Active route.
-   Current objective.
-   Active hazards.
-   Selected map layers.

### Structured assistant response

Responses should be composed from clear sections:

1.  **Recommendation**
2.  **Supporting evidence**
3.  **Route details**
4.  **Warnings**
5.  **Data sources**
6.  **Available actions**

### Tool transparency

Show when the assistant is:

-   Checking terrain layers.
-   Evaluating slope and roughness.
-   Inspecting hazard overlays.
-   Comparing routes.
-   Checking return feasibility.
-   Retrieving scientific target evidence.

Distinguish tool-derived results from generated explanatory text.
Include source names, timestamps or dataset identifiers when available.
Do not imply that a tool was used if no tool call occurred.

### Suggested actions

-   View route on map.
-   Compare alternatives.
-   Add target to mission.
-   Open source data.
-   Recalculate feasibility.

------------------------------------------------------------------------

## Screen 7 --- Mission Reports

**Purpose:** Provide a professional, traceable summary of a mission or
traverse for review and handoff.

### Header

-   Mission name and identifier.
-   Exploration region.
-   Mission date / reporting period.
-   Mission status.
-   Export report action.

### Report sections

-   Mission objectives.
-   Selected exploration region.
-   Route summary.
-   Terrain analysis.
-   Science targets visited.
-   Estimated distance and duration.
-   Hazards encountered.
-   Emergency rerouting history.
-   Data sources used.

### Presentation

-   Use a clear report hierarchy with section headings and compact data
    tables.
-   Include a route map snapshot and terrain profile where available.
-   Show planned vs. actual values only when both are available.
-   Mark estimated and simulated values explicitly.
-   Include provenance for scientific observations and derived metrics.
-   Provide export feedback and a printable layout.

------------------------------------------------------------------------

## 5. Reusable component library

Build a consistent component system shared across all screens.

  -----------------------------------------------------------------------
  Component                           Requirements
  ----------------------------------- -----------------------------------
  Sidebar navigation                  Active, inactive, collapsed, hover,
                                      keyboard-focus states

  Top navigation                      Mission context, status, sync,
                                      notifications, profile

  Metric card                         Label, tabular value, unit,
                                      optional status / delta

  Map layer control                   Toggle, optional opacity, disabled
                                      / unavailable state

  Map legend item                     Symbol, label, concise description

  Mission status indicator            Safe, caution, critical, inactive,
                                      simulated

  Route comparison card               Name, metrics, feasibility,
                                      selected state, action

  Hazard indicator                    Severity, type, location, status

  Science target card                 Name, feature type, priority,
                                      distance, source

  AI response card                    Recommendation, evidence, warnings,
                                      actions

  Data source badge                   Observed, derived, simulated,
                                      unavailable

  Timeline item                       Timestamp, event, category,
                                      severity

  Confirmation dialog                 Clear consequence, cancel, confirm

  Button                              Primary, secondary, tertiary,
                                      destructive, disabled, loading

  Form control                        Default, focus, error, disabled,
                                      helper text

  Empty state                         Clear explanation and useful next
                                      action

  Loading state                       Quiet progress indicator and
                                      contextual label

  Error state                         Plain-language issue, recovery
                                      action, source if relevant
  -----------------------------------------------------------------------

### Button hierarchy

-   **Primary:** Mars orange fill with warm-white text; one primary
    action per major panel.
-   **Secondary:** transparent or graphite surface with border.
-   **Tertiary:** text-only for low-emphasis actions.
-   **Destructive:** restrained red treatment, reserved for irreversible
    or critical actions.
-   **Disabled:** low-contrast but still readable; explain why
    unavailable when useful.

### Icons

Use a consistent outline icon family. Icons should be simple,
recognizable, and paired with labels for mission-critical actions. Avoid
decorative icon clusters.

------------------------------------------------------------------------

## 6. Interaction and motion

-   Keep transitions short and purposeful (roughly 150--220 ms).
-   Use subtle fades and position changes for panel transitions.
-   Route selection should update the map and route summary together.
-   Layer toggles should update the map and legend in sync.
-   Selecting a target on the map should open the matching inspector.
-   Selecting a route card should highlight the corresponding map route.
-   Emergency rerouting should present a clear before / after state.
-   Provide visible keyboard focus and support keyboard navigation.
-   Respect reduced-motion preferences.
-   Do not use pulsing or flashing animations for critical alerts.

------------------------------------------------------------------------

## 7. Responsive behavior

### Desktop (1280 px and above)

-   Full sidebar and top navigation.
-   Multi-column dashboards.
-   Large map canvas with floating controls and inspector.
-   Route cards displayed side by side.

### Tablet (768--1279 px)

-   Collapsible sidebar / icon rail.
-   Reduce dashboard columns to two, then one as needed.
-   Map controls become compact drawers or anchored panels.
-   Route cards may stack or become horizontally scrollable.

### Mobile (below 768 px)

-   Use a navigation drawer or compact bottom navigation.
-   Prioritize map, current position, route, and emergency action.
-   Convert side panels into bottom sheets.
-   Stack metric cards in a compact grid.
-   Keep important actions reachable without covering the map.
-   Use touch targets of at least 44 × 44 px.
-   Avoid dense multi-column data tables; use stacked key-value rows.

------------------------------------------------------------------------

## 8. Accessibility and usability

-   Meet WCAG AA contrast for essential text and controls.
-   Never use color as the only status signal.
-   Use clear labels and accessible names for icon-only controls.
-   Maintain visible keyboard focus.
-   Support keyboard navigation through menus, dialogs, and map
    controls.
-   Provide text alternatives or summaries for map-only information.
-   Use readable type sizes and adequate line height.
-   Use tabular numerals for values that need comparison.
-   Keep warning messages concise and action-oriented.
-   Provide empty, loading, warning, unavailable, and error states.
-   Ensure the interface remains usable at 200% zoom.

------------------------------------------------------------------------

## 9. Data integrity and content rules

-   Do not invent live mission telemetry.
-   Clearly label demonstration values as simulated.
-   Distinguish observed measurements from derived estimates and model
    outputs.
-   Name NASA missions, instruments, and datasets only when the
    underlying data is actually used.
-   Do not fabricate citations, dataset identifiers, timestamps, or
    scientific confidence values.
-   Show units for all distances, durations, coordinates, and
    measurements.
-   Use consistent coordinate formatting throughout the product.
-   When data is missing or stale, say so rather than displaying a
    plausible-looking value.
-   Explain route feasibility using the inputs and constraints that
    produced the assessment.

------------------------------------------------------------------------

## 10. Suggested information architecture

``` text
DHRUVION
├── Mission Overview
│   ├── Mission status
│   ├── Terrain overview
│   ├── Mission metrics
│   ├── Activity timeline
│   ├── Alerts
│   └── Mission briefing
├── Martian Map
│   ├── Map canvas
│   ├── Map layers
│   ├── Legend
│   ├── Feature inspector
│   └── Coordinate search
├── Route Planner
│   ├── Route inputs
│   ├── Shortest route
│   ├── Safest route
│   ├── Balanced route
│   └── Feasibility comparison
├── Science Explorer
│   ├── Target discovery
│   ├── Filters
│   └── Target inspection
├── Emergency Navigation
│   ├── Hazard status
│   ├── Blocked route
│   ├── Alternative route
│   └── Return feasibility
├── AI Mission Assistant
│   ├── Conversation
│   ├── Mission context
│   ├── Tool activity
│   └── Structured recommendations
├── Mission Reports
│   ├── Mission summary
│   ├── Terrain analysis
│   ├── Science log
│   ├── Hazard / reroute history
│   └── Export
└── Settings
    ├── Display preferences
    ├── Units and coordinates
    └── Data / source preferences
```

------------------------------------------------------------------------

## 11. Prototype acceptance checklist

### Visual quality

-   [ ] The interface feels like a premium planetary mission-control
    product.
-   [ ] Mars terrain is the dominant visual element on the map screen.
-   [ ] The dark graphite / Mars-orange palette is applied consistently.
-   [ ] Typography, spacing, borders, and radii are consistent.
-   [ ] Decorative HUD elements do not interfere with legibility.

### Workflow coverage

-   [ ] All seven application screens are represented.
-   [ ] Sidebar navigation clearly identifies the active screen.
-   [ ] Route cards and map routes stay synchronized.
-   [ ] Map layer toggles and legend stay synchronized.
-   [ ] Science targets can be inspected and added to a mission.
-   [ ] Emergency rerouting shows blocked and alternative paths.
-   [ ] AI responses show evidence, sources, warnings, and actions.
-   [ ] Mission reports include the required summary sections.

### Trust and accessibility

-   [ ] Observed, derived, and simulated data are visually distinct.
-   [ ] No fabricated telemetry is presented as live.
-   [ ] Status is not communicated by color alone.
-   [ ] Keyboard focus and accessible labels are present.
-   [ ] Loading, empty, warning, and error states are designed.
-   [ ] Responsive layouts work on desktop, tablet, and mobile.

------------------------------------------------------------------------

## 12. Design north star

**DHRUVION should look and behave like a real mission tool for
understanding and navigating the Martian surface.** The cinematic
references provide atmosphere; the aerospace and instrumentation
references provide precision; the product workflow provides purpose. The
map, evidence, route feasibility, and operator decisions must always
take priority over visual spectacle.

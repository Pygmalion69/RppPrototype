# RPP Prototype — Deterministic Start Point via CLI Argument

## Summary
Today the start point of the Rural Postman Problem (RPP) route export is **arbitrary**: `nx.eulerian_circuit(E, keys=True)` is called **without** a `source` argument, so NetworkX selects an arbitrary start node (effectively the first node in `E`'s internal order). This order depends on how edges are added (required edges, then connectors, then duplicates), not on geography.

We want to make the route start **deterministic and user-controllable** by adding a CLI argument for a *requested* starting coordinate. The *actual* start node must be the **closest connected node** to that coordinate in the routing graph/component.

---

## Problem Statement
- The current GPX export begins at an arbitrary node because `nx.eulerian_circuit` is invoked without `source`.
- This makes runs non-intuitive (start location may be far from the user’s area of interest) and can vary if edge insertion order changes.

**Screenshot context**: `RppRouteExport.gpx()` (or equivalent) calls `nx.eulerian_circuit(E, keys=True)` and NetworkX chooses an arbitrary start node.

---

## Goals / Requirements

### Functional requirements
1. **Add CLI argument for requested start point**
   - Add a new command-line argument to the RPP prototype, e.g.:
     - `--start "lat,lon"` **or** `--start-lat <float> --start-lon <float>`.
   - The argument is optional; if omitted, preserve current behavior (arbitrary start) **or** use a deterministic fallback (see below).

2. **Snap requested start to a valid graph node**
   - Compute the *actual* start node as the node in the chosen routing component whose geographic position is closest to the *requested* start coordinate.
   - Distance metric can be:
     - Haversine (recommended), or
     - Euclidean approximation (acceptable for small areas).
   - Node coordinate source:
     - Prefer OSMnx-style node attrs: `x` = lon, `y` = lat.
     - If your project uses different attribute names (e.g., `lat`, `lon`), adapt accordingly.

3. **Respect connectivity (“connected node”)**
   - The node must be connected to the graph/component used for routing.
   - Avoid snapping into disconnected islands.
   - At minimum:
     - Choose the **largest connected component** of the routing graph (or weakly-connected if DiGraph).
   - Preferably (if you already have a “main” component containing the majority of required edges):
     - Choose the component that contains **most required edges**.

4. **Pass chosen start node to Eulerian circuit**
   - Call:
     - `nx.eulerian_circuit(E, source=chosen_node, keys=True)`
   - `E` must be the Eulerized graph used for the final circuit.

5. **Diagnostics / logging**
   - Print/log:
     - requested start (lat,lon),
     - chosen node id,
     - snapped node coordinates,
     - snap distance in meters,
     - which component selection strategy was used (largest component vs required-edges component).

### Non-functional requirements
- Deterministic given same input graph and same start coordinate.
- Performance: snapping should be efficient enough for typical region sizes.
  - A simple O(N) scan over nodes is acceptable initially.
  - Optional improvement: spatial index (KDTree / BallTree / OSMnx nearest_nodes).
- Backward compatible: existing runs without `--start` must still work.

---

## Proposed CLI
Choose one style (either is fine):

### Option A: single parameter
- `--start "51.6902,6.1213"`

### Option B: separate parameters
- `--start-lat 51.6902 --start-lon 6.1213`

Optional extras (future-proofing, not required now):
- `--start-mode {arbitrary,nw_corner,nearest}` (default: `nearest` when `--start` given)
- `--component-mode {largest,required_edges}` (default: `largest`)

---

## Acceptance Criteria
1. Running the tool with the same dataset and the same `--start` yields the same first GPX point across repeated runs.
2. The first point of the exported GPX corresponds to:
   - the chosen graph node, and
   - is the closest connected node to the requested coordinate (within the selected component).
3. When the requested coordinate is near a disconnected subgraph, the chosen node is still in the main routing component (per component selection strategy).
4. The Eulerian circuit is generated using `source=chosen_node` and starts there.
5. The program prints the requested vs snapped start information including snap distance.

---

## Implementation Notes (for Codex)

### Where to change
- Locate the call site that currently does:
  - `nx.eulerian_circuit(E, keys=True)`
- Likely in:
  - `rpp/gpx_export.py` and/or `rpp/rpp_solver.py` (as mentioned in the screenshot commentary).
- Add CLI parsing (probably in `main.py` or your existing argparse module), propagate the chosen node to the export/solver layer.

### Component selection
- If `G` is an undirected `nx.Graph`:
  - `nx.connected_components(G)`
- If `G` is a `nx.DiGraph`:
  - `nx.weakly_connected_components(G)` (usually best for road networks)

### Snapping
- Minimal approach: scan all nodes in the chosen component and compute distance to requested point.
- If OSMnx is already in the project:
  - consider `osmnx.distance.nearest_nodes(G, X=lon, Y=lat)` but ensure you pass a graph restricted to the chosen component.

### Edge cases
- If `--start` is provided but snapping yields no node (e.g. missing coords):
  - raise a clear error explaining missing node coordinate attributes.
- If `--start` omitted:
  - either keep current arbitrary behavior **or**
  - compute a deterministic fallback (e.g. north-west-most node in the chosen component).

---

## Test Plan
1. **Unit test**: small synthetic graph with known node coordinates and two components.
   - Provide a requested start near the smaller component; ensure chosen node is in the selected main component.
2. **Integration test**: run on a known OSM extract.
   - Compare first GPX point with expected snapped node.
3. **Regression test**: run without `--start` and confirm existing behavior (or chosen deterministic fallback) remains valid and documented.

---

## Definition of Done
- New CLI argument added and documented (`--help` output updated).
- Start node snapping implemented and used in Eulerian circuit.
- Logs show requested vs actual start and snap distance.
- Tests added for snapping + component behavior.

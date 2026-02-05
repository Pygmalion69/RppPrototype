# Rural Postman Problem (RPP) Solver Prototype

A Python-based tool to solve the Rural Postman Problem (RPP) on OpenStreetMap (OSM) data.
It identifies a set of required edges (for example, residential streets) and calculates an
Eulerian circuit that covers all of them with minimum total cost, exporting the result as a
GPX file.

## Features
- **Graph loading and filtering**: imports OSM data using `osmnx`/`networkx`, filters out
  non-driveable edges (e.g., footways, cycleways, private access), and keeps the largest
  connected component.
- **Required-edge selection**: required service streets include `residential`,
  `living_street`, `tertiary`, and `unclassified`.
- **Undirected and directed solvers**:
  - Undirected solver connects required components and fixes odd-degree nodes via
    min-weight matching.
  - Directed solver respects one-way restrictions for both routing and required arcs,
    balancing in/out degree with min-cost flow.
- **Directed preflight + diagnostics**: validates required nodes against the drive graph,
  checks strongly connected components, and can emit a DRPP diagnostics report or a GPX
  file of blocking required edges.
- **GPX export**: generates a GPX route with edge geometry for navigation.
- **Geometry-preserving edge selection**: prefers OSM edges with geometry when building the
  Eulerian multigraph to avoid straight-line fallbacks.

## Usage
Run the main script to process the sample data:
```bash
python main.py
```

### Common options
```bash
python main.py --osm data/area.osm
```

- `--osm`: path to an `.osm` file (defaults to `data/area.osm`).
- `--ignore-oneway`: treats one-way streets as bidirectional for shortest-path routing.
- `--directed-service`: uses the directed service graph and the directed solver for
  required arcs, fully respecting one-way restrictions.
- `--drpp-diagnostics`: writes a DRPP diagnostics report (SCC sizes, required nodes/edges
  outside the largest SCC, and cross-SCC required edges).
- `--drop-drpp-blockers`: removes required edges that fall outside the largest SCC before
  solving the directed problem.
- `--drpp-blockers-gpx`: writes blocking required edges to a GPX file (useful for inspection
  before dropping them).
- `--visualize`: writes an HTML visualization of the solution route (street/segment tables).

The solver writes `rpp_route.gpx` in the current directory.

## Tests
Run the unit tests with:
```bash
pytest
```

### Sample
https://github.com/user-attachments/assets/3958631c-9b01-4edf-b342-266f00c53466

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
- **GPX export**: generates a GPX route with edge geometry for navigation.

## Requirements
- Python 3.10+
- Dependencies: `osmnx`, `networkx`, and `gpxpy` (install via pip).

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

The solver writes `rpp_route.gpx` in the current directory.

## Tests
Run the unit tests with:
```bash
pytest
```

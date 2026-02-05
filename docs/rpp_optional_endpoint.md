# RPP Prototype — Optional End Point Support (Undirected & Directed)

## Context
The current RPP prototype always produces a **closed Eulerian circuit**:
- all required streets (edges/arcs) are covered,
- start and end coincide,
- the start location is arbitrary unless explicitly provided.

We already plan to add a **start point** via CLI snapping.
This document specifies how to add an **optional end point**, allowing the route to:
- start at a chosen location, and
- finish at a *different* chosen location,
while **still covering all required streets**.

Edge coverage (not node coverage) is the objective.

---

## High-level behavior

### CLI
Add an optional end point:
- `--start "lat,lon"`
- `--end "lat,lon"`

Rules:
- No `--end` → **closed route** (Eulerian circuit).
- `--end` provided and `end != start` → **open route** (Eulerian path/trail).
- `--end == --start` → treated as closed route.

Both start and end are snapped to valid, connected graph nodes.

---

## Undirected RPP (`solve_rpp`)

### Goal
Produce:
- **Eulerian circuit** if no end point is given.
- **Eulerian path** from `start_node` to `end_node` if an end point is given.

### Key idea
In an undirected graph:
- Eulerian circuit → all degrees even.
- Eulerian path → exactly **two odd-degree nodes** (start and end).

### Algorithmic change
After building the Eulerian multigraph `E`:

1. Compute odd-degree nodes:
```python
odd = {n for n in E.nodes if E.degree(n) % 2 == 1}
```

2. If open route requested:
```python
odd ^= {start_node, end_node}
```

3. Run minimum-weight matching on this adjusted set.

### Validation
- Closed route: `nx.is_eulerian(E)`
- Open route: odd nodes are exactly `{start_node, end_node}`

### Traversal
- Closed: `nx.eulerian_circuit(E, source=start_node, keys=True)`
- Open: `nx.eulerian_path(E, source=start_node, keys=True)`

---

## Directed RPP (`solve_drpp`)

### Goal
Produce:
- Eulerian directed circuit, or
- Eulerian directed path from `start_node` to `end_node`.

### Directed degree conditions
- start: `out − in = +1`
- end: `out − in = −1`
- others: `0`

### Algorithmic change
After building `E`:

1. Compute imbalance:
```python
delta = {n: E.out_degree(n) - E.in_degree(n) for n in E.nodes}
```

2. If open route requested:
```python
delta[start_node] -= 1
delta[end_node]   += 1
```

3. Run existing min-cost flow imbalance repair.

### Validation
- Closed: balanced everywhere.
- Open: only start/end have imbalance.

### Traversal
- Closed: `nx.eulerian_circuit(E, source=start_node, keys=True)`
- Open: `nx.eulerian_path(E, source=start_node, keys=True)`

---

## Snapping start and end points

- Undirected: snap within chosen connected component.
- Directed: snap within SCC compatible with required arcs.

Log requested vs snapped coordinates and snap distance.

---

## Acceptance Criteria
1. Deterministic start with `--start`.
2. Open route with `--start` + `--end`.
3. All required streets covered.
4. Endpoint-aware matching / imbalance repair.
5. Deterministic results.

---

## Definition of Done
- CLI supports `--end`.
- Solvers accept optional `start_node` / `end_node`.
- Correct circuit vs path traversal.

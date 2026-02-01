# Implementation Instructions for Directed Rural Postman Support

This document describes the tasks required to extend the `feature/one-way` branch of **RppPrototype**
so that the Rural Postman solver fully respects one-way restrictions not only for path lengths but also
for the **service edges themselves**.

The current branch already provides:
- a **directed driving graph**, and
- an **undirected service graph**,

so shortest paths already respect one-way streets. However, the required edges are still treated as
undirected and the solver still performs Christofides-style matching on an undirected multigraph.

To implement a **fully directed Rural Postman solver**, follow the steps below.

---

## 1. Extend the graph loader

### Goal
Expose both directed and undirected representations of the service graph.

### Current state
`rpp/graph_loader.py` already:
- loads a filtered `MultiDiGraph` (`G_filt`)
- produces a directed or undirected **driving graph** depending on `ignore_oneway`

This behaviour for the driving graph must be preserved.

### Required changes

Modify `load_graphs` to return **three graphs**:

- **`G_drive`**  
  Directed or undirected depending on `ignore_oneway` (unchanged).

- **`G_service_undirected`**  
  The existing undirected graph used for geometry lookup (unchanged).

- **`G_service_directed`**  
  A new directed service graph used to build the required graph.

Implementation note:
```python
G_service_directed = G_filt
```

Since `G_filt` is already a directed multigraph, this preserves:
- `length`
- `geometry`
- `highway`
- all other edge attributes

---

## 2. Build a directed required graph

### Current state
`rpp/required_edges.py` constructs an **undirected** graph `R` by scanning the service graph and
selecting edges whose `highway` tag is in `REQUIRED_HIGHWAYS`.

### Required changes

Replace the existing logic with **two functions**:

### 2.1 Undirected required graph (unchanged)
```python
build_required_graph_undirected(G_service_undirected) -> nx.Graph
```

- Keep existing behaviour
- Maintains backward compatibility

### 2.2 Directed required graph (new)
```python
build_required_graph_directed(G_service_directed) -> nx.DiGraph
```

Implementation details:
- Iterate over arcs `(u, v, key, data)` in `G_service_directed`
- For each arc:
  - `is_driveable_edge(data)` must be `True`
  - `data["highway"]` must be in `REQUIRED_HIGHWAYS`
- Add a **directed** arc `(u, v)` with the same weight
- **Do not** automatically add the reverse arc

Important:
> If a street is truly two-way in OSM, both directions will already be present in
> `G_service_directed` and will therefore be added independently.

---

## 3. Implement a directed RPP solver

### New solver entry point
Create a new function in `rpp/rpp_solver.py`:

```python
solve_drpp(
    G_drive: nx.MultiDiGraph,
    G_service_directed: nx.MultiDiGraph,
    R: nx.DiGraph,
) -> nx.MultiDiGraph
```

### 3.1 Connect required components

1. Compute **strongly connected components** of `R`
2. If there is only one component, skip this step
3. Otherwise:
   - Choose one representative vertex per component
   - For each consecutive pair `(C_i, C_{i+1})`:
     - Find the shortest **directed** path in `G_drive`
     - Use `nx.single_source_dijkstra`
     - If no path exists, try the reverse direction
     - If neither direction exists, raise `RuntimeError`
4. Store all connector paths for later insertion

### 3.2 Build the service multigraph

Create an empty directed multigraph:
```python
E = nx.MultiDiGraph()
```

Populate it as follows:
- Required arcs → `kind="required"`
- Connector arcs → `kind="connector"`

### 3.3 Compute vertex imbalances

For each vertex `v`:
```python
delta[v] = out_degree(v) - in_degree(v)
```

Define:
- `D_plus  = { v | delta[v] > 0 }`
- `D_minus = { v | delta[v] < 0 }`

### 3.4 Construct the cost matrix

For each `(i, j)` with:
- `i ∈ D_minus`
- `j ∈ D_plus`

Compute the shortest directed path in `G_drive`.
Cache both path and cost.

### 3.5 Solve the min-cost flow problem

- Build bipartite graph `D_minus → D_plus`
- Edge cost = shortest path cost
- Demands:
  - `D_minus`: negative
  - `D_plus`: positive

Solve with:
```python
networkx.algorithms.flow.min_cost_flow
```

### 3.6 Duplicate balancing paths

For each `(i, j)` where `flow[i][j] > 0`:
- Insert the cached path `flow[i][j]` times
- Mark arcs with `kind="duplicate"`

### 3.7 Eulerian verification and tour

- Assert `out_degree == in_degree` for all vertices
- Verify `nx.is_eulerian(E)`
- Compute:
```python
nx.eulerian_circuit(E, keys=True)
```

Return `E`.

---

## 4. CLI integration

- Add `--directed-service` flag
- Choose solver based on flag
- Export using existing GPX logic (direction-aware)

---

## 5. Testing

- Unit tests on toy directed graphs
- Regression tests for undirected mode
- Real OSM validation on one-way streets

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Dict, Iterable, List

import networkx as nx


@dataclass(frozen=True)
class VisualizationEdge:
    source: str
    target: str
    label: str


def visualize_solution(
    E: nx.Graph,
    G_service: nx.Graph,
    output_path: str,
) -> None:
    """
    Write an HTML file with a Mermaid flowchart of the Eulerian circuit.

    The visualization renders the traversed sequence of nodes with labeled arrows
    (required/connector/duplicate) so the route order is explicit.
    """
    circuit = list(nx.eulerian_circuit(E))
    if not circuit:
        raise RuntimeError("Eulerian circuit is empty; cannot visualize solution.")

    node_labels = _build_node_labels(circuit)
    edges = _build_edges(circuit, E)
    sequence = _build_sequence(circuit)

    html = _render_html(node_labels, edges, sequence, G_service.graph.get("crs"))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def _build_node_labels(circuit: Iterable[tuple]) -> Dict[str, str]:
    unique_nodes: List[int] = []
    for u, v in circuit:
        if u not in unique_nodes:
            unique_nodes.append(u)
        if v not in unique_nodes:
            unique_nodes.append(v)
    return {f"n{idx}": str(node) for idx, node in enumerate(unique_nodes)}


def _build_edges(
    circuit: Iterable[tuple],
    E: nx.Graph,
) -> List[VisualizationEdge]:
    node_map: Dict[int, str] = {}
    for idx, node in enumerate(_collect_nodes(circuit)):
        node_map[node] = f"n{idx}"

    edges: List[VisualizationEdge] = []
    for idx, (u, v) in enumerate(circuit, start=1):
        data = _edge_data(E, u, v)
        label = f"{idx}: {data.get('kind', 'route')}"
        edges.append(VisualizationEdge(node_map[u], node_map[v], label))
    return edges


def _build_sequence(circuit: Iterable[tuple]) -> List[int]:
    nodes = []
    for u, v in circuit:
        if not nodes:
            nodes.append(u)
        nodes.append(v)
    return nodes


def _collect_nodes(circuit: Iterable[tuple]) -> List[int]:
    nodes: List[int] = []
    for u, v in circuit:
        if u not in nodes:
            nodes.append(u)
        if v not in nodes:
            nodes.append(v)
    return nodes


def _edge_data(E: nx.Graph, u: int, v: int) -> dict:
    data = E.get_edge_data(u, v)
    if isinstance(E, (nx.MultiGraph, nx.MultiDiGraph)):
        if not data:
            return {}
        first_key = next(iter(data))
        return data[first_key]
    return data or {}


def _render_html(
    node_labels: Dict[str, str],
    edges: List[VisualizationEdge],
    sequence: List[int],
    crs: str | None,
) -> str:
    mermaid_lines = ["flowchart LR"]
    for node_id, label in node_labels.items():
        mermaid_lines.append(f'  {node_id}["{escape(label)}"]')
    for edge in edges:
        mermaid_lines.append(
            f'  {edge.source} -->|"{escape(edge.label)}"| {edge.target}'
        )

    mermaid_diagram = "\n".join(mermaid_lines)
    sequence_text = " → ".join(escape(str(node)) for node in sequence)
    crs_text = escape(crs) if crs else "unknown"

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>RPP Solution Visualization</title>
    <style>
      body {{
        font-family: Arial, sans-serif;
        margin: 24px;
        color: #1f2a37;
        background: #f8fafc;
      }}
      .panel {{
        background: #ffffff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
        margin-bottom: 20px;
      }}
      .sequence {{
        font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        font-size: 13px;
        line-height: 1.6;
        word-break: break-word;
      }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
      mermaid.initialize({{ startOnLoad: true }});
    </script>
  </head>
  <body>
    <div class="panel">
      <h1>RPP Solution Visualization</h1>
      <p>Coordinate reference system: <strong>{crs_text}</strong></p>
    </div>
    <div class="panel">
      <h2>Eulerian Circuit Graph</h2>
      <div class="mermaid">
{mermaid_diagram}
      </div>
    </div>
    <div class="panel">
      <h2>Node Traversal Sequence</h2>
      <div class="sequence">{sequence_text}</div>
    </div>
  </body>
</html>
"""

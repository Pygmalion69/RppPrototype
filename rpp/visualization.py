from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Dict, Iterable, List, Tuple

import networkx as nx


@dataclass(frozen=True)
class SegmentRow:
    index: int
    start: int
    end: int
    street: str
    kind: str
    distance: float


def visualize_solution(
    E: nx.Graph,
    G_service: nx.Graph,
    output_path: str,
) -> None:
    """
    Write an HTML file with a per-segment overview of the Eulerian circuit.

    The visualization renders the ordered list of traversed segments (street name,
    edge kind, and distance) plus a summary grouped by street.
    """
    circuit = list(nx.eulerian_circuit(E))
    if not circuit:
        raise RuntimeError("Eulerian circuit is empty; cannot visualize solution.")

    segments = _build_segments(circuit, E, G_service)
    summary = _summarize_by_street(segments)

    html = _render_html(segments, summary, G_service.graph.get("crs"))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

def _build_segments(
    circuit: Iterable[tuple],
    E: nx.Graph,
    G_service: nx.Graph,
) -> List[SegmentRow]:
    segments: List[SegmentRow] = []
    for idx, (u, v) in enumerate(circuit, start=1):
        e_data = _edge_data(E, u, v)
        kind = str(e_data.get("kind", "route"))
        distance = float(e_data.get("weight", 0.0))
        street = _street_name(G_service, u, v)
        segments.append(SegmentRow(idx, u, v, street, kind, distance))
    return segments


def _summarize_by_street(segments: List[SegmentRow]) -> List[Tuple[str, int, float, str]]:
    summary: Dict[str, Dict[str, object]] = {}
    for segment in segments:
        entry = summary.setdefault(
            segment.street,
            {"count": 0, "distance": 0.0, "kinds": set()},
        )
        entry["count"] = int(entry["count"]) + 1
        entry["distance"] = float(entry["distance"]) + segment.distance
        entry["kinds"].add(segment.kind)

    ordered = sorted(
        summary.items(), key=lambda item: (-item[1]["count"], item[0].lower())
    )
    return [
        (
            street,
            int(values["count"]),
            float(values["distance"]),
            ", ".join(sorted(values["kinds"])),
        )
        for street, values in ordered
    ]


def _edge_data(E: nx.Graph, u: int, v: int) -> dict:
    data = E.get_edge_data(u, v)
    if isinstance(E, (nx.MultiGraph, nx.MultiDiGraph)):
        if not data:
            return {}
        first_key = next(iter(data))
        return data[first_key]
    return data or {}


def _render_html(
    segments: List[SegmentRow],
    summary: List[Tuple[str, int, float, str]],
    crs: str | None,
) -> str:
    crs_text = escape(crs) if crs else "unknown"
    segment_rows = "\n".join(_render_segment_row(segment) for segment in segments)
    summary_rows = "\n".join(
        _render_summary_row(street, count, distance, kinds)
        for street, count, distance, kinds in summary
    )

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
      table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
      }}
      th,
      td {{
        border-bottom: 1px solid #e2e8f0;
        padding: 8px 10px;
        text-align: left;
      }}
      th {{
        background: #f1f5f9;
        font-weight: 600;
      }}
      .mono {{
        font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        font-size: 12px;
      }}
    </style>
  </head>
  <body>
    <div class="panel">
      <h1>RPP Solution Visualization</h1>
      <p>Coordinate reference system: <strong>{crs_text}</strong></p>
    </div>
    <div class="panel">
      <h2>Street Summary</h2>
      <table>
        <thead>
          <tr>
            <th>Street</th>
            <th>Segment Count</th>
            <th>Total Distance</th>
            <th>Kinds</th>
          </tr>
        </thead>
        <tbody>
          {summary_rows}
        </tbody>
      </table>
    </div>
    <div class="panel">
      <h2>Segment-by-Segment Route</h2>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>From</th>
            <th>To</th>
            <th>Street</th>
            <th>Kind</th>
            <th>Distance</th>
          </tr>
        </thead>
        <tbody>
          {segment_rows}
        </tbody>
      </table>
    </div>
  </body>
</html>
"""


def _street_name(G_service: nx.Graph, u: int, v: int) -> str:
    data = G_service.get_edge_data(u, v)
    if not data and G_service.is_directed():
        data = G_service.get_edge_data(v, u)
    if not data:
        return "unnamed"
    if isinstance(G_service, (nx.MultiGraph, nx.MultiDiGraph)):
        candidate = next(iter(data.values()))
    else:
        candidate = data
    name = candidate.get("name")
    if isinstance(name, list):
        name = ", ".join(str(part) for part in name if part)
    return str(name) if name else "unnamed"


def _render_segment_row(segment: SegmentRow) -> str:
    return (
        "          <tr>"
        f"<td class=\"mono\">{segment.index}</td>"
        f"<td class=\"mono\">{escape(str(segment.start))}</td>"
        f"<td class=\"mono\">{escape(str(segment.end))}</td>"
        f"<td>{escape(segment.street)}</td>"
        f"<td>{escape(segment.kind)}</td>"
        f"<td class=\"mono\">{segment.distance:.2f}</td>"
        "</tr>"
    )


def _render_summary_row(
    street: str,
    count: int,
    distance: float,
    kinds: str,
) -> str:
    return (
        "          <tr>"
        f"<td>{escape(street)}</td>"
        f"<td class=\"mono\">{count}</td>"
        f"<td class=\"mono\">{distance:.2f}</td>"
        f"<td>{escape(kinds)}</td>"
        "</tr>"
    )

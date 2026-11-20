"""Draw the dbt lineage graph of dbt_project into images/dbt-dag.png.

Usage, from the root of the repository: uv run generate_lineage.py
"""

import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).parent
DBT_PROJECT = ROOT / "dbt_project"
OUTPUT = ROOT / "images" / "dbt-dag.png"

# Same colors as the dbt docs lineage graph
COLORS = {"source": "#5fb825", "seed": "#8eb0d6", "model": "#0094b3", "snapshot": "#88447d"}


def load_graph() -> tuple[dict[str, dict], list[tuple[str, str]]]:
    """Parse the project and return its nodes and edges from the manifest."""
    subprocess.run(["dbt", "parse", "--quiet"], cwd=DBT_PROJECT, check=True)
    manifest = json.loads((DBT_PROJECT / "target" / "manifest.json").read_text(encoding="utf-8"))
    nodes = {}
    for unique_id, node in {**manifest["nodes"], **manifest["sources"]}.items():
        if node["resource_type"] in COLORS:
            nodes[unique_id] = {"name": node["name"], "type": node["resource_type"]}
    edges = [
        (parent, child)
        for child, parents in manifest["parent_map"].items()
        if child in nodes
        for parent in parents
        if parent in nodes
    ]
    return nodes, edges


def assign_columns(nodes: dict[str, dict], edges: list[tuple[str, str]]) -> dict[str, int]:
    """Put each node one column to the right of its furthest parent."""
    column = {node: 0 for node in nodes}
    for _ in nodes:
        for parent, child in edges:
            column[child] = max(column[child], column[parent] + 1)
    # Move sources and seeds right next to the first model that uses them
    for node in nodes:
        children = [column[child] for parent, child in edges if parent == node]
        if children and not any(child == node for _, child in edges):
            column[node] = min(children) - 1
    return column


def draw(nodes: dict[str, dict], edges: list[tuple[str, str]], column: dict[str, int]) -> None:
    """Draw the boxes and arrows and save the PNG."""
    by_column: dict[int, list[str]] = {}
    for node in sorted(nodes, key=lambda n: nodes[n]["name"]):
        by_column.setdefault(column[node], []).append(node)
    width, height, x_gap, y_gap = 2.6, 0.6, 1.2, 0.5
    rows = max(len(members) for members in by_column.values())
    position = {}
    for col, members in by_column.items():
        offset = (rows - len(members)) * (height + y_gap) / 2
        for row, node in enumerate(members):
            position[node] = (col * (width + x_gap), -(offset + row * (height + y_gap)))

    columns = max(by_column) + 1
    fig, ax = plt.subplots(figsize=(columns * 3.2, rows * 1.0 + 0.6))
    for parent, child in edges:
        (x1, y1), (x2, y2) = position[parent], position[child]
        arrow = FancyArrowPatch(
            (x1 + width, y1 + height / 2),
            (x2, y2 + height / 2),
            arrowstyle="-|>",
            mutation_scale=12,
            color="#7a7a7a",
            connectionstyle="arc3,rad=0",
        )
        ax.add_patch(arrow)
    for node, (x, y) in position.items():
        box = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            color=COLORS[nodes[node]["type"]],
        )
        ax.add_patch(box)
        ax.text(
            x + width / 2,
            y + height / 2,
            nodes[node]["name"],
            ha="center",
            va="center",
            color="white",
            fontsize=9,
        )

    handles = [Rectangle((0, 0), 1, 1, color=color) for color in COLORS.values()]
    ax.legend(
        handles,
        COLORS.keys(),
        loc="upper center",
        bbox_to_anchor=(0.5, 0.0),
        ncol=len(COLORS),
        frameon=False,
    )
    ax.set_xlim(-0.2, columns * (width + x_gap) - x_gap + 0.2)
    ax.set_ylim(-(rows - 1) * (height + y_gap) - 0.2, height + 0.2)
    ax.axis("off")
    OUTPUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, bbox_inches="tight")
    print(f"Lineage graph written to {OUTPUT}")


def main() -> None:
    nodes, edges = load_graph()
    draw(nodes, edges, assign_columns(nodes, edges))


if __name__ == "__main__":
    main()

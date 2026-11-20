"""Draw the dbt lineage graph of dbt_project into images/dbt-dag.png.

It also writes images/dbt-dag.json, a text description of the nodes, edges and layout of the
graph. The PNG bytes depend on the matplotlib version and the OS, the JSON does not, so the tests
compare the JSON to check that the committed graph is up to date.

Usage: uv run dbt-hello-world lineage
"""

import contextlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

from dbt_hello_world import config  # noqa: E402
from dbt_hello_world.runner import invoke  # noqa: E402


def load_graph(
    project_dir: Path = config.DBT_PROJECT,
) -> tuple[dict[str, dict], list[tuple[str, str]]]:
    """Parse the project and return its nodes and edges from the manifest."""
    with contextlib.chdir(project_dir):
        invoke(["parse", "--quiet"])
    manifest = json.loads((project_dir / "target" / "manifest.json").read_text(encoding="utf-8"))
    nodes = {}
    for section in config.MANIFEST_SECTIONS:
        for unique_id, node in manifest[section].items():
            if node["resource_type"] in config.COLORS:
                nodes[unique_id] = {"name": node["name"], "type": node["resource_type"]}
    edges = sorted(
        (parent, child)
        for child, parents in manifest["parent_map"].items()
        if child in nodes
        for parent in parents
        if parent in nodes
    )
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


def assign_rows(
    nodes: dict[str, dict], edges: list[tuple[str, str]], column: dict[str, int]
) -> dict[str, int]:
    """Number the nodes of each column from the top, close to the average row of their parents.

    Nodes without parents count as row 0, ties are sorted by name. This keeps the arrows short
    and avoids most crossings.
    """
    row: dict[str, int] = {}
    for col in sorted(set(column.values())):

        def key(node: str) -> tuple[float, str]:
            parents = [row[parent] for parent, child in edges if child == node and parent in row]
            return (sum(parents) / len(parents) if parents else 0.0, nodes[node]["name"])

        members = sorted((n for n in nodes if column[n] == col), key=key)
        for index, node in enumerate(members):
            row[node] = index
    return row


def describe(nodes: dict[str, dict], edges: list[tuple[str, str]]) -> dict:
    """Return the nodes, edges and layout of the graph as plain data, saved as dbt-dag.json."""
    column = assign_columns(nodes, edges)
    row = assign_rows(nodes, edges, column)
    return {
        "nodes": [
            {**nodes[node], "column": column[node], "row": row[node]}
            for node in sorted(nodes, key=lambda n: (column[n], row[n]))
        ],
        "edges": [[nodes[parent]["name"], nodes[child]["name"]] for parent, child in edges],
    }


def draw(description: dict, output: Path = config.LINEAGE_PNG) -> None:
    """Draw the boxes and arrows of the description and save the PNG."""
    width, height, x_gap, y_gap = 2.6, 0.6, 1.2, 0.5
    nodes = description["nodes"]
    sizes: dict[int, int] = {}
    for node in nodes:
        sizes[node["column"]] = sizes.get(node["column"], 0) + 1
    rows = max(sizes.values())
    position = {}
    for node in nodes:
        offset = (rows - sizes[node["column"]]) * (height + y_gap) / 2
        position[node["name"]] = (
            node["column"] * (width + x_gap),
            -(offset + node["row"] * (height + y_gap)),
        )

    columns = max(sizes) + 1
    fig, ax = plt.subplots(figsize=(columns * 3.2, rows * 1.0 + 0.6))
    for parent, child in description["edges"]:
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
    for node in nodes:
        x, y = position[node["name"]]
        box = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            color=config.COLORS[node["type"]],
        )
        ax.add_patch(box)
        ax.text(
            x + width / 2,
            y + height / 2,
            node["name"],
            ha="center",
            va="center",
            color="white",
            fontsize=9,
        )

    used = [kind for kind in config.COLORS if any(node["type"] == kind for node in nodes)]
    handles = [Rectangle((0, 0), 1, 1, color=config.COLORS[kind]) for kind in used]
    ax.legend(
        handles,
        [kind.replace("_", " ") for kind in used],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.0),
        ncol=len(used),
        frameon=False,
    )
    ax.set_xlim(-0.2, columns * (width + x_gap) - x_gap + 0.2)
    ax.set_ylim(-(rows - 1) * (height + y_gap) - 0.2, height + 0.2)
    ax.axis("off")
    output.parent.mkdir(parents=True, exist_ok=True)
    # No date or version in the metadata, so the same graph gives the same file on one machine
    fig.savefig(output, dpi=150, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    print(f"Lineage graph written to {output}")


def to_json(description: dict) -> str:
    """Serialize the description in a stable, diff-friendly way."""
    return json.dumps(description, indent=2) + "\n"


def main(project_dir: Path = config.DBT_PROJECT, output: Path = config.LINEAGE_PNG) -> None:
    """Write the JSON description and the PNG, next to each other."""
    description = describe(*load_graph(project_dir))
    json_path = output.with_suffix(".json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(to_json(description), encoding="utf-8")
    print(f"Lineage description written to {json_path}")
    draw(description, output)

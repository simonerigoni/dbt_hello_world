"""Unit tests of the lineage graph layout and drawing."""

import json
from pathlib import Path

from dbt_hello_world import config, lineage


def test_assign_columns() -> None:
    """Each node goes one column after its furthest parent, sources right before their child."""
    nodes = {name: {"name": name, "type": "model"} for name in ["src", "seed", "a", "b", "c"]}
    edges = [("src", "a"), ("a", "b"), ("b", "c"), ("seed", "c"), ("a", "c")]
    column = lineage.assign_columns(nodes, edges)
    assert column == {"src": 0, "seed": 2, "a": 1, "b": 2, "c": 3}


def test_assign_rows() -> None:
    """Nodes sit close to their parents, so the child of the top parent goes on top."""
    nodes = {name: {"name": name, "type": "model"} for name in ["p1", "p2", "a", "z"]}
    edges = [("p1", "z"), ("p2", "a")]
    column = {"p1": 0, "p2": 0, "a": 1, "z": 1}
    assert lineage.assign_rows(nodes, edges, column) == {"p1": 0, "p2": 1, "z": 0, "a": 1}


def small_graph() -> dict:
    nodes = {
        "source.raw": {"name": "raw", "type": "source"},
        "model.m": {"name": "m", "type": "model"},
        "exposure.e": {"name": "e", "type": "exposure"},
    }
    edges = [("source.raw", "model.m"), ("model.m", "exposure.e")]
    return lineage.describe(nodes, edges)


def test_describe() -> None:
    assert small_graph() == {
        "nodes": [
            {"name": "raw", "type": "source", "column": 0, "row": 0},
            {"name": "m", "type": "model", "column": 1, "row": 0},
            {"name": "e", "type": "exposure", "column": 2, "row": 0},
        ],
        "edges": [["raw", "m"], ["m", "e"]],
    }
    assert json.loads(lineage.to_json(small_graph())) == small_graph()


def test_draw(tmp_path: Path) -> None:
    output = tmp_path / "images" / "graph.png"
    lineage.draw(small_graph(), output)
    assert output.read_bytes().startswith(b"\x89PNG")


def test_every_type_has_the_dbt_docs_color() -> None:
    assert config.COLORS["exposure"] == "#ff694b"
    assert set(config.COLORS) == {
        "source", "seed", "model", "snapshot", "semantic_model", "metric", "exposure",
    }  # fmt: skip

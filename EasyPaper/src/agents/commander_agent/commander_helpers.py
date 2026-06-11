"""
Helper utilities for CommanderAgent graph/context transformation.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..writer_agent.section_models import ArgumentStructure, Material, Point


CLAIM_NODE_TYPES = {"idea", "hypothesis", "question", "finding"}
BACKGROUND_NODE_TYPES = {"literature", "concept"}


def build_argument_structure(
    materials: List[Material],
    section_type: str,
    user_prompt: str,
) -> ArgumentStructure:
    """
    Build an argument structure from materials.
    """
    point_materials = []
    evidence_materials = []
    background_materials = []

    for material in materials:
        if material.material_type in CLAIM_NODE_TYPES:
            point_materials.append(material)
        elif material.material_type in BACKGROUND_NODE_TYPES:
            background_materials.append(material)
        else:
            evidence_materials.append(material)

    main_points = []
    if point_materials:
        for point_material in point_materials:
            point_index = point_materials.index(point_material)
            chunk_size = max(1, len(evidence_materials) // len(point_materials))
            start_idx = point_index * chunk_size
            end_idx = start_idx + chunk_size if point_index < len(point_materials) - 1 else len(evidence_materials)
            supporting = evidence_materials[start_idx:end_idx]

            point = Point(
                id=f"point-{point_material.id}",
                statement=point_material.content[:200] if point_material.content else point_material.title,
                point_type="main",
                supporting_materials=supporting,
                counter_materials=[],
                sub_points=[],
            )
            main_points.append(point)
    else:
        default_point = Point(
            id="point-default",
            statement=user_prompt or f"Present the {section_type} content",
            point_type="main",
            supporting_materials=evidence_materials,
            counter_materials=[],
            sub_points=[],
        )
        main_points.append(default_point)

    thesis = None
    if main_points:
        first_point = main_points[0].statement
        thesis = f"This section presents: {first_point[:150]}..."

    return ArgumentStructure(
        thesis=thesis,
        main_points=main_points,
        background_context=background_materials,
    )


def build_node_map(nodes: List[Dict]) -> Dict[str, Dict]:
    """
    Build a map of node_id -> node for quick lookup.
    """
    node_map = {}

    def add_node(node):
        node_map[node["id"]] = node
        for block in node.get("blocks", []):
            add_node(block)

    for node in nodes:
        add_node(node)

    return node_map


def node_to_context(node: Dict) -> Dict[str, Any]:
    """
    Convert a graph node to a dict for later Material conversion.
    """
    data = node.get("data", {})
    inputs = data.get("inputsValues", {})
    content = None
    node_type = node.get("type", "unknown")

    if node_type in ["idea", "hypothesis", "question"]:
        content = inputs.get("Description", {}).get("content", "")
    elif node_type == "method":
        desc = inputs.get("Description", {}).get("content", "")
        eq = inputs.get("Equation", {}).get("content", "")
        content = desc
        if eq:
            content += f"\n\nEquation: {eq}"
    elif node_type == "experiment":
        content = inputs.get("Description", {}).get("content", "")
        setup = inputs.get("Setup", {}).get("content", "")
        if setup:
            content += f"\n\nSetup: {setup}"
    elif node_type == "result":
        content = inputs.get("Summary", {}).get("content", "")
    elif node_type == "paper_section":
        prompt = inputs.get("user_prompt", {}).get("content", "")
        draft = inputs.get("draft_content", {}).get("content", "")
        content = draft if draft else prompt
    elif node_type == "finding":
        content = inputs.get("Finding", {}).get("content", "")
    elif node_type == "literature":
        content = inputs.get("Summary", {}).get("content", "")
    elif node_type == "concept":
        content = inputs.get("Definition", {}).get("content", "")
    elif node_type == "data":
        content = inputs.get("Description", {}).get("content", "")
    elif node_type == "metric":
        content = inputs.get("Definition", {}).get("content", "")
    elif node_type in {"figure", "table"}:
        content = inputs.get("Caption", {}).get("content", "")
    elif node_type == "note":
        content = inputs.get("Content", {}).get("content", "")
    else:
        for field in ["Description", "Content", "Summary", "Text"]:
            if field in inputs:
                content = inputs.get(field, {}).get("content", "")
                if content:
                    break

    return {
        "node_id": node["id"],
        "node_type": node_type,
        "title": data.get("title", ""),
        "content": content,
        "metadata": {
            "references": data.get("references", []),
        },
    }


def find_relevant_nodes(nodes: List[Dict], section_type: str) -> List[Dict]:
    """
    Find nodes relevant to a specific section type.
    """
    relevance_map = {
        "abstract": ["result", "finding", "method", "hypothesis"],
        "introduction": ["question", "hypothesis", "idea", "literature"],
        "related_work": ["literature", "concept"],
        "method": ["method", "experiment", "data"],
        "experiment": ["experiment", "data", "metric"],
        "result": ["result", "finding", "figure", "table"],
        "discussion": ["result", "finding", "hypothesis"],
        "conclusion": ["result", "finding", "hypothesis", "question"],
    }

    relevant_types = relevance_map.get(section_type, [])
    relevant_nodes = []

    def check_node(node):
        if node.get("type") in relevant_types:
            relevant_nodes.append(node)
        for block in node.get("blocks", []):
            check_node(block)

    for node in nodes:
        check_node(node)

    return relevant_nodes[:10]


def format_node_context(node: Dict[str, Any]) -> str:
    """
    Format a node dict for logging.
    """
    node_type = node.get("node_type", "unknown")
    title = node.get("title") or node.get("node_id", "unknown")
    content = node.get("content", "")
    parts = [f"[{node_type.upper()}] {title}"]
    if content:
        parts.append(f"  Content: {content[:500]}")
    return "\n".join(parts)

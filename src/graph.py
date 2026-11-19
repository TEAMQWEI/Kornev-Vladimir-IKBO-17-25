"""Iterative BFS dependency graph builder and reverse dependency finder."""

from collections import deque
from collections.abc import Callable

from src.fetcher import FetchError, NpmRegistryFetcher

NODE_DELIMITER = "@"
SPLIT_MAX = 1
NAME_INDEX = 0
VER_INDEX = 1


def build_graph_bfs(
    root: str,
    get_neighbors: Callable[[str], list[str]],
) -> dict[str, list[str]]:
    """Build a directed graph iteratively via BFS without recursion."""
    graph: dict[str, list[str]] = {}
    visited: set[str] = {root}
    queue: deque[str] = deque([root])
    while queue:
        current = queue.popleft()
        neighbors = list(get_neighbors(current))
        graph[current] = neighbors
        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return graph


def build_test_graph(
    root: str,
    repo_graph: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Build transitive dependency subgraph for a test repository."""
    if root not in repo_graph:
        raise FetchError(
            f"Package '{root}' not found in test repository."
        )
    return build_graph_bfs(root, lambda node: repo_graph.get(node, []))


def _split_npm_node(node: str) -> tuple[str, str]:
    """Split 'package@version' node identifier into name and version."""
    name, version = node.rsplit(NODE_DELIMITER, SPLIT_MAX)
    return (name, version)


def build_npm_graph(
    fetcher: NpmRegistryFetcher,
    package_name: str,
    version: str,
) -> dict[str, list[str]]:
    """Build transitive npm dependency graph via iterative BFS."""
    root = f"{package_name}{NODE_DELIMITER}{version}"

    def get_neighbors(node: str) -> list[str]:
        """Fetch and resolve direct dependencies for an npm node."""
        pkg_name, pkg_ver = _split_npm_node(node)
        direct = fetcher.get_direct_dependencies(pkg_name, pkg_ver)
        resolved_nodes: list[str] = []
        for dep_name, ver_range in sorted(direct.items()):
            dep_ver = fetcher.resolve_dependency_version(
                dep_name,
                ver_range,
            )
            resolved_nodes.append(
                f"{dep_name}{NODE_DELIMITER}{dep_ver}"
            )
        return resolved_nodes

    return build_graph_bfs(root, get_neighbors)


def invert_graph(
    graph: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Invert all directed edges of a graph to find dependents."""
    inverted: dict[str, list[str]] = {node: [] for node in graph}
    for source, targets in graph.items():
        for target in targets:
            inverted.setdefault(target, [])
            if source not in inverted[target]:
                inverted[target].append(source)
    return inverted


def find_reverse_dependencies(
    target: str,
    repo_graph: dict[str, list[str]],
) -> list[str]:
    """Find all packages depending on target using iterative BFS."""
    if target not in repo_graph:
        raise FetchError(
            f"Package '{target}' not found in repository."
        )
    inverted = invert_graph(repo_graph)
    traversed = build_graph_bfs(
        target,
        lambda node: inverted.get(node, []),
    )
    return [node for node in traversed if node != target]


def format_graph_text(graph: dict[str, list[str]]) -> str:
    """Format adjacency dictionary as human-readable text."""
    lines: list[str] = []
    for node, deps in graph.items():
        deps_str = ", ".join(deps) if deps else "(no dependencies)"
        lines.append(f"{node} -> {deps_str}")
    return "\n".join(lines)
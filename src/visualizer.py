"""Mermaid diagram generation and image display via standard library."""

import base64
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MERMAID_INK_BASE = "https://mermaid.ink/img/"
MERMAID_PNG_QUERY = "?type=png"
USER_AGENT = "dep-graph-visualizer/1.0"
DEFAULT_TIMEOUT = 20
WINDOW_TITLE = "Dependency Graph"


class VisualizationError(RuntimeError):
    """Raised when diagram rendering or screen display fails."""


def _collect_nodes(graph: dict[str, list[str]]) -> list[str]:
    """Collect unique nodes in deterministic traversal order."""
    ordered: list[str] = []
    seen: set[str] = set()
    for node, deps in graph.items():
        if node not in seen:
            seen.add(node)
            ordered.append(node)
        for dep in deps:
            if dep not in seen:
                seen.add(dep)
                ordered.append(dep)
    return ordered


def _escape_label(label: str) -> str:
    """Escape double quotes inside Mermaid node labels."""
    return label.replace('"', "'")


def graph_to_mermaid(graph: dict[str, list[str]]) -> str:
    """Convert an adjacency graph dictionary to Mermaid diagram text."""
    nodes = _collect_nodes(graph)
    node_ids = {node: f"n{idx}" for idx, node in enumerate(nodes)}
    lines = ["graph TD"]
    for node in nodes:
        safe_label = _escape_label(node)
        lines.append(f'    {node_ids[node]}["{safe_label}"]')
    for source, targets in graph.items():
        src_id = node_ids[source]
        for target in targets:
            dst_id = node_ids[target]
            lines.append(f"    {src_id} --> {dst_id}")
    return "\n".join(lines)


def build_mermaid_url(mermaid_text: str) -> str:
    """Encode Mermaid diagram syntax into a mermaid.ink PNG URL."""
    encoded = base64.urlsafe_b64encode(
        mermaid_text.encode("utf-8")
    ).decode("ascii")
    return f"{MERMAID_INK_BASE}{encoded}{MERMAID_PNG_QUERY}"


def fetch_mermaid_png(
    mermaid_text: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> bytes:
    """Download rendered PNG bytes for a Mermaid diagram."""
    url = build_mermaid_url(mermaid_text)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as err:
        raise VisualizationError(
            f"HTTP {err.code} rendering Mermaid diagram."
        ) from err
    except URLError as err:
        raise VisualizationError(
            f"Network error rendering Mermaid diagram: {err.reason}."
        ) from err


def display_png_window(
    png_bytes: bytes,
    title: str = WINDOW_TITLE,
) -> None:
    """Display PNG image bytes on screen in a tkinter window."""
    try:
        import tkinter as tk
    except ImportError as err:
        raise VisualizationError("tkinter is not installed.") from err
    try:
        root = tk.Tk()
        root.title(title)
        encoded = base64.b64encode(png_bytes).decode("ascii")
        photo = tk.PhotoImage(data=encoded)
        label = tk.Label(root, image=photo)
        label.image = photo
        label.pack()
        root.mainloop()
    except tk.TclError as err:
        raise VisualizationError(
            f"Failed to display graph window: {err}"
        ) from err
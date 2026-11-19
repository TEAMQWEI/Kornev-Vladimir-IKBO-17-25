"""Unit tests for Mermaid diagram generation."""

import unittest

from src.visualizer import build_mermaid_url, graph_to_mermaid


class TestVisualizer(unittest.TestCase):
    """Verify Mermaid text output and URL encoding."""

    def test_mermaid_edges_and_labels(self) -> None:
        """Generate valid Mermaid syntax for scoped npm names."""
        graph = {
            "@scope/app@1.0.0": ["debug@4.3.7"],
            "debug@4.3.7": ["ms@2.1.3"],
            "ms@2.1.3": [],
        }
        mermaid = graph_to_mermaid(graph)
        self.assertIn("graph TD", mermaid)
        self.assertIn('n0["@scope/app@1.0.0"]', mermaid)
        self.assertIn("n0 --> n1", mermaid)
        self.assertIn("n1 --> n2", mermaid)

    def test_mermaid_isolated_node(self) -> None:
        """Render standalone node when package has no dependencies."""
        mermaid = graph_to_mermaid({"A": []})
        self.assertEqual(mermaid, 'graph TD\n    n0["A"]')

    def test_mermaid_url_format(self) -> None:
        """Produce valid mermaid.ink PNG endpoint URL."""
        url = build_mermaid_url("graph TD\n    n0[\"A\"]")
        self.assertTrue(url.startswith("https://mermaid.ink/img/"))
        self.assertTrue(url.endswith("?type=png"))


if __name__ == "__main__":
    unittest.main()
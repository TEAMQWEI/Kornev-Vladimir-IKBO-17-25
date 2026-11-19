"""CLI entry point for the dependency graph visualizer."""

import argparse
import sys

from src.config import AppConfig, ConfigError, format_config, load_config
from src.fetcher import (
    FetchError,
    NpmRegistryFetcher,
    load_test_repository,
)
from src.graph import (
    build_npm_graph,
    build_test_graph,
    find_reverse_dependencies,
    format_graph_text,
)
from src.visualizer import (
    VisualizationError,
    build_mermaid_url,
    display_png_window,
    fetch_mermaid_png,
    graph_to_mermaid,
)

EXIT_OK = 0
EXIT_ERROR = 1
DEFAULT_CONFIG = "config.ini"
MODES = ("config", "direct", "graph", "reverse", "visualize")


def build_arg_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Package dependency graph visualizer (npm)."
    )
    parser.add_argument(
        "-c",
        "--config",
        default=DEFAULT_CONFIG,
        help="Path to the INI configuration file.",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=MODES,
        default=None,
        help="Execution stage mode.",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Skip GUI window display and print Mermaid text only.",
    )
    return parser


def _resolve_graph(config: AppConfig) -> dict[str, list[str]]:
    """Build transitive dependency graph according to config mode."""
    if config.test_mode:
        repo = load_test_repository(config.repository_url)
        return build_test_graph(config.package_name, repo)
    fetcher = NpmRegistryFetcher(config.repository_url)
    return build_npm_graph(
        fetcher,
        config.package_name,
        config.package_version,
    )


def _run_direct_mode(config: AppConfig) -> None:
    """Print direct dependencies for Stage 2."""
    if config.test_mode:
        repo = load_test_repository(config.repository_url)
        if config.package_name not in repo:
            raise FetchError(
                f"Package '{config.package_name}' not in test repository."
            )
        deps = repo[config.package_name]
        print("\n".join(deps) if deps else "No direct dependencies.")
        return
    fetcher = NpmRegistryFetcher(config.repository_url)
    deps_map = fetcher.get_direct_dependencies(
        config.package_name,
        config.package_version,
    )
    if not deps_map:
        print("No direct dependencies.")
        return
    for name, ver_range in sorted(deps_map.items()):
        print(f"{name}: {ver_range}")


def _run_reverse_mode(config: AppConfig) -> None:
    """Print reverse dependencies for Stage 4."""
    if not config.test_mode:
        raise ConfigError(
            "Reverse dependency mode requires test_mode=true."
        )
    repo = load_test_repository(config.repository_url)
    rev_deps = find_reverse_dependencies(config.package_name, repo)
    if not rev_deps:
        print("No reverse dependencies found.")
        return
    print("\n".join(rev_deps))


def _run_visualize_mode(config: AppConfig, no_display: bool) -> None:
    """Generate Mermaid output and show graph image for Stage 5."""
    graph = _resolve_graph(config)
    mermaid_code = graph_to_mermaid(graph)
    print(mermaid_code)
    if no_display:
        return
    url = build_mermaid_url(mermaid_code)
    try:
        png_bytes = fetch_mermaid_png(mermaid_code)
        display_png_window(
            png_bytes,
            title=f"Dependencies: {config.package_name}",
        )
    except VisualizationError as err:
        print(f"Display warning: {err}", file=sys.stderr)
        print(f"Mermaid image URL: {url}", file=sys.stderr)


def _dispatch(mode: str, config: AppConfig, no_display: bool) -> None:
    """Execute the requested operational mode."""
    if mode == "config":
        print(format_config(config))
    elif mode == "direct":
        _run_direct_mode(config)
    elif mode == "graph":
        print(format_graph_text(_resolve_graph(config)))
    elif mode == "reverse":
        _run_reverse_mode(config)
    else:
        _run_visualize_mode(config, no_display)


def main(argv: list[str] | None = None) -> int:
    """Run CLI application and return process exit code."""
    args = build_arg_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        selected_mode = args.mode
        if selected_mode is None:
            selected_mode = (
                "reverse" if config.reverse_mode else "visualize"
            )
        _dispatch(selected_mode, config, args.no_display)
        return EXIT_OK
    except (ConfigError, FetchError, VisualizationError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
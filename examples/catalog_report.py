"""Render a catalog from the canonical SciTeX user configuration."""

from scitex_affairs import catalog_frame, load_config
from scitex_affairs.render import render_frame


def main() -> None:
    """Print the resolved catalog as Markdown."""

    print(render_frame(catalog_frame(load_config()), "markdown"))


if __name__ == "__main__":
    main()

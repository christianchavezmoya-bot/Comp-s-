"""Worker entrypoint.

In v0.1 the API runs ML inline, so this is a no-op placeholder.
In Phase 4 we'll spin up Dramatiq actors here that consume the analysis queue
and call the compas-ml package.
"""
from __future__ import annotations

import logging

log = logging.getLogger("compas.worker")


def main() -> None:
    log.info("Compás worker v0.1 — no-op. Real workers land in Phase 4.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

"""CLI entrypoint alias for the reproducible data cleaning pipeline (Phase 1 / Mission A)."""

from src.pipeline import main, run_pipeline

__all__ = ["main", "run_pipeline"]

if __name__ == "__main__":
    main()

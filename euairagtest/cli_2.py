"""Phase 1 CLI: ingest the corpus and write provisions to Parquet + JSON.

    uv run euaiact-ingest                         # pull default HF dataset
    uv run euaiact-ingest --source data/eu-ai-act.parquet
    uv run euaiact-ingest --format json --out-dir data
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .loader import DEFAULT_HF_GLOB, IngestResult, load_provisions


def _write_json(result: IngestResult, path: Path) -> None:
    path.write_text(
        json.dumps([p.to_row() for p in result.provisions], ensure_ascii=False, indent=2)
    )


def _write_parquet(result: IngestResult, path: Path) -> None:
    import polars as pl

    # infer_schema_length=None: scan all rows so nullable int columns (article,
    # paragraph, chapter, recital, annex_point) aren't mis-inferred as Null from an
    # all-None head — the 24-row sample never exercised this; the full corpus does.
    pl.DataFrame(
        [p.to_row() for p in result.provisions], infer_schema_length=None
    ).write_parquet(path)


def run(source: str | None, out_dir: Path, fmt: str, expand: bool, lang: str | None) -> IngestResult:
    result = load_provisions(source, expand_points=expand, lang=lang)
    out_dir.mkdir(parents=True, exist_ok=True)
    if fmt in ("json", "both"):
        _write_json(result, out_dir / "provisions.json")
    if fmt in ("parquet", "both"):
        _write_parquet(result, out_dir / "provisions.parquet")
    return result


def _summarize(result: IngestResult, out_dir: Path, fmt: str) -> str:
    lines = [
        f"Ingested {len(result.provisions)} provisions -> {out_dir}/ ({fmt})",
        "  by chunk_type: "
        + ", ".join(f"{k}={v}" for k, v in sorted(result.counts.items())),
    ]
    if result.unmapped:
        lines.append(f"  unmapped rows: {len(result.unmapped)} (see --verbose)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="EU AI Act Phase-1 corpus ingestion")
    ap.add_argument("--source", default=None,
                    help=f"parquet/json path or hf:// glob (default: {DEFAULT_HF_GLOB})")
    ap.add_argument("--out-dir", type=Path, default=Path("data"))
    ap.add_argument("--format", choices=["parquet", "json", "both"], default="both")
    ap.add_argument("--no-expand", action="store_true",
                    help="do not split paragraphs/annex items into point/sub-point children")
    ap.add_argument("--lang", default="en",
                    help="keep only this language (default: en); pass 'all' to keep every language")
    ap.add_argument("--verbose", action="store_true", help="list unmapped rows")
    args = ap.parse_args(argv)

    lang = None if args.lang == "all" else args.lang
    try:
        result = run(args.source, args.out_dir, args.format, expand=not args.no_expand, lang=lang)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(_summarize(result, args.out_dir, args.format))
    if args.verbose and result.unmapped:
        for sp, reason in result.unmapped:
            print(f"  UNMAPPED {sp}: {reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Load pipeline configuration from config.yaml.

One source of truth for the AOI, job-name prefix, search window and baseline
rules — replacing the constants previously hardcoded across the workflow
scripts. Pass a different path (each script's `--config`) to target another AOI.

Usage (from any workflow script):
    from config import load_config
    cfg = load_config(args.config)        # args.config may be None -> default
    aoi = cfg.aoi_path
    prefix = cfg.job_name_prefix
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


@dataclass(frozen=True)
class BaselineConfig:
    max_temporal_baseline_days: int
    sbas_neighbors: int
    max_perp_baseline_m: float


@dataclass(frozen=True)
class RescueGateConfig:
    """Quality bar a CONCERN pair must clear to be eligible as a bridge."""
    max_atmos_r2: float
    min_coherence: float
    min_surviving_pct: float


@dataclass(frozen=True)
class Config:
    aoi_path: Path
    job_name_prefix: str
    search_start: datetime
    search_end: datetime
    baseline: BaselineConfig
    rescue_gate: RescueGateConfig
    exclude_from_rescue: tuple[str, ...]

    @property
    def aoi_slug(self) -> str:
        """Short site slug from the AOI filename ('ramban_aoi.geojson' -> 'ramban').
        Used to prefix per-AOI output filenames (rainfall CSVs etc.), so pointing
        config.yaml at another AOI cannot clobber a previous site's artifacts."""
        stem = self.aoi_path.stem
        return stem[:-4] if stem.endswith("_aoi") else stem

    @property
    def data_suffix(self) -> str:
        """'' for ramban (grandfathered — its products already live in the plain
        dirs) else '_<slug>'. Appended to the Phase 2-4 output dir names
        (data/velocity, data/hazard, data/alerts, data/mosaic*) so two AOIs
        coexist: the same Sentinel-1 frames can cover both sites, so stack
        labels alone do not separate them."""
        return "" if self.aoi_slug == "ramban" else f"_{self.aoi_slug}"


def _to_utc(value) -> datetime:
    """Normalize a YAML date/datetime to a tz-aware UTC datetime.

    PyYAML parses 'YYYY-MM-DD' to datetime.date and full timestamps to
    datetime.datetime; the ASF query expects tz-aware datetimes.
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    # String fallback (e.g. quoted dates).
    return datetime.fromisoformat(str(value)).replace(tzinfo=timezone.utc)


def load_config(path: str | Path | None = None) -> Config:
    """Read and validate config.yaml (default: project-root config.yaml)."""
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config not found: {cfg_path}")

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    for key in ("aoi_path", "job_name_prefix", "search_start", "search_end"):
        if key not in raw:
            raise ValueError(f"Config {cfg_path} is missing required key: {key!r}")

    aoi = Path(raw["aoi_path"])
    if not aoi.is_absolute():
        aoi = PROJECT_ROOT / aoi

    b = raw.get("baseline") or {}
    g = raw.get("rescue_gate") or {}
    return Config(
        aoi_path=aoi,
        job_name_prefix=str(raw["job_name_prefix"]),
        search_start=_to_utc(raw["search_start"]),
        search_end=_to_utc(raw["search_end"]),
        baseline=BaselineConfig(
            max_temporal_baseline_days=int(b.get("max_temporal_baseline_days", 24)),
            sbas_neighbors=int(b.get("sbas_neighbors", 1)),
            max_perp_baseline_m=float(b.get("max_perp_baseline_m", 150)),
        ),
        rescue_gate=RescueGateConfig(
            max_atmos_r2=float(g.get("max_atmos_r2", 0.45)),
            min_coherence=float(g.get("min_coherence", 0.6)),
            min_surviving_pct=float(g.get("min_surviving_pct", 15)),
        ),
        exclude_from_rescue=tuple(raw.get("exclude_from_rescue") or []),
    )

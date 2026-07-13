"""Load pipeline configuration from config.yaml.

One source of truth for the AOI, job-name prefix, search window and baseline
rules — replacing the constants previously hardcoded across the workflow
scripts. Three ways to target an AOI, in precedence order:

  1. an explicit path (the `--config` flag on scripts that expose it);
  2. the INSAR_CONFIG environment variable (works for EVERY script, including
     the many that call load_config() at import time — the per-command
     multi-AOI mechanism, e.g.
     `docker compose run --rm -e INSAR_CONFIG=config/ramban.yaml insar python ...`);
  3. the root config.yaml — normally a one-line `active_config:` pointer into
     the per-AOI registry under config/ (a full config there still works).

Usage (from any workflow script):
    from config import load_config
    cfg = load_config(args.config)        # args.config may be None -> default
    aoi = cfg.aoi_path
    prefix = cfg.job_name_prefix
"""

from __future__ import annotations

import os
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
class SoilConfig:
    """Infinite-slope soil shear-strength parameters (Phase 3, geomechanical_engine).

    Defaults = the Ramban GSI-calibrated values (RESULTS_AND_KPIS.md §20), which the
    Vaishno Devi literature pass (§37) also brackets. A NEW AOI must do its own soil
    literature/field pass and set these in its config — do not silently inherit them
    (see NEW_AOI_PLAYBOOK.md, manual step M2). CLI flags on geomechanical_engine.py
    still override.
    """
    cohesion_dry_kpa: float
    cohesion_wet_kpa: float
    phi_deg: float
    gamma_kn_m3: float
    depth_m: float


@dataclass(frozen=True)
class Config:
    aoi_path: Path
    site_name: str
    operational_m: float
    watch_m: float
    kappa: float
    job_name_prefix: str
    search_start: datetime
    search_end: datetime
    baseline: BaselineConfig
    rescue_gate: RescueGateConfig
    soil: SoilConfig
    exclude_from_rescue: tuple[str, ...]
    source_path: Path  # the YAML this config was loaded from (after pointer resolution)

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
    """Read and validate config.yaml (default: project-root config.yaml).

    The root config.yaml may be a one-line POINTER (`active_config: config/<aoi>.yaml`)
    into the per-AOI registry under config/ — switch the whole pipeline to another AOI
    by editing that single line. A full config at the root still works (legacy form).
    The INSAR_CONFIG env var overrides the default path (but not an explicit `path`),
    so any script can be pointed at another AOI without touching the pointer.
    """
    if path is None and os.environ.get("INSAR_CONFIG"):
        path = os.environ["INSAR_CONFIG"]
        if not Path(path).is_absolute():
            path = PROJECT_ROOT / path
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config not found: {cfg_path}")

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    if "active_config" in raw:
        target = Path(raw["active_config"])
        if not target.is_absolute():
            target = PROJECT_ROOT / target
        if not target.exists():
            raise FileNotFoundError(
                f"{cfg_path} points at active_config={raw['active_config']} which does "
                f"not exist ({target})")
        pointed = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
        if "active_config" in pointed:
            raise ValueError(f"active_config chains are not allowed: {target} is itself "
                             f"a pointer")
        return load_config(target)

    for key in ("aoi_path", "job_name_prefix", "search_start", "search_end"):
        if key not in raw:
            raise ValueError(f"Config {cfg_path} is missing required key: {key!r}")

    aoi = Path(raw["aoi_path"])
    if not aoi.is_absolute():
        aoi = PROJECT_ROOT / aoi

    b = raw.get("baseline") or {}
    g = raw.get("rescue_gate") or {}
    s = raw.get("soil") or {}
    slug_stem = aoi.stem[:-4] if aoi.stem.endswith("_aoi") else aoi.stem
    return Config(
        aoi_path=aoi,
        # Human-readable site label for dashboard titles; optional — falls back to
        # the slug. (Ramban's config should carry `site_name: Ramban NH-44` to keep
        # its historical dashboard titles when regenerated.)
        site_name=str(raw.get("site_name") or slug_stem.title()),
        # Site-tuned operating points (assumed saturation m) for the two warning
        # tiers, from the per-site selectivity sweep (`rainfall_selectivity_
        # backtest.py`; ramban §21b/§23, vaishnodevi §32). Defaults = the
        # ramban-calibrated values, so configs without these keys are unchanged.
        operational_m=float(raw.get("operational_m", 0.50)),
        watch_m=float(raw.get("watch_m", 0.70)),
        # TWI-distributed saturation slope (Science Upgrade Plan #2, §45): each pixel's
        # saturation is m_i = clip(m + kappa*(TWI_i - TWI_mean), 0, 1) instead of a uniform
        # m. kappa (units 1/TWI) is swept per site like operational_m; DEFAULT 0.0 exactly
        # reproduces the uniform-m behavior (a built-in regression gate), so a config without
        # this key is numerically unchanged.
        kappa=float(raw.get("kappa", 0.0)),
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
        soil=SoilConfig(
            cohesion_dry_kpa=float(s.get("cohesion_dry_kpa", 18.5)),
            cohesion_wet_kpa=float(s.get("cohesion_wet_kpa", 5.0)),
            phi_deg=float(s.get("phi_deg", 36.0)),
            gamma_kn_m3=float(s.get("gamma_kn_m3", 19.0)),
            depth_m=float(s.get("depth_m", 3.0)),
        ),
        exclude_from_rescue=tuple(raw.get("exclude_from_rescue") or []),
        source_path=cfg_path,
    )

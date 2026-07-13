"""fs_real.py — single source of truth for how a day's AOI-mean saturation m becomes
the per-pixel FS_real field, and for the inverse question (the critical saturation a
zone activates at).

Physics layers, each optional and each with an exact regression gate:

  kappa (§45)   TWI-distributed saturation: m_i = clip(m + kappa*(TWI_i - TWI_mean), 0, 1).
                kappa=0 (default) -> uniform m, identical to the historical behaviour.
                TWI is centred on its own mean, so kappa REDISTRIBUTES wetness without
                changing the AOI mean (the rainfall proxy) — except where the clip
                engages (extreme-TWI tails at high m; measured mean shift is small).

  suction (§46) van Genuchten / Vanapalli nonlinear cohesion: instead of cohesion (and
                therefore FS) varying LINEARLY between the c_dry/c_wet end-members, the
                suction-derived apparent cohesion follows the soil-water retention curve

                    psi(m)  = (1/alpha) * (m^(-1/(1-1/n)) - 1)^(1/n)      [kPa]
                    c(m)    = c_wet + min(c_dry - c_wet, psi(m)*m*tan(phi'))

                (Vanapalli 1996 suction strength psi*S_e*tan(phi'), with m read as the
                effective saturation S_e; the min() cap anchors c(0)=c_dry exactly — the
                field-measured dry strength bounds what suction can contribute — and
                psi(1)=0 anchors c(1)=c_wet exactly, so BOTH engine end-member rasters
                are reproduced bit-for-bit at m=0 and m=1). Because only the cohesion
                term is nonlinear, FS needs no engine re-run:

                    FS(m) = (1-m)*FS_dry + m*FS_sat + [c(m) - c_lin(m)] * K
                    K     = dFS/dc = 1 / (gamma * z * sin(beta) * cos(beta))

                with K computed from the existing slope_deg raster (K=0 on <2 deg ground,
                matching the engine's flat-ground FS=5 override). suction=None (default)
                = the historical linear model.

Every consumer of "FS at wetness m" must go through this module so the layers can
never diverge between the standing product, the season timeline, the per-zone gate
and the triage ranking (that divergence bug is exactly how §45's first cut shipped:
hazard_timeline and watch_triage silently ignored kappa — error log 2026-07-13).
"""

from __future__ import annotations

import numpy as np


def m_field(m: float, twi: np.ndarray | None, kappa: float) -> np.ndarray | float:
    """Per-pixel saturation for AOI-mean wetness m. Scalar m when kappa=0 / no TWI."""
    if not kappa or twi is None:
        return m
    twi_mean = float(np.nanmean(twi))
    mf = np.clip(m + kappa * (twi - twi_mean), 0.0, 1.0)
    return np.where(np.isfinite(twi), mf, m)   # scalar m where TWI is undefined


def _psi_kpa(m, alpha_kpa_inv: float, n: float):
    """Matric suction (kPa) from the inverted van Genuchten retention curve; m is the
    effective saturation, strictly inside (0, 1)."""
    mv = 1.0 - 1.0 / n
    return np.power(np.power(m, -1.0 / mv) - 1.0, 1.0 / n) / alpha_kpa_inv


def cohesion_kpa(m, soil, suction):
    """c(m) under the van Genuchten/Vanapalli curve. Anchors: c(0)=c_dry, c(1)=c_wet.
    Accepts scalar or array m; returns the same shape."""
    span = soil.cohesion_dry_kpa - soil.cohesion_wet_kpa
    m_arr = np.atleast_1d(np.asarray(m, dtype=float))
    c_app = np.full(m_arr.shape, span)                 # m<=0 -> full dry apparent cohesion
    inside = (m_arr > 0.0) & (m_arr < 1.0)
    with np.errstate(over="ignore"):
        psi = _psi_kpa(m_arr[inside], suction.alpha_kpa_inv, suction.n)
    c_app[inside] = np.minimum(span, psi * m_arr[inside]
                               * np.tan(np.radians(soil.phi_deg)))
    c_app[m_arr >= 1.0] = 0.0                          # suction gone at saturation
    out = soil.cohesion_wet_kpa + c_app
    return float(out[0]) if np.isscalar(m) else out.reshape(np.shape(m))


def cohesion_correction_kpa(m, soil, suction):
    """delta_c(m) = c_vG(m) - c_linear(m). Exactly 0 at m=0 and m=1 (end-member gate)."""
    m_arr = np.asarray(m, dtype=float)
    c_lin = (1.0 - m_arr) * soil.cohesion_dry_kpa + m_arr * soil.cohesion_wet_kpa
    return cohesion_kpa(m, soil, suction) - c_lin


def fs_cohesion_sensitivity(slope_deg, soil):
    """K = dFS/dc = 1/(gamma*z*sin(beta)*cos(beta)) from the slope raster (or scalar).
    0 on <2 deg ground (the engine forces FS=5 there) and where slope is undefined."""
    b = np.radians(np.asarray(slope_deg, dtype=float))
    with np.errstate(invalid="ignore", divide="ignore"):
        den = soil.gamma_kn_m3 * soil.depth_m * np.sin(b) * np.cos(b)
        k = np.where(np.isfinite(den) & (den > 1e-6)
                     & (np.asarray(slope_deg) >= 2.0), 1.0 / den, 0.0)
    return float(k) if np.isscalar(slope_deg) else k


def fs_field(fs_dry: np.ndarray, fs_sat: np.ndarray, m: float,
             twi: np.ndarray | None = None, kappa: float = 0.0,
             slope_deg: np.ndarray | None = None, soil=None,
             suction=None) -> np.ndarray:
    """FS_real raster at AOI-mean wetness m, through every enabled physics layer."""
    mf = m_field(m, twi, kappa)
    fs = (1.0 - mf) * fs_dry + mf * fs_sat
    if suction is not None:
        k = fs_cohesion_sensitivity(slope_deg, soil)
        fs = np.clip(fs + cohesion_correction_kpa(mf, soil, suction) * k, 0.0, 5.0)
    return fs


def critical_saturation(fs_dry: float, fs_sat: float) -> float | None:
    """m* solving FS_dry + m*(FS_sat - FS_dry) = 1, clipped to [0, 1]. None if degenerate
    (saturation must REDUCE FS for a valid m*)."""
    denom = fs_sat - fs_dry
    if not np.isfinite(fs_dry) or not np.isfinite(fs_sat) or denom >= 0:
        return None
    return float(np.clip((1.0 - fs_dry) / denom, 0.0, 1.0))


def mstar(fs_dry_px: float, fs_sat_px: float, soil=None, suction=None,
          slope_deg_px: float | None = None, grid: int = 1024) -> float | None:
    """Critical LOCAL saturation m* at which this pixel crosses FS=1.

    suction=None -> the historical closed form (FS linear in m). With suction, FS(m) is
    nonlinear, so m* is found by a grid scan + linear interpolation (robust to any curve
    shape; §46). Semantics mirror the closed form exactly: None when saturation does not
    reduce FS (degenerate), 0.0 when already unstable dry, 1.0 when it never fails."""
    if suction is None:
        return critical_saturation(fs_dry_px, fs_sat_px)
    if (not np.isfinite(fs_dry_px) or not np.isfinite(fs_sat_px)
            or (fs_sat_px - fs_dry_px) >= 0):
        return None
    k = fs_cohesion_sensitivity(slope_deg_px if slope_deg_px is not None else 0.0, soil)
    ms = np.linspace(0.0, 1.0, grid)
    fs = ((1.0 - ms) * fs_dry_px + ms * fs_sat_px
          + cohesion_correction_kpa(ms, soil, suction) * k)
    below = fs < 1.0
    if not below.any():
        return 1.0
    i = int(np.argmax(below))
    if i == 0:
        return 0.0
    f0, f1 = float(fs[i - 1]), float(fs[i])
    t = (1.0 - f0) / (f1 - f0) if f1 != f0 else 0.0
    return float(np.clip(ms[i - 1] + t * (ms[i] - ms[i - 1]), 0.0, 1.0))


def effective_mstar(mstar: float, twi_zone: float | None, twi_mean: float | None,
                    kappa: float) -> float:
    """The AOI-mean wetness m(t) at which a zone activates, under the kappa layer.

    The zone's LOCAL saturation is m(t) + kappa*(TWI_zone - TWI_mean); it crosses its
    critical m* when m(t) = m* - kappa*(TWI_zone - TWI_mean). kappa=0 -> m* exactly."""
    if not kappa or twi_zone is None or twi_mean is None or not np.isfinite(twi_zone):
        return mstar
    return float(np.clip(mstar - kappa * (twi_zone - twi_mean), 0.0, 1.0))

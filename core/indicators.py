"""Trade competitiveness indicators.

All functions are pure: aligned pandas Series in, Series or float out.
Series are expected to share an index (product code or partner code);
alignment is by index, missing entries count as zero where stated.
"""

import numpy as np
import pandas as pd


def market_share(x_ik: pd.Series, m_k: pd.Series) -> pd.Series:
    """MS_ik = X_ik / M_k, as a percentage.

    x_ik: supplier i's exports to market k, by product.
    m_k:  market k's total imports from the world, by product.
    Products absent from m_k or with zero imports yield NaN.
    """
    ms = x_ik / m_k.reindex(x_ik.index)
    return (ms * 100).replace([np.inf, -np.inf], np.nan)


def rca(x_ip: pd.Series, w_p: pd.Series) -> pd.Series:
    """Balassa revealed comparative advantage (VCR).

    RCA_ip = (X_ip / sum_p X_ip) / (W_p / sum_p W_p)

    x_ip: country i's exports by product.
    w_p:  reference-group (world) exports by product.
    Both totals are taken over the union of products; missing entries
    count as zero. Products with zero reference exports yield NaN.
    """
    idx = x_ip.index.union(w_p.index)
    x = x_ip.reindex(idx, fill_value=0.0)
    w = w_p.reindex(idx, fill_value=0.0)
    x_share = x / x.sum()
    w_share = w / w.sum()
    out = (x_share / w_share).replace([np.inf, -np.inf], np.nan)
    return out.reindex(x_ip.index)


def grubel_lloyd(x: pd.Series, m: pd.Series) -> pd.Series:
    """Per-product Grubel-Lloyd index (ICII), 0-100.

    GL_p = (1 - |X_p - M_p| / (X_p + M_p)) * 100
    Missing entries count as zero; products with no trade yield NaN.
    """
    idx = x.index.union(m.index)
    xv = x.reindex(idx, fill_value=0.0)
    mv = m.reindex(idx, fill_value=0.0)
    total = xv + mv
    gl = (1 - (xv - mv).abs() / total) * 100
    return gl.where(total > 0)


def grubel_lloyd_aggregate(x: pd.Series, m: pd.Series) -> float:
    """Trade-weighted aggregate Grubel-Lloyd index, 0-100."""
    idx = x.index.union(m.index)
    xv = x.reindex(idx, fill_value=0.0)
    mv = m.reindex(idx, fill_value=0.0)
    total = (xv + mv).sum()
    if total == 0:
        return float("nan")
    return float((total - (xv - mv).abs().sum()) / total * 100)


def hhi(values: pd.Series) -> float:
    """Herfindahl-Hirschman concentration index, 0-1."""
    total = values.sum()
    if total == 0:
        return float("nan")
    shares = values / total
    return float((shares**2).sum())


def cagr(series: pd.Series) -> float:
    """Compound annual growth rate (%) over a year-indexed value series.

    Uses the first and last non-zero observations; NaN when fewer than
    two usable points or a non-positive starting value.
    """
    s = series.dropna().sort_index()
    s = s[s > 0]
    if len(s) < 2:
        return float("nan")
    years = s.index[-1] - s.index[0]
    if years <= 0:
        return float("nan")
    return float(((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100)

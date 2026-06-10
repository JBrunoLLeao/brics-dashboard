import math

import pandas as pd
import pytest

from core.indicators import (
    cagr,
    grubel_lloyd,
    grubel_lloyd_aggregate,
    hhi,
    market_share,
    rca,
)


def test_market_share_basic():
    x = pd.Series({"01": 20.0, "02": 50.0})
    m = pd.Series({"01": 100.0, "02": 200.0, "03": 50.0})
    ms = market_share(x, m)
    assert ms["01"] == pytest.approx(20.0)
    assert ms["02"] == pytest.approx(25.0)


def test_market_share_zero_market_is_nan():
    ms = market_share(pd.Series({"01": 5.0}), pd.Series({"01": 0.0}))
    assert math.isnan(ms["01"])


def test_rca_hand_computed():
    # Country: 80% product A, 20% product B. World: 40% A, 60% B.
    x = pd.Series({"A": 80.0, "B": 20.0})
    w = pd.Series({"A": 400.0, "B": 600.0})
    out = rca(x, w)
    assert out["A"] == pytest.approx(2.0)
    assert out["B"] == pytest.approx(1 / 3)


def test_rca_missing_product_counts_as_zero():
    x = pd.Series({"A": 10.0})
    w = pd.Series({"A": 50.0, "B": 50.0})
    # x_share(A)=1, w_share(A)=0.5
    assert rca(x, w)["A"] == pytest.approx(2.0)


def test_grubel_lloyd_per_product():
    x = pd.Series({"A": 100.0, "B": 100.0, "C": 0.0})
    m = pd.Series({"A": 100.0, "B": 0.0, "C": 0.0})
    gl = grubel_lloyd(x, m)
    assert gl["A"] == pytest.approx(100.0)  # perfectly balanced
    assert gl["B"] == pytest.approx(0.0)  # one-way trade
    assert math.isnan(gl["C"])  # no trade


def test_grubel_lloyd_aggregate_weighted():
    # |200-100|=100, total=300 -> (300-100)/300*100
    x = pd.Series({"A": 200.0})
    m = pd.Series({"A": 100.0})
    assert grubel_lloyd_aggregate(x, m) == pytest.approx(200 / 300 * 100)


def test_hhi_monopoly_and_uniform():
    assert hhi(pd.Series([10.0, 0.0, 0.0])) == pytest.approx(1.0)
    assert hhi(pd.Series([1.0, 1.0, 1.0, 1.0])) == pytest.approx(0.25)


def test_cagr_doubling_in_two_years():
    s = pd.Series({2020: 100.0, 2021: 150.0, 2022: 400.0})
    assert cagr(s) == pytest.approx(100.0)


def test_cagr_insufficient_data():
    assert math.isnan(cagr(pd.Series({2020: 100.0})))

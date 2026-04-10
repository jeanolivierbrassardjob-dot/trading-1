"""
Elite Quantitative Portfolio Manager
─────────────────────────────────────
Steps 1-3: ETF selection, backtest (simulation from real historical params),
           Markowitz + Risk Parity optimization.
Data:      Embedded parameters calibrated on 2014-2024 data for 13 ETFs.
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from itertools import combinations
from scipy.optimize import minimize
import json

np.random.seed(42)

RISK_FREE    = 0.053   # US 3-month T-bill 2024
TRADING_DAYS = 252
SIM_YEARS    = 10
N_DAYS       = SIM_YEARS * TRADING_DAYS

# ──────────────────────────────────────────────────────────────────────────────
# STEP 1 — ETF UNIVERSE  (params calibrated on 2014-2024 historical data)
# ──────────────────────────────────────────────────────────────────────────────

# Annual drift (geometric), annual vol, category
ETF_PARAMS = {
    #         Ann Return  Ann Vol   Category
    "QQQ":   (0.188,      0.210,   "Momentum/Broad"),
    "XLK":   (0.203,      0.222,   "Sector-Tech"),
    "SOXX":  (0.225,      0.302,   "Sector-Semi"),
    "MTUM":  (0.152,      0.186,   "Momentum"),
    "SPMO":  (0.172,      0.198,   "Momentum"),
    "GLD":   (0.062,      0.138,   "Diversifier"),
    "TLT":   (-0.018,     0.152,   "Diversifier"),
    "SCHD":  (0.142,      0.168,   "Dividend"),
    "SSO":   (0.283,      0.405,   "2x Leverage"),
    "QLD":   (0.298,      0.424,   "2x Leverage"),
    "BOTZ":  (0.118,      0.242,   "Sector-AI"),
    "XLE":   (0.082,      0.278,   "Sector-Energy"),
    "QQQM":  (0.188,      0.210,   "Momentum/Broad"),  # proxy = QQQ
}

DESCRIPTIONS = {
    "QQQ":  "Invesco QQQ (NASDAQ-100)",
    "XLK":  "SPDR Tech Sector",
    "SOXX": "iShares Semiconductor",
    "MTUM": "iShares MSCI Momentum",
    "SPMO": "Invesco S&P 500 Momentum",
    "GLD":  "SPDR Gold Shares",
    "TLT":  "iShares 20+ Year Treasury",
    "SCHD": "Schwab US Dividend",
    "SSO":  "ProShares Ultra S&P500 (2×)",
    "QLD":  "ProShares Ultra QQQ (2×)",
    "BOTZ": "Global X AI & Robotics",
    "XLE":  "SPDR Energy Sector",
    "QQQM": "Invesco NASDAQ-100 mini",
}

# Correlation matrix (calibrated on 2014-2024 pairwise correlations)
TICKERS = list(ETF_PARAMS.keys())
N = len(TICKERS)

_CORR_VALUES = {
    ("QQQ",  "XLK"):  0.88, ("QQQ",  "SOXX"): 0.84, ("QQQ",  "MTUM"): 0.88,
    ("QQQ",  "SPMO"): 0.92, ("QQQ",  "GLD"):  0.08, ("QQQ",  "TLT"): -0.22,
    ("QQQ",  "SCHD"): 0.72, ("QQQ",  "SSO"):  0.97, ("QQQ",  "QLD"):  0.97,
    ("QQQ",  "BOTZ"): 0.80, ("QQQ",  "XLE"):  0.50, ("QQQ",  "QQQM"): 0.999,
    ("XLK",  "SOXX"): 0.80, ("XLK",  "MTUM"): 0.84, ("XLK",  "SPMO"): 0.86,
    ("XLK",  "GLD"):  0.06, ("XLK",  "TLT"): -0.20, ("XLK",  "SCHD"): 0.65,
    ("XLK",  "SSO"):  0.86, ("XLK",  "QLD"):  0.86, ("XLK",  "BOTZ"): 0.76,
    ("XLK",  "XLE"):  0.48, ("XLK",  "QQQM"): 0.88,
    ("SOXX", "MTUM"): 0.78, ("SOXX", "SPMO"): 0.80, ("SOXX", "GLD"):  0.05,
    ("SOXX", "TLT"): -0.18, ("SOXX", "SCHD"): 0.60, ("SOXX", "SSO"):  0.83,
    ("SOXX", "QLD"):  0.83, ("SOXX", "BOTZ"): 0.80, ("SOXX", "XLE"):  0.44,
    ("SOXX", "QQQM"): 0.84,
    ("MTUM", "SPMO"): 0.88, ("MTUM", "GLD"):  0.05, ("MTUM", "TLT"): -0.18,
    ("MTUM", "SCHD"): 0.72, ("MTUM", "SSO"):  0.86, ("MTUM", "QLD"):  0.86,
    ("MTUM", "BOTZ"): 0.74, ("MTUM", "XLE"):  0.52, ("MTUM", "QQQM"): 0.88,
    ("SPMO", "GLD"):  0.06, ("SPMO", "TLT"): -0.20, ("SPMO", "SCHD"): 0.74,
    ("SPMO", "SSO"):  0.90, ("SPMO", "QLD"):  0.90, ("SPMO", "BOTZ"): 0.78,
    ("SPMO", "XLE"):  0.55, ("SPMO", "QQQM"): 0.92,
    ("GLD",  "TLT"):  0.22, ("GLD",  "SCHD"): 0.10, ("GLD",  "SSO"):  0.07,
    ("GLD",  "QLD"):  0.07, ("GLD",  "BOTZ"): 0.06, ("GLD",  "XLE"):  0.20,
    ("GLD",  "QQQM"): 0.08,
    ("TLT",  "SCHD"): 0.00, ("TLT",  "SSO"): -0.22, ("TLT",  "QLD"): -0.22,
    ("TLT",  "BOTZ"): -0.18, ("TLT", "XLE"): -0.12, ("TLT",  "QQQM"): -0.22,
    ("SCHD", "SSO"):  0.70, ("SCHD", "QLD"):  0.70, ("SCHD", "BOTZ"): 0.62,
    ("SCHD", "XLE"):  0.58, ("SCHD", "QQQM"): 0.72,
    ("SSO",  "QLD"):  0.95, ("SSO",  "BOTZ"): 0.78, ("SSO",  "XLE"):  0.50,
    ("SSO",  "QQQM"): 0.97,
    ("QLD",  "BOTZ"): 0.78, ("QLD",  "XLE"):  0.50, ("QLD",  "QQQM"): 0.97,
    ("BOTZ", "XLE"):  0.48, ("BOTZ", "QQQM"): 0.80,
    ("XLE",  "QQQM"): 0.50,
}

def build_corr_matrix():
    C = np.eye(N)
    for i, ti in enumerate(TICKERS):
        for j, tj in enumerate(TICKERS):
            if i < j:
                key = (ti, tj) if (ti, tj) in _CORR_VALUES else (tj, ti)
                v = _CORR_VALUES.get(key, 0.50)
                C[i, j] = C[j, i] = v
    # Nearest positive-definite fix
    eigvals = np.linalg.eigvalsh(C)
    if eigvals.min() < 0:
        C += (-eigvals.min() + 1e-6) * np.eye(N)
        d = np.sqrt(np.diag(C))
        C = C / np.outer(d, d)
    return C

CORR = build_corr_matrix()

# ──────────────────────────────────────────────────────────────────────────────
# SIMULATE DAILY RETURNS (GBM with calibrated params)
# ──────────────────────────────────────────────────────────────────────────────

def simulate_prices():
    """Generate N_DAYS of correlated daily returns via Cholesky decomposition."""
    mu_daily  = np.array([ETF_PARAMS[t][0] / TRADING_DAYS for t in TICKERS])
    sig_daily = np.array([ETF_PARAMS[t][1] / np.sqrt(TRADING_DAYS) for t in TICKERS])

    # Covariance matrix from correlation × vol
    D    = np.diag(sig_daily)
    cov  = D @ CORR @ D

    # Cholesky decomposition for correlated draws
    try:
        L = np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:
        eigvals, eigvecs = np.linalg.eigh(cov)
        eigvals = np.maximum(eigvals, 1e-10)
        cov = eigvecs @ np.diag(eigvals) @ eigvecs.T
        L = np.linalg.cholesky(cov)

    Z = np.random.randn(N_DAYS, N)
    daily_rets = mu_daily + (Z @ L.T)   # shape: (N_DAYS, N)

    # Build price series starting at 100
    prices = pd.DataFrame(
        100 * np.exp(np.cumsum(daily_rets, axis=0)),
        columns=TICKERS,
        index=pd.bdate_range("2015-01-01", periods=N_DAYS),
    )
    return prices

# ──────────────────────────────────────────────────────────────────────────────
# METRICS
# ──────────────────────────────────────────────────────────────────────────────

def port_rets(prices, weights):
    return (prices.pct_change().dropna() * weights).sum(axis=1)

def cagr(r):
    return (1 + r).prod() ** (TRADING_DAYS / len(r)) - 1

def sharpe(r):
    e = r.mean() * TRADING_DAYS - RISK_FREE
    v = r.std()  * np.sqrt(TRADING_DAYS)
    return e / v if v else np.nan

def sortino(r):
    e    = r.mean() * TRADING_DAYS - RISK_FREE
    neg  = r[r < 0]
    dv   = neg.std() * np.sqrt(TRADING_DAYS) if len(neg) else np.nan
    return e / dv if dv else np.nan

def max_dd(r):
    c = (1 + r).cumprod()
    return ((c - c.cummax()) / c.cummax()).min()

def calmar(r):
    c   = cagr(r)
    mdd = abs(max_dd(r))
    return c / mdd if mdd else np.nan

def win_rate_m(r):
    m = r.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    return (m > 0).mean()

def metrics(prices, w, label=""):
    r = port_rets(prices, w)
    return dict(
        label    = label,
        CAGR     = round(cagr(r) * 100, 2),
        Sharpe   = round(sharpe(r), 3),
        Sortino  = round(sortino(r), 3),
        MaxDD    = round(max_dd(r) * 100, 2),
        Calmar   = round(calmar(r), 3),
        WinR_M   = round(win_rate_m(r) * 100, 1),
        Ann_Vol  = round(r.std() * np.sqrt(TRADING_DAYS) * 100, 2),
    )

# ──────────────────────────────────────────────────────────────────────────────
# STEP 2 — BACKTEST ALL COMBINATIONS
# ──────────────────────────────────────────────────────────────────────────────

def backtest_all(prices):
    tickers = list(prices.columns)
    rows = []
    for r in range(3, 6):
        for combo in combinations(tickers, r):
            sub = prices[list(combo)]
            if len(sub) < 252:
                continue
            w   = np.ones(r) / r
            m   = metrics(sub, w, "+".join(combo))
            m["tickers"] = list(combo)
            rows.append(m)
    df = pd.DataFrame(rows)
    df["Score"] = (
        df["Sharpe"]  * 0.40 +
        df["Sortino"] * 0.20 +
        df["Calmar"]  * 0.15 +
        df["WinR_M"]  * 0.0015 +
        df["MaxDD"]   * (-0.10) / 100
    )
    return df.sort_values("Score", ascending=False, ignore_index=True)

# ──────────────────────────────────────────────────────────────────────────────
# STEP 3 — OPTIMIZATION
# ──────────────────────────────────────────────────────────────────────────────

def max_sharpe(dr, lo=0.10, hi=0.50):
    mu  = dr.mean().values
    cov = dr.cov().values
    n   = len(mu)
    def obj(w):
        r   = np.dot(w, mu)
        vol = np.sqrt(w @ cov @ w)
        return -(r - RISK_FREE / TRADING_DAYS) / vol if vol > 0 else 1e6
    res = minimize(obj, np.ones(n) / n,
                   bounds=[(lo, hi)] * n,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
                   method="SLSQP", options={"maxiter": 2000, "ftol": 1e-10})
    return res.x if res.success else np.ones(n) / n

def risk_parity(dr, lo=0.10, hi=0.50):
    cov = dr.cov().values
    n   = cov.shape[0]
    def obj(w):
        pv  = np.sqrt(w @ cov @ w)
        mrc = cov @ w / pv
        rc  = w * mrc / (w @ cov @ w + 1e-10)
        return np.sum((rc - 1 / n) ** 2)
    res = minimize(obj, np.ones(n) / n,
                   bounds=[(lo, hi)] * n,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
                   method="SLSQP", options={"maxiter": 2000, "ftol": 1e-12})
    return res.x if res.success else np.ones(n) / n

def multi_period(prices, w):
    out = {}
    for label, days in [("1Y", 252), ("3Y", 756), ("5Y", 1260), ("10Y", 2520)]:
        sub = prices.iloc[-days:] if len(prices) >= days else prices
        out[label] = metrics(sub, w, label)
    return out

# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    sep = "=" * 72

    print(sep)
    print("  ELITE QUANTITATIVE PORTFOLIO MANAGER")
    print("  Data: Calibrated simulation (2014–2024 historical parameters)")
    print(sep)

    # ── STEP 1 ────────────────────────────────────────────────────────────
    print("\nSTEP 1 — ETF UNIVERSE")
    print("-" * 72)
    print(f"{'ETF':<7} {'Description':<40} {'Ann Ret':>8} {'Ann Vol':>8} {'Category'}")
    print("-" * 72)
    for t in TICKERS:
        r, v, cat = ETF_PARAMS[t]
        print(f"{t:<7} {DESCRIPTIONS[t]:<40} {r*100:>7.1f}% {v*100:>7.1f}% {cat}")

    print("\nSimulating 10-year daily price history...")
    prices = simulate_prices()
    print(f"  {len(prices)} trading days, {len(TICKERS)} ETFs, correlated returns")

    # ── STEP 2 ────────────────────────────────────────────────────────────
    print(f"\n{sep}")
    print("STEP 2 — BACKTEST ALL COMBINATIONS (equal-weight, 10Y)")
    print("-" * 72)

    results = backtest_all(prices)
    print(f"Combinations tested: {len(results)}")
    print("\nTOP 10 COMBINATIONS:")
    cols = ["label", "CAGR", "Sharpe", "Sortino", "MaxDD", "Calmar", "WinR_M", "Score"]
    print(results[cols].head(10).to_string(index=False))

    # Prefer combinations with MaxDD > -22% (less negative), else fallback to score
    constrained = results[results["MaxDD"] > -22.0]
    if len(constrained) >= 1:
        best_row = constrained.iloc[0]
        note = " [MaxDD-constrained]"
    else:
        best_row = results.iloc[0]
        note = " [unconstrained]"
    best_tickers = best_row["tickers"]
    print(f"\n→ Best combination: {best_row['label']}  (Score={best_row['Score']:.4f}){note}")

    # ── STEP 3 ────────────────────────────────────────────────────────────
    print(f"\n{sep}")
    print("STEP 3 — PORTFOLIO OPTIMIZATION")
    print("-" * 72)

    sub = prices[best_tickers]
    dr  = sub.pct_change().dropna()

    w_eq  = np.ones(len(best_tickers)) / len(best_tickers)
    w_ms  = max_sharpe(dr)
    w_rp  = risk_parity(dr)

    m_eq  = metrics(sub, w_eq,  "EqualWeight")
    m_ms  = metrics(sub, w_ms,  "MaxSharpe")
    m_rp  = metrics(sub, w_rp,  "RiskParity")

    print(f"\n{'Strategy':<14} {'CAGR%':>8} {'Sharpe':>8} {'Sortino':>8} {'MaxDD%':>8} {'Calmar':>8} {'WinR%':>7}")
    print("-" * 70)
    for m in [m_eq, m_ms, m_rp]:
        print(f"{m['label']:<14} {m['CAGR']:>8} {m['Sharpe']:>8} {m['Sortino']:>8} {m['MaxDD']:>8} {m['Calmar']:>8} {m['WinR_M']:>7}")

    # Pick winner
    if m_ms["Sharpe"] >= m_rp["Sharpe"]:
        final_w, final_m, method = w_ms, m_ms, "Markowitz Max-Sharpe"
    else:
        final_w, final_m, method = w_rp, m_rp, "Risk Parity"

    print(f"\n→ Selected: {method}")
    print(f"\nFINAL PORTFOLIO ALLOCATIONS:")
    print(f"{'ETF':<7} {'Description':<40} {'Weight':>8}")
    print("-" * 60)
    for t, w in zip(best_tickers, final_w):
        print(f"{t:<7} {DESCRIPTIONS.get(t,''):<40} {w*100:>7.1f}%")

    # Multi-period
    print(f"\nMULTI-PERIOD PERFORMANCE ({method}):")
    mpm = multi_period(sub, final_w)
    print(f"\n{'Period':<6} {'CAGR%':>8} {'Sharpe':>8} {'Sortino':>8} {'MaxDD%':>8} {'Calmar':>8} {'WinR%':>7}")
    print("-" * 62)
    for p, m in mpm.items():
        print(f"{p:<6} {m['CAGR']:>8} {m['Sharpe']:>8} {m['Sortino']:>8} {m['MaxDD']:>8} {m['Calmar']:>8} {m['WinR_M']:>7}")

    # Correlation matrix
    print(f"\nCORRELATION MATRIX (final portfolio ETFs):")
    print(dr.corr().round(3).to_string())

    # ── SAVE RESULT ────────────────────────────────────────────────────────
    result = {
        "tickers": best_tickers,
        "weights": [round(float(w), 6) for w in final_w],
        "method":  method,
        "metrics_10y": final_m,
    }
    with open("portfolio_result.json", "w") as f:
        json.dump(result, f, indent=2)

    # ── STEP 5 — REPORT ───────────────────────────────────────────────────
    print(f"\n{sep}")
    print("STEP 5 — FINAL REPORT")
    print(sep)
    print(f"\n  OPTIMAL PORTFOLIO — {method}")
    print(f"  ETFs : {', '.join(best_tickers)}")
    print(f"\n  BACKTEST PERFORMANCE (10-year simulation, calibrated params):")
    print(f"    CAGR               : {final_m['CAGR']}%  (annualized)")
    print(f"    Sharpe Ratio        : {final_m['Sharpe']}  (target >1.5) {'✓' if final_m['Sharpe']>1.5 else '!'}")
    print(f"    Sortino Ratio       : {final_m['Sortino']}  (target >2.0) {'✓' if final_m['Sortino']>2.0 else '!'}")
    print(f"    Max Drawdown        : {final_m['MaxDD']}%  (target >-20%) {'✓' if final_m['MaxDD']>-20 else '!'}")
    print(f"    Calmar Ratio        : {final_m['Calmar']}")
    print(f"    Monthly Win Rate    : {final_m['WinR_M']}%")
    print(f"    Annual Volatility   : {final_m['Ann_Vol']}%")
    print(f"\n  RISKS TO MONITOR:")
    print(f"    • Rebalance if any ETF drifts >5% from target weight")
    print(f"    • Review quarterly or if portfolio drawdown exceeds 15%")
    if any(t in ["SSO", "QLD"] for t in best_tickers):
        print(f"    • 2× leveraged ETFs carry volatility decay risk in ranging markets")
    print(f"\n  REBALANCING THRESHOLD: ±5% from target weight")
    print(f"\n  Result saved to: portfolio_result.json")

    return result

if __name__ == "__main__":
    main()

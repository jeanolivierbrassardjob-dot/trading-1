"""
Alpaca Portfolio Deployment Script
────────────────────────────────────
Reads portfolio_result.json, checks account balance,
shows a dry-run preview, then asks for confirmation before
placing real market orders on Alpaca (paper or live).

Usage:
    python deploy.py              # dry-run (no orders)
    python deploy.py --live       # places real orders after confirmation
"""

import json
import time
import argparse
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Credentials ──────────────────────────────────────────────────────────────
ALPACA_KEY    = os.getenv("ALPACA_API_KEY",    "PK6SHYVFM7F6RKV3C7RE6US4QX")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY", "HPxuZsa8DKBpmBv2bN23xbczVhZKceEbsBzuwD1CcgwX")
TRADE_URL     = os.getenv("ALPACA_BASE_URL",   "https://paper-api.alpaca.markets/v2")
DATA_URL      = "https://data.alpaca.markets/v2"

HEADERS = {
    "APCA-API-KEY-ID":     ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET,
    "Accept":              "application/json",
    "Content-Type":        "application/json",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def api(method, path, base=TRADE_URL, **kwargs):
    url  = f"{base.rstrip('/')}/{path.lstrip('/')}"
    resp = requests.request(method, url, headers=HEADERS, timeout=20, **kwargs)
    resp.raise_for_status()
    return resp.json()

def get_account():
    return api("GET", "/account")

def get_positions():
    return api("GET", "/positions")

def get_orders(status="open"):
    return api("GET", f"/orders?status={status}")

def get_quote(symbol):
    """Get latest mid-price via Alpaca Data API."""
    try:
        q = api("GET", f"/stocks/{symbol}/quotes/latest", base=DATA_URL)
        quote = q.get("quote", {})
        ask   = float(quote.get("ap", 0))
        bid   = float(quote.get("bp", 0))
        if ask and bid:
            return (ask + bid) / 2
        return ask or bid
    except Exception:
        pass
    try:
        b = api("GET", f"/stocks/{symbol}/bars/latest", base=DATA_URL)
        return float(b.get("bar", {}).get("c", 0))
    except Exception:
        return 0.0

def submit_order(symbol, qty, side="buy", order_type="market"):
    payload = {
        "symbol":        symbol,
        "qty":           str(qty),
        "side":          side,
        "type":          order_type,
        "time_in_force": "day",
    }
    return api("POST", "/orders", json=payload)

def cancel_all_orders():
    return api("DELETE", "/orders")

# ── Main deployment logic ─────────────────────────────────────────────────────

def deploy(dry_run=True):
    sep = "=" * 68

    # Load portfolio
    try:
        with open("portfolio_result.json") as f:
            portfolio = json.load(f)
    except FileNotFoundError:
        print("ERROR: portfolio_result.json not found. Run portfolio_analysis.py first.")
        return

    tickers = portfolio["tickers"]
    weights = portfolio["weights"]
    method  = portfolio["method"]
    m       = portfolio.get("metrics_10y", portfolio.get("metrics", {}))

    print(sep)
    print("  ALPACA PORTFOLIO DEPLOYMENT" + (" — DRY RUN" if dry_run else " — LIVE"))
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(sep)

    # Account info
    print("\n[1/5] ACCOUNT STATUS")
    acct   = get_account()
    cash   = float(acct["cash"])
    equity = float(acct["equity"])
    bp     = float(acct.get("buying_power", cash))
    pdt    = acct.get("pattern_day_trader", False)
    status = acct.get("status", "unknown")

    print(f"  Account ID     : {acct['id'][:8]}…")
    print(f"  Status         : {status}")
    print(f"  Equity         : ${equity:>12,.2f}")
    print(f"  Cash           : ${cash:>12,.2f}")
    print(f"  Buying Power   : ${bp:>12,.2f}")
    print(f"  PDT flag       : {pdt}")
    print(f"  Currency       : {acct.get('currency', 'USD')}")

    # Existing positions
    positions = get_positions()
    if positions:
        print(f"\n  Existing positions ({len(positions)}):")
        for p in positions:
            mv = float(p.get("market_value", 0))
            print(f"    {p['symbol']:<7}  qty={p['qty']:>8}  MV=${mv:>10,.2f}")
    else:
        print("  No existing positions.")

    # Capital to deploy (use 98% of cash, never borrow)
    deploy_capital = min(cash * 0.98, equity)
    print(f"\n  Capital to deploy: ${deploy_capital:,.2f}  (98% of cash)")

    if deploy_capital < 100:
        print("  ERROR: Insufficient cash to deploy portfolio.")
        return

    # Get prices
    print("\n[2/5] FETCHING LIVE PRICES")
    prices = {}
    for t in tickers:
        price = get_quote(t)
        prices[t] = price
        print(f"  {t:<7}  ${price:>10,.2f}")

    # Calculate allocations
    print("\n[3/5] PORTFOLIO ALLOCATIONS")
    print(f"\n  {'ETF':<7} {'Weight':>7} {'Alloc $':>12} {'Price':>10} {'Shares':>8} {'Cost':>12}")
    print("  " + "-" * 62)

    orders_to_place = []
    total_cost = 0.0

    for t, w in zip(tickers, weights):
        alloc = deploy_capital * w
        price = prices[t]
        if price <= 0:
            print(f"  {t:<7} {w*100:>6.1f}%   — price unavailable, SKIPPED")
            continue
        shares = int(alloc / price)   # whole shares only (no fractional)
        cost   = shares * price
        total_cost += cost
        print(f"  {t:<7} {w*100:>6.1f}% ${alloc:>11,.2f} ${price:>9,.2f} {shares:>8} ${cost:>11,.2f}")
        if shares >= 1:
            orders_to_place.append({
                "symbol": t,
                "shares": shares,
                "price":  price,
                "weight": w,
                "cost":   cost,
            })

    remaining_cash = cash - total_cost
    print(f"\n  Total deployment cost : ${total_cost:>12,.2f}")
    print(f"  Remaining cash        : ${remaining_cash:>12,.2f}")

    # Optimization summary
    print(f"\n[4/5] PORTFOLIO SUMMARY")
    print(f"  Optimization method   : {method}")
    print(f"  ETFs                  : {', '.join(tickers)}")
    print(f"  CAGR (10Y backtest)   : {m.get('CAGR','N/A')}%")
    print(f"  Sharpe Ratio          : {m.get('Sharpe','N/A')}")
    print(f"  Sortino Ratio         : {m.get('Sortino','N/A')}")
    print(f"  Max Drawdown          : {m.get('MaxDD','N/A')}%")
    print(f"  Monthly Win Rate      : {m.get('WinR_M', m.get('WinRate_M','N/A'))}%")

    if dry_run:
        print(f"\n[5/5] DRY RUN COMPLETE — No orders placed.")
        print(f"  Run with --live to execute orders.")
        return

    # ── LIVE EXECUTION ────────────────────────────────────────────────────
    print(f"\n[5/5] PLACING ORDERS ({len(orders_to_place)} market orders)")
    print()
    confirm = input("  Type 'YES' to confirm and place all orders: ").strip()
    if confirm != "YES":
        print("  Aborted. No orders placed.")
        return

    # Cancel any stale open orders first
    try:
        cancel_all_orders()
        print("  Stale open orders cancelled.")
    except Exception:
        pass

    executed = []
    failed   = []

    for o in orders_to_place:
        try:
            resp   = submit_order(o["symbol"], o["shares"])
            oid    = resp.get("id", "")
            status = resp.get("status", "unknown")
            print(f"  ✓ {o['symbol']:<7} ×{o['shares']:>5} shares  →  {status}  (id: {oid[:12]}…)")
            executed.append({**o, "order_id": oid, "status": status})
        except requests.HTTPError as e:
            msg = e.response.text[:120] if e.response else str(e)
            print(f"  ✗ {o['symbol']:<7} FAILED: {msg}")
            failed.append({**o, "error": msg})
        time.sleep(0.4)   # ~2.5 req/s, within Alpaca limits

    # Summary
    print(f"\n  EXECUTION SUMMARY")
    print(f"  Successful orders : {len(executed)}/{len(orders_to_place)}")
    print(f"  Failed orders     : {len(failed)}")

    if failed:
        print("  Failed symbols    :", [f["symbol"] for f in failed])

    # Save execution log
    log = {
        "timestamp":  datetime.now().isoformat(),
        "portfolio":  portfolio,
        "executed":   executed,
        "failed":     failed,
        "cash_used":  total_cost,
        "cash_left":  remaining_cash,
    }
    logfile = f"deploy_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(logfile, "w") as f:
        json.dump(log, f, indent=2)
    print(f"  Log saved to      : {logfile}")

    print(f"\n  Portfolio deployed successfully. Monitor in Alpaca dashboard.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy ETF portfolio to Alpaca")
    parser.add_argument("--live", action="store_true",
                        help="Place real orders (default: dry-run)")
    args = parser.parse_args()

    deploy(dry_run=not args.live)

import yfinance as yf
from mcp.server.fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP("StockMarket")


def _fmt(val, prefix="", suffix="", decimals=2) -> str:
    """Safely format a value."""
    if val is None:
        return "N/A"
    try:
        if isinstance(val, (int, float)):
            return f"{prefix}{val:,.{decimals}f}{suffix}"
        return str(val)
    except Exception:
        return "N/A"


def _humanize(n) -> str:
    """Convert large numbers to human readable (B, M, K)."""
    if n is None:
        return "N/A"
    try:
        n = float(n)
        if abs(n) >= 1e12:
            return f"{n/1e12:.2f}T"
        if abs(n) >= 1e9:
            return f"{n/1e9:.2f}B"
        if abs(n) >= 1e6:
            return f"{n/1e6:.2f}M"
        if abs(n) >= 1e3:
            return f"{n/1e3:.2f}K"
        return f"{n:.2f}"
    except Exception:
        return "N/A"

@mcp.tool()
def search_stock_symbol(company_name: str = "") -> str:
    """
    Search for a stock ticker symbol by company name.
    ALWAYS call this first when you don't know the exact ticker.
    Works for Indian stocks (NSE/BSE) and global markets.
    Example: search_stock_symbol("Reliance Industries") → RELIANCE.NS
    Example: search_stock_symbol("Tata Consultancy")    → TCS.NS
    """
    if not company_name.strip():
        return (
            "Error: company_name is required. "
            "Example usage: search_stock_symbol('Reliance Industries')"
        )
    try:
        results = yf.Search(company_name)
        quotes = results.quotes
        if not quotes:
            return f"No ticker found for '{company_name}'. Try a different name."
        lines = [f"Top matches for '{company_name}':"]
        for q in quotes[:5]:
            lines.append(
                f"  {q.get('symbol','?'):<14} "
                f"{q.get('longname') or q.get('shortname', '?')}  "
                f"[{q.get('exchange','?')}]"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def get_stock_price(ticker: str) -> str:
    """
    Get the current stock price and key metrics for a ticker symbol.
    Example: get_stock_price("AAPL") or get_stock_price("RELIANCE.NS") for Indian stocks
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        if not info or (info.get("regularMarketPrice") is None and info.get("currentPrice") is None):
            return f"Error: Could not find data for ticker '{ticker}'. Check the symbol."

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev_close = info.get("previousClose", 0)
        change = price - prev_close if price and prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0
        arrow = "▲" if change >= 0 else "▼"
        currency = info.get("currency", "USD")

        return (
            f"📈 {info.get('longName', ticker.upper())} ({ticker.upper()})\n"
            f"💰 Price: {currency} {_fmt(price)} "
            f"{arrow} {_fmt(abs(change))} ({_fmt(abs(change_pct))}%)\n"
            f"📊 Open: {_fmt(info.get('open'))} | "
            f"Prev Close: {_fmt(prev_close)}\n"
            f"📉 Day Range: {_fmt(info.get('dayLow'))} – {_fmt(info.get('dayHigh'))}\n"
            f"📅 52w Range: {_fmt(info.get('fiftyTwoWeekLow'))} – {_fmt(info.get('fiftyTwoWeekHigh'))}\n"
            f"📦 Volume: {_humanize(info.get('volume'))} "
            f"(Avg: {_humanize(info.get('averageVolume'))})\n"
            f"🏦 Market Cap: {_humanize(info.get('marketCap'))}\n"
            f"🔁 Exchange: {info.get('exchange', 'N/A')}"
        )
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_stock_info(ticker: str) -> str:
    """
    Get detailed fundamental information about a stock including P/E, EPS, dividends, sector, etc.
    Example: get_stock_info("MSFT")
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        if not info:
            return f"Error: No data for '{ticker}'."

        return (
            f"🏢 {info.get('longName', ticker.upper())} ({ticker.upper()})\n"
            f"🏭 Sector: {info.get('sector', 'N/A')} | Industry: {info.get('industry', 'N/A')}\n"
            f"🌍 Country: {info.get('country', 'N/A')} | Exchange: {info.get('exchange', 'N/A')}\n\n"
            f"── Valuation ────────────────────\n"
            f"💰 Market Cap:  {_humanize(info.get('marketCap'))}\n"
            f"📊 P/E Ratio:   {_fmt(info.get('trailingPE'))}\n"
            f"📊 Fwd P/E:     {_fmt(info.get('forwardPE'))}\n"
            f"📊 P/B Ratio:   {_fmt(info.get('priceToBook'))}\n"
            f"📊 P/S Ratio:   {_fmt(info.get('priceToSalesTrailing12Months'))}\n"
            f"💵 EPS (TTM):   {_fmt(info.get('trailingEps'))}\n"
            f"💵 Fwd EPS:     {_fmt(info.get('forwardEps'))}\n\n"
            f"── Financials ───────────────────\n"
            f"💹 Revenue:     {_humanize(info.get('totalRevenue'))}\n"
            f"💹 Net Income:  {_humanize(info.get('netIncomeToCommon'))}\n"
            f"📈 Profit Margin: {_fmt((info.get('profitMargins') or 0) * 100)}%\n"
            f"📈 ROE:         {_fmt((info.get('returnOnEquity') or 0) * 100)}%\n"
            f"💳 Debt/Equity: {_fmt(info.get('debtToEquity'))}\n\n"
            f"── Dividends ────────────────────\n"
            f"💸 Dividend:    {_fmt(info.get('dividendRate'))} ({_fmt((info.get('dividendYield') or 0)*100)}% yield)\n"
            f"📅 Ex-Div Date: {info.get('exDividendDate', 'N/A')}\n\n"
            f"── Analysts ─────────────────────\n"
            f"🎯 Target Price: {_fmt(info.get('targetMeanPrice'))}\n"
            f"🔔 Recommendation: {info.get('recommendationKey', 'N/A').upper()}\n"
            f"👥 Analyst Count: {info.get('numberOfAnalystOpinions', 'N/A')}\n\n"
            f"📝 About: {(info.get('longBusinessSummary') or 'N/A')[:300]}..."
        )
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_stock_history(ticker: str, period: str = "1mo") -> str:
    """
    Get historical price data for a stock.
    period options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    Example: get_stock_history("TSLA", "3mo")
    """
    valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
    if period not in valid_periods:
        return f"Error: Invalid period. Choose from: {', '.join(valid_periods)}"

    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=period)

        if hist.empty:
            return f"Error: No historical data for '{ticker}'."

        start_price = hist["Close"].iloc[0]
        end_price = hist["Close"].iloc[-1]
        change = end_price - start_price
        change_pct = (change / start_price) * 100
        high = hist["High"].max()
        low = hist["Low"].min()
        avg_vol = hist["Volume"].mean()
        arrow = "▲" if change >= 0 else "▼"

        # Show last 10 data points
        recent = hist.tail(10)[["Open", "High", "Low", "Close", "Volume"]]
        rows = []
        for date, row in recent.iterrows():
            date_str = date.strftime("%Y-%m-%d")
            rows.append(
                f"  {date_str}  O:{row['Open']:.2f}  H:{row['High']:.2f}  "
                f"L:{row['Low']:.2f}  C:{row['Close']:.2f}  Vol:{_humanize(row['Volume'])}"
            )

        return (
            f"📈 {ticker.upper()} — {period} History\n"
            f"Period: {hist.index[0].strftime('%Y-%m-%d')} → {hist.index[-1].strftime('%Y-%m-%d')}\n"
            f"Start: {start_price:.2f} | End: {end_price:.2f}\n"
            f"Change: {arrow} {abs(change):.2f} ({abs(change_pct):.2f}%)\n"
            f"Period High: {high:.2f} | Period Low: {low:.2f}\n"
            f"Avg Volume: {_humanize(avg_vol)}\n\n"
            f"Recent Data (last 10 sessions):\n" + "\n".join(rows)
        )
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def compare_stocks(tickers: list[str]) -> str:
    """
    Compare multiple stocks side by side.
    tickers: list of ticker symbols, e.g. ["AAPL", "MSFT", "GOOGL"]
    Example: compare_stocks(["AAPL", "MSFT", "GOOGL"])
    """
    if not tickers:
        return "Error: Please provide at least one ticker."
    if len(tickers) > 6:
        return "Error: Max 6 tickers at once."

    results = []
    for t in tickers:
        try:
            stock = yf.Ticker(t.upper())
            info = stock.info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            prev = info.get("previousClose", 0)
            change_pct = ((price - prev) / prev * 100) if price and prev else 0
            arrow = "▲" if change_pct >= 0 else "▼"
            results.append(
                f"  {t.upper():<8} {_fmt(price):<10} {arrow}{abs(change_pct):.2f}%   "
                f"MCap: {_humanize(info.get('marketCap'))}   "
                f"P/E: {_fmt(info.get('trailingPE'))}"
            )
        except Exception as e:
            results.append(f"  {t.upper():<8} Error: {e}")

    header = f"  {'TICKER':<8} {'PRICE':<10} {'CHANGE%':<10} {'MARKET CAP':<16} {'P/E'}"
    divider = "  " + "-" * 60
    return "📊 Stock Comparison\n" + header + "\n" + divider + "\n" + "\n".join(results)


@mcp.tool()
def get_market_movers(market: str = "US") -> str:
    """
    Get top gainers and losers. market options: 'US' (default).
    Shows major indices performance.
    Example: get_market_movers()
    """
    indices = {
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "Dow Jones": "^DJI",
        "Russell 2000": "^RUT",
        "VIX": "^VIX",
    }

    lines = ["📊 Major Market Indices\n"]
    for name, sym in indices.items():
        try:
            t = yf.Ticker(sym)
            info = t.info
            price = info.get("regularMarketPrice") or info.get("currentPrice")
            prev = info.get("previousClose", 0)
            if price and prev:
                change = price - prev
                change_pct = change / prev * 100
                arrow = "▲" if change >= 0 else "▼"
                lines.append(f"  {name:<16} {price:>10,.2f}  {arrow} {abs(change_pct):.2f}%")
            else:
                lines.append(f"  {name:<16} N/A")
        except Exception:
            lines.append(f"  {name:<16} Error fetching data")

    return "\n".join(lines)


@mcp.tool()
def get_stock_dividends(ticker: str) -> str:
    """
    Get historical dividend payments for a stock.
    Example: get_stock_dividends("KO")
    """
    try:
        stock = yf.Ticker(ticker.upper())
        divs = stock.dividends

        if divs.empty:
            return f"{ticker.upper()} has no dividend history or doesn't pay dividends."

        recent = divs.tail(12)
        lines = [f"💸 {ticker.upper()} Dividend History (last 12 payments)\n"]
        for date, amount in recent.items():
            lines.append(f"  {date.strftime('%Y-%m-%d')}  ${amount:.4f}")

        annual = divs.resample("YE").sum().tail(5)
        lines.append("\n📅 Annual Dividends (last 5 years):")
        for date, amount in annual.items():
            lines.append(f"  {date.year}  ${amount:.4f}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
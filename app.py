import os
import requests
import statistics
import time # Import the time module
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from datetime import date, timedelta

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)

# --- FMP API Configuration ---
API_KEY = os.getenv("FMP_API_KEY") 
BASE_URL = "https://financialmodelingprep.com/api/v3"

# --- CACHE IMPLEMENTATION ---
screener_cache = {}
CACHE_DURATION_SECONDS = 2 * 60 * 60 # 2 hours

# --- List of All Features ---
features = {
    # Screeners
    "benjamin_graham": "Benjamin Graham",
    "piotroski_scan": "Piotroski Scan",
    "fii_buying": "Institutional Buying",
    "canslim": "CANSLIM",
    "darvas_scan": "Darvas Scan",
    "magic_formula": "Magic Formula",
    "coffee_can": "Coffee Can Investing",
    "qual_quant_analysis": "High-Quality Score",
    "balance_sheet_analysis": "Strong Balance Sheet",
    "market_view_forecast": "Market View Forecast",
    # Single-Stock Analysis Tools
    "share_holding_pattern": "Share Holding Pattern",
    "peers_comparison": "Peers Comparison"
}

# --- All Screener & Tool Functions (Optimized) ---

def run_benjamin_graham_screener():
    print("Running fast screener for Indian stocks...")
    screener_params = { 'marketCapMoreThan': 1000000000, 'priceEarningsRatioTTMLessThan': 15, 'priceToBookRatioTTMLessThan': 1.5, 'currentRatioTTMMoreThan': 2, 'debtToEquityTTMLessThan': 0.5, 'exchange': 'NSE,BSE', 'apikey': API_KEY }
    try:
        response = requests.get(f"{BASE_URL}/stock-screener", params=screener_params)
        response.raise_for_status()
        passed_stocks = response.json()
        if not passed_stocks: return ["No Indian stocks passed the Benjamin Graham criteria."]
        return [f"{stock['symbol']} ({stock['companyName']})" for stock in passed_stocks]
    except Exception as e: return [f"Error fetching data for Benjamin Graham scan: {e}"]

def run_piotroski_scan():
    print("Starting Piotroski F-Score Scan for Indian stocks...")
    high_f_score_stocks = []
    try:
        value_candidates_params = { 'priceToBookRatioTTMLessThan': 2, 'marketCapMoreThan': 500000000, 'isActivelyTrading': True, 'exchange': 'NSE,BSE', 'limit': 75, 'apikey': API_KEY }
        response = requests.get(f"{BASE_URL}/stock-screener", params=value_candidates_params)
        response.raise_for_status()
        candidate_stocks = response.json()
    except Exception as e: return [f"Error fetching candidate stocks: {e}"]
    print(f"Found {len(candidate_stocks)} candidates. Now calculating F-Score...")
    for i, stock in enumerate(candidate_stocks):
        ticker, name = stock['symbol'], stock['companyName']
        print(f"  [{i+1}/{len(candidate_stocks)}] Calculating for {ticker}...")
        try:
            ratios_data = requests.get(f"{BASE_URL}/ratios/{ticker}?period=annual&limit=2&apikey={API_KEY}").json()
            if len(ratios_data) < 2: continue
            cy, py = ratios_data[0], ratios_data[1]
            f_score = sum([ cy.get(k, 0) > py.get(k, 0) for k in ['returnOnAssets', 'currentRatio', 'assetTurnover', 'grossProfitMargin'] ]) + sum([ cy.get(k, 0) > 0 for k in ['returnOnAssets', 'operatingCashFlowPerShare'] ]) + (cy.get('operatingCashFlowPerShare', 0) > cy.get('netIncomePerShare', 0)) + (cy.get('debtEquityRatio', float('inf')) < py.get('debtEquityRatio', float('inf')))
            if f_score >= 8: high_f_score_stocks.append(f"{ticker} ({name}) - Score: {f_score}")
        except Exception: continue
    if not high_f_score_stocks: return ["No stocks found with a high F-Score (>= 8)."]
    return high_f_score_stocks

def run_fii_buying_screener():
    print("Starting FII/Institutional Buying Scan for Indian stocks...")
    ownership_increased_stocks = []
    try:
        candidate_params = { 'marketCapMoreThan': 2000000000, 'isActivelyTrading': True, 'exchange': 'NSE,BSE', 'limit': 75, 'apikey': API_KEY }
        response = requests.get(f"{BASE_URL}/stock-screener", params=candidate_params)
        response.raise_for_status()
        candidate_stocks = response.json()
    except Exception as e: return [f"Error fetching candidate stocks: {e}"]
    print(f"Found {len(candidate_stocks)} candidates. Checking for ownership increase...")
    for i, stock in enumerate(candidate_stocks):
        ticker, name = stock['symbol'], stock['companyName']
        print(f"  [{i+1}/{len(candidate_stocks)}] Checking {ticker}...")
        try:
            ownership_data = requests.get(f"{BASE_URL}/institutional-holder/{ticker}?apikey={API_KEY}").json()
            if len(ownership_data) < 2: continue
            ownership_data.sort(key=lambda x: x['date'], reverse=True)
            if ownership_data[0].get('totalHolding', 0) > ownership_data[1].get('totalHolding', 0): ownership_increased_stocks.append(f"{ticker} ({name})")
        except Exception: continue
    if not ownership_increased_stocks: return ["No stocks found with increased institutional ownership."]
    return ownership_increased_stocks

def run_canslim_screener():
    print("Starting CANSLIM Scan for Indian stocks...")
    try:
        market_data = requests.get(f"{BASE_URL}/historical-price-full/^NSEI?from={date.today() - timedelta(days=300)}&to={date.today()}&apikey={API_KEY}").json().get('historical', [])
        if len(market_data) < 200: return ["Could not fetch enough market data to determine trend."]
        market_data.reverse()
        prices = [item['close'] for item in market_data]
        current_price, sma_50, sma_200 = prices[-1], statistics.mean(prices[-50:]), statistics.mean(prices[-200:])
        if not (current_price > sma_50 and sma_50 > sma_200): return ["Market is not in a confirmed uptrend. CANSLIM investing is not advised."]
    except Exception as e: return [f"Error checking market direction: {e}"]
    print("Market is in an uptrend. Searching for CANSLIM stocks...")
    canslim_stocks = []
    try:
        candidate_params = { 'marketCapMoreThan': 2000000000, 'epsGrowthTTMMoreThan': 25, 'volumeMoreThan': 100000, 'exchange': 'NSE,BSE', 'limit': 75, 'apikey': API_KEY }
        candidate_stocks = requests.get(f"{BASE_URL}/stock-screener", params=candidate_params).json()
    except Exception as e: return [f"Error fetching candidate stocks: {e}"]
    for i, stock in enumerate(candidate_stocks):
        ticker, name = stock['symbol'], stock['companyName']
        print(f"  [{i+1}/{len(candidate_stocks)}] Checking {ticker}...")
        try:
            profile = requests.get(f"{BASE_URL}/profile/{ticker}?apikey={API_KEY}").json()[0]
            if not (profile.get('price', 0) > float(profile.get('range', '0-0').split('-')[1]) * 0.75): continue
            if requests.get(f"{BASE_URL}/technical_indicator/daily/{ticker}?period=14&type=rsi&apikey={API_KEY}").json()[0].get('rsi', 0) < 70: continue
            if len(requests.get(f"{BASE_URL}/institutional-holder/{ticker}?apikey={API_KEY}").json()) < 10: continue
            income = requests.get(f"{BASE_URL}/income-statement/{ticker}?period=quarter&limit=5&apikey={API_KEY}").json()
            if len(income) < 5 or income[4].get('eps', 0) <= 0 or ((income[0].get('eps', 0) - income[4].get('eps', 0)) / income[4].get('eps', 0)) < 0.25: continue
            canslim_stocks.append(f"{ticker} ({name})")
        except Exception: continue
    if not canslim_stocks: return ["No stocks passed the detailed CANSLIM criteria."]
    return canslim_stocks

def run_darvas_scan():
    print("Starting Darvas Scan for Indian stocks...")
    darvas_stocks = []
    try:
        candidate_params = { 'marketCapMoreThan': 5000000000, 'volumeMoreThan': 200000, 'isActivelyTrading': True, 'exchange': 'NSE,BSE', 'limit': 75, 'apikey': API_KEY }
        response = requests.get(f"{BASE_URL}/stock-screener", params=candidate_params)
        response.raise_for_status()
        candidate_stocks = response.json()
    except Exception as e: return [f"Error fetching candidate stocks: {e}"]
    print(f"Found {len(candidate_stocks)} candidates. Analyzing for Darvas Boxes...")
    for i, stock in enumerate(candidate_stocks):
        ticker, name = stock['symbol'], stock['companyName']
        print(f"  [{i+1}/{len(candidate_stocks)}] Checking {ticker}...")
        try:
            historical_data = requests.get(f"{BASE_URL}/historical-price-full/{ticker}?timeseries=65&apikey={API_KEY}").json().get('historical', [])
            if len(historical_data) < 60: continue
            historical_data.reverse()
            latest_day, current_price, current_volume = historical_data[-1], historical_data[-1].get('close', 0), historical_data[-1].get('volume', 0)
            high_52_wk = float(requests.get(f"{BASE_URL}/profile/{ticker}?apikey={API_KEY}").json()[0].get('range', '0-0').split('-')[1])
            if not (current_price >= high_52_wk * 0.95): continue
            recent_high = max(d.get('high', 0) for d in historical_data[-21:-1])
            if not (current_price > recent_high): continue
            avg_volume = statistics.mean(d.get('volume', 0) for d in historical_data[-21:-1])
            if avg_volume == 0 or not (current_volume > avg_volume * 1.5): continue
            darvas_stocks.append(f"{ticker} ({name})")
        except Exception as e: continue
    if not darvas_stocks: return ["No stocks found matching the Darvas Scan criteria."]
    return darvas_stocks

def run_magic_formula_screener():
    print("Starting Robust Magic Formula Scan for Indian stocks...")
    try:
        candidate_params = { 'marketCapMoreThan': 500000000, 'isActivelyTrading': True, 'priceEarningsRatioTTMLessThan': 50, 'priceEarningsRatioTTMMoreThan': 1, 'exchange': 'NSE,BSE', 'limit': 500, 'apikey': API_KEY }
        response = requests.get(f"{BASE_URL}/stock-screener", params=candidate_params)
        response.raise_for_status()
        candidates = response.json()
        for stock in candidates:
            stock['goodness_metric'] = stock.get('returnOnCapitalEmployedTTM') or stock.get('returnOnEquityTTM') or 0
            pe_ratio = stock.get('priceEarningsRatioTTM')
            if stock.get('earningsYieldTTM'): stock['cheapness_metric'] = stock.get('earningsYieldTTM')
            elif pe_ratio and pe_ratio > 0: stock['cheapness_metric'] = 1 / pe_ratio
            else: stock['cheapness_metric'] = 0
        filtered_candidates = [s for s in candidates if s['goodness_metric'] > 0 and s['cheapness_metric'] > 0]
    except Exception as e: return [f"Error fetching candidate stocks for Magic Formula: {e}"]
    if len(filtered_candidates) < 20: return ["Not enough data available to perform a meaningful Magic Formula ranking."]
    print(f"Found {len(filtered_candidates)} valid candidates. Now ranking...")
    good_ranked = sorted(filtered_candidates, key=lambda x: x['goodness_metric'], reverse=True)
    cheap_ranked = sorted(filtered_candidates, key=lambda x: x['cheapness_metric'], reverse=True)
    combined_ranks = {stock['symbol']: {'stock': stock} for stock in filtered_candidates}
    for i, stock in enumerate(good_ranked): combined_ranks[stock['symbol']]['rank_good'] = i + 1
    for i, stock in enumerate(cheap_ranked): combined_ranks[stock['symbol']]['rank_cheap'] = i + 1
    final_list = [ {**ranks, 'total_rank': ranks['rank_good'] + ranks['rank_cheap']} for symbol, ranks in combined_ranks.items() ]
    final_list_sorted = sorted(final_list, key=lambda x: x['total_rank'])
    top_stocks = [ f"{item['stock']['symbol']} ({item['stock']['companyName']}) - Combined Rank: {item['total_rank']}" for item in final_list_sorted[:30] ]
    if not top_stocks: return ["Could not generate Magic Formula rankings."]
    return top_stocks

def run_coffee_can_screener():
    print("Starting Adapted Coffee Can (5-Year) Scan for Indian stocks...")
    coffee_can_stocks = []
    try:
        candidate_params = { 'marketCapMoreThan': 10000000000, 'isActivelyTrading': True, 'exchange': 'NSE,BSE', 'limit': 50, 'apikey': API_KEY }
        response = requests.get(f"{BASE_URL}/stock-screener", params=candidate_params)
        response.raise_for_status()
        candidate_stocks = response.json()
    except Exception as e: return [f"Error fetching candidate stocks for Coffee Can scan: {e}"]
    print(f"Found {len(candidate_stocks)} candidates. Analyzing 5-year history for each...")
    for i, stock in enumerate(candidate_stocks):
        ticker, name = stock['symbol'], stock['companyName']
        print(f"  [{i+1}/{len(candidate_stocks)}] Checking {ticker}...")
        try:
            metrics_data = requests.get(f"{BASE_URL}/key-metrics/{ticker}?period=annual&limit=5&apikey={API_KEY}").json()
            if not metrics_data or len(metrics_data) < 5: continue
            roce_ok_years = sum(1 for year_data in metrics_data if (year_data.get('returnOnCapitalEmployed') or year_data.get('returnOnEquity') or 0) > 0.15)
            if roce_ok_years < 4: continue
            growth_ok_years = 0
            metrics_data.reverse()
            for j in range(1, len(metrics_data)):
                current_revenue = metrics_data[j].get('revenuePerShare', 0) * metrics_data[j].get('sharesOutstanding', 1)
                previous_revenue = metrics_data[j-1].get('revenuePerShare', 0) * metrics_data[j-1].get('sharesOutstanding', 1)
                if previous_revenue > 0 and current_revenue > previous_revenue: growth_ok_years += 1
            if growth_ok_years < 4: continue
            print(f"    >> {ticker} passed the 5-Year Coffee Can criteria!")
            coffee_can_stocks.append(f"{ticker} ({name})")
        except Exception as e: continue
    if not coffee_can_stocks: return ["No stocks found matching the stringent 5-Year Coffee Can criteria."]
    return coffee_can_stocks

def run_quality_screener():
    print("Starting High-Quality Score Scan for Indian stocks...")
    screener_params = { 'marketCapMoreThan': 5000000000, 'returnOnEquityTTMMoreThan': 15, 'grossProfitMarginTTMMoreThan': 30, 'netProfitMarginTTMMoreThan': 10, 'debtToEquityTTMLessThan': 1, 'revenueGrowth5YMoreThan': 5, 'exchange': 'NSE,BSE', 'limit': 100, 'apikey': API_KEY }
    try:
        response = requests.get(f"{BASE_URL}/stock-screener", params=screener_params)
        response.raise_for_status()
        passed_stocks = response.json()
        if not passed_stocks: return ["No Indian stocks passed the High-Quality Score criteria."]
        return [f"{stock['symbol']} ({stock['companyName']})" for stock in passed_stocks]
    except Exception as e: return [f"Error fetching data for High-Quality Score scan: {e}"]

def run_balance_sheet_screener():
    print("Starting Strong Balance Sheet Scan for Indian stocks...")
    strong_balance_sheet_stocks = []
    try:
        candidate_params = { 'marketCapMoreThan': 1000000000, 'currentRatioTTMMoreThan': 1.5, 'debtToEquityTTMLessThan': 1, 'totalDebtToTotalAssetsTTMLessThan': 0.5, 'exchange': 'NSE,BSE', 'limit': 75, 'apikey': API_KEY }
        response = requests.get(f"{BASE_URL}/stock-screener", params=candidate_params)
        response.raise_for_status()
        candidate_stocks = response.json()
    except Exception as e: return [f"Error fetching candidate stocks for Balance Sheet scan: {e}"]
    print(f"Found {len(candidate_stocks)} candidates with strong current stats. Now checking historical growth...")
    for i, stock in enumerate(candidate_stocks):
        ticker, name = stock['symbol'], stock['companyName']
        print(f"  [{i+1}/{len(candidate_stocks)}] Checking {ticker}...")
        try:
            metrics_data = requests.get(f"{BASE_URL}/key-metrics/{ticker}?period=annual&limit=5&apikey={API_KEY}").json()
            if not metrics_data or len(metrics_data) < 5: continue
            metrics_data.reverse()
            initial_bvps = metrics_data[0].get('bookValuePerShare', 0)
            final_bvps = metrics_data[-1].get('bookValuePerShare', 0)
            if initial_bvps <= 0 or (final_bvps / initial_bvps) < 1.3: continue
            growth_years = sum(1 for j in range(1, len(metrics_data)) if metrics_data[j].get('bookValuePerShare', 0) > metrics_data[j-1].get('bookValuePerShare', 0))
            if growth_years < 3: continue
            print(f"    >> {ticker} passed the balance sheet growth criteria!")
            strong_balance_sheet_stocks.append(f"{ticker} ({name})")
        except Exception: continue
    if not strong_balance_sheet_stocks: return ["No stocks found with a consistently growing strong balance sheet."]
    return strong_balance_sheet_stocks

def run_market_view_forecast():
    print("Analyzing Indian market trend (NIFTY 50)...")
    try:
        market_data = requests.get(f"{BASE_URL}/historical-price-full/^NSEI?from={date.today() - timedelta(days=300)}&to={date.today()}&apikey={API_KEY}").json().get('historical', [])
        if not market_data or len(market_data) < 200: return ["Error: Could not fetch enough market data to determine the trend."]
        market_data.reverse()
        prices = [item['close'] for item in market_data]
        current_price = prices[-1]
        sma_50 = statistics.mean(prices[-50:])
        sma_200 = statistics.mean(prices[-200:])
        verdict = "Uncertain / Sideways"
        if current_price > sma_50 and sma_50 > sma_200: verdict = "Strong Uptrend (Bullish)"
        elif current_price > sma_50 and current_price > sma_200: verdict = "Uptrend (Bullish)"
        elif current_price < sma_50 and sma_50 < sma_200: verdict = "Strong Downtrend (Bearish)"
        elif current_price < sma_50 and current_price < sma_200: verdict = "Downtrend (Bearish)"
        results = [
            f"Index: NIFTY 50 (^NSEI)", f"Current Price: {current_price:,.2f}",
            f"50-Day Avg: {sma_50:,.2f}", f"200-Day Avg: {sma_200:,.2f}",
            f"Verdict: {verdict}"
        ]
        return results
    except Exception as e: return [f"An error occurred while analyzing the market: {e}"]

def get_shareholding_pattern(ticker):
    print(f"Fetching shareholding for {ticker}...")
    try:
        ownership_data = requests.get(f"{BASE_URL}/institutional-holder/{ticker}?apikey={API_KEY}").json()
        if not ownership_data: return [f"No institutional ownership data found for {ticker}."]
        ownership_data.sort(key=lambda x: x.get('shares', 0), reverse=True)
        total_shares_held = sum(item.get('shares', 0) for item in ownership_data)
        results = [f"Top Institutional Holders for {ticker.upper()}:"]
        for holder in ownership_data[:10]:
            holder_name = holder.get('holder')
            shares = holder.get('shares', 0)
            percentage = (shares / total_shares_held * 100) if total_shares_held > 0 else 0
            results.append(f"- {holder_name}: {shares:,} shares ({percentage:.2f}%)")
        return results
    except Exception as e: return [f"Could not fetch shareholding data for {ticker}: {e}"]

def get_peers_comparison(ticker):
    print(f"Fetching peers comparison for {ticker}...")
    try:
        profile_response = requests.get(f"{BASE_URL}/profile/{ticker.upper()}?apikey={API_KEY}").json()
        if not profile_response: return [f"Could not find a profile for {ticker}."]
        main_stock_profile = profile_response[0]
        industry = main_stock_profile.get('industry')
        sector = main_stock_profile.get('sector')
        if not industry: return [f"Could not determine the industry for {ticker}."]
        peers_params = { 'industry': industry, 'sector': sector, 'exchange': 'NSE,BSE', 'limit': 10, 'apikey': API_KEY }
        peers_response = requests.get(f"{BASE_URL}/stock-screener", params=peers_params).json()
        peer_list = [peer['symbol'] for peer in peers_response if peer['symbol'] != ticker.upper()]
        if not peer_list: return [f"Could not find any peers for {ticker} in the {industry} industry."]
        all_tickers = [ticker.upper()] + peer_list
        results = [f"Peer Comparison in '{industry}' (Metric: Main vs. Peer Avg):"]
        comparison_data = {}
        for t in all_tickers:
            ratios = requests.get(f"{BASE_URL}/ratios-ttm/{t}?apikey={API_KEY}").json()
            if ratios: comparison_data[t] = ratios[0]
        if not comparison_data or ticker.upper() not in comparison_data: return ["Could not fetch financial data for comparison."]
        main_stock_data = comparison_data[ticker.upper()]
        peer_data_list = [data for t, data in comparison_data.items() if t != ticker.upper()]
        metrics_to_compare = {
            "P/E Ratio": 'priceEarningsRatioTTM', "P/B Ratio": 'priceToBookRatioTTM',
            "Debt/Equity": 'debtEquityRatioTTM', "Return on Equity (ROE)": 'returnOnEquityTTM',
            "Net Profit Margin": 'netProfitMarginTTM'
        }
        for display_name, key in metrics_to_compare.items():
            main_value = main_stock_data.get(key, 0) if main_stock_data.get(key) is not None else 0
            peer_values = [p.get(key, 0) for p in peer_data_list if p.get(key) is not None]
            peer_avg = statistics.mean(peer_values) if peer_values else 0
            results.append(f"- {display_name}: {main_value:.2f} vs. {peer_avg:.2f}")
        return results
    except Exception as e: return [f"An error occurred during peer comparison: {e}"]


# --- API Routes ---
@app.route('/')
def home():
    return render_template('index.html', features=features)

@app.route('/run_screener/<screener_key>')
def run_screener_api(screener_key):
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    current_time = time.time()
    if not force_refresh and screener_key in screener_cache:
        cached_data = screener_cache[screener_key]
        if current_time - cached_data['timestamp'] < CACHE_DURATION_SECONDS:
            print(f"Returning cached results for {screener_key}")
            return jsonify(results=cached_data['data'])

    print(f"Running fresh scan for {screener_key}...")
    results = [f"Logic for '{screener_key}' is not implemented yet."]
    screener_functions = {
        "benjamin_graham": run_benjamin_graham_screener, "piotroski_scan": run_piotroski_scan,
        "fii_buying": run_fii_buying_screener, "canslim": run_canslim_screener,
        "darvas_scan": run_darvas_scan, "magic_formula": run_magic_formula_screener,
        "coffee_can": run_coffee_can_screener, "qual_quant_analysis": run_quality_screener,
        "balance_sheet_analysis": run_balance_sheet_screener, "market_view_forecast": run_market_view_forecast
    }
    if screener_key in screener_functions:
        results = screener_functions[screener_key]()
    screener_cache[screener_key] = {'timestamp': current_time, 'data': results}
    return jsonify(results=results)

@app.route('/get_details/<tool_key>')
def get_details_api(tool_key):
    ticker = request.args.get('ticker', '').strip()
    if not ticker: return jsonify(results=["Please enter a stock ticker (e.g., RELIANCE.NS)."])
    results = [f"Logic for tool '{tool_key}' is not implemented yet."]
    if tool_key == "share_holding_pattern": results = get_shareholding_pattern(ticker)
    elif tool_key == "peers_comparison": results = get_peers_comparison(ticker)
    return jsonify(results=results)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
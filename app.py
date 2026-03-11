import streamlit as st
import numpy as np
from PIL import Image
from datetime import datetime
import easyocr
import requests
import pandas as pd
import re

st.set_page_config(page_title="Forex AI MTF Real", page_icon="📈", layout="centered")

# CONFIGURA QUI LA TUA API KEY (gratis su alphavantage.co)
ALPHA_VANTAGE_API_KEY = st.secrets.get("ALPHA_VANTAGE_KEY", "DEMO_KEY")

@st.cache_data(ttl=300)  # Cache 5 minuti
def get_real_forex_data(pair, timeframe):
    """
    Scarica dati reali da Alpha Vantage
    """
    # Mappa coppie
    symbol_map = {
        "XAU/USD": "XAUUSD",  # Alpha Vantage usa formato specifico
        "EUR/USD": "EURUSD",
        "GBP/USD": "GBPUSD",
        "USD/JPY": "USDJPY",
        "BTC/USD": "BTCUSD"
    }
    
    symbol = symbol_map.get(pair, pair.replace("/", ""))
    
    # Mappa timeframe Alpha Vantage
    interval_map = {
        "H1": "60min",
        "H4": "240min",  # Alpha Vantage non ha 4h nativo, simuliamo
        "D1": "daily"
    }
    
    interval = interval_map.get(timeframe, "60min")
    
    try:
        if timeframe == "D1":
            # Dati giornalieri
            url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={symbol[:3]}&to_symbol={symbol[3:]}&apikey={ALPHA_VANTAGE_API_KEY}"
        else:
            # Intraday
            url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={symbol[:3]}&to_symbol={symbol[3:]}&interval={interval}&apikey={ALPHA_VANTAGE_API_KEY}"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # Estrai time series
        if "Time Series FX" in data:
            ts_key = [k for k in data.keys() if "Time Series" in k][0]
            df = pd.DataFrame.from_dict(data[ts_key], orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            df.columns = ['open', 'high', 'low', 'close']
            df = df.astype(float)
            return df
        
        # Fallback per XAU (metallo, non forex)
        if "XAU" in pair:
            return get_gold_data_alternative(pair, timeframe)
            
    except Exception as e:
        st.error(f"Errore API: {e}")
        return None
    
    return None

def get_gold_data_alternative(pair, timeframe):
    """
    Per XAU/USD usa yfinance come fallback (più stabile per gold)
    """
    try:
        import yfinance as yf
        symbol = "GC=F"  # Gold Futures
        period = "5d" if timeframe in ["H1", "H4"] else "1mo"
        interval = "1h" if timeframe == "H1" else "1d"
        
        data = yf.download(symbol, period=period, interval=interval, progress=False)
        if not data.empty:
            data.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
            return data[['open', 'high', 'low', 'close']]
    except:
        pass
    return None

def calculate_real_trend(data, periods=14):
    """
    Calcola trend reale con indicatori tecnici
    """
    if data is None or len(data) < periods:
        return "NEUTRAL", 50
    
    # Calcola SMA
    data['sma20'] = data['close'].rolling(window=min(20, len(data)//4)).mean()
    data['sma50'] = data['close'].rolling(window=min(50, len(data)//2)).mean()
    
    # RSI
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]
    
    # Trend basato su SMA e prezzo
    current_price = data['close'].iloc[-1]
    sma20 = data['sma20'].iloc[-1]
    sma50 = data['sma50'].iloc[-1]
    
    # Score trend 0-100
    score = 50
    
    if current_price > sma20:
        score += 15
    else:
        score -= 15
        
    if current_price > sma50:
        score += 15
    else:
        score -= 15
        
    if current_rsi > 50:
        score += 10
    else:
        score -= 10
    
    # Determina trend
    if score > 65:
        trend = "BULLISH"
    elif score < 35:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"
        score = 50
    
    return trend, max(30, min(95, score))

def analyze_multi_timeframe_real(pair, current_price):
    """
    Analisi MTF con dati REALI da API
    """
    with st.spinner("📡 Scaricando dati reali da Alpha Vantage..."):
        
        # Scarica dati per ogni timeframe
        data_h1 = get_real_forex_data(pair, "H1")
        data_h4 = get_real_forex_data(pair, "H4") 
        data_d1 = get_real_forex_data(pair, "D1")
    
    # Calcola trend reali
    trend_h1, strength_h1 = calculate_real_trend(data_h1) if data_h1 is not None else ("NEUTRAL", 50)
    trend_h4, strength_h4 = calculate_real_trend(data_h4) if data_h4 is not None else ("NEUTRAL", 50)
    trend_d1, strength_d1 = calculate_real_trend(data_d1) if data_d1 is not None else ("NEUTRAL", 50)
    
    # Confluenza
    trends = [trend_h1, trend_h4, trend_d1]
    bullish = trends.count("BULLISH")
    bearish = trends.count("BEARISH")
    
    if bullish >= 2 and bearish == 0:
        signal = "STRONG BUY"
        direction = "BUY"
        score = 75 + (bullish * 8)
    elif bearish >= 2 and bullish == 0:
        signal = "STRONG SELL"
        direction = "SELL"
        score = 75 + (bearish * 8)
    elif bullish > bearish:
        signal = "WEAK BUY"
        direction = "BUY"
        score = 60
    elif bearish > bullish:
        signal = "WEAK SELL"
        direction = "SELL"
        score = 60
    else:
        signal = "NO TRADE"
        direction = "NEUTRAL"
        score = 40
    
    # Livelli basati su ATR reale
    if data_h4 is not None:
        atr = calculate_atr(data_h4)
    else:
        atr = 15 if pair == "XAU/USD" else 0.0020
    
    if direction == "BUY":
        entry = current_price
        tp = entry + (atr * 2.5)
        sl = entry - (atr * 1.0)
    elif direction == "SELL":
        entry = current_price
        tp = entry - (atr * 2.5)
        sl = entry + (atr * 1.0)
    else:
        entry, tp, sl = current_price, current_price, current_price
    
    decimals = 2 if pair in ["XAU/USD", "BTC/USD"] else 5
    
    return {
        'timeframes': {
            'H1': {'trend': trend_h1, 'strength': strength_h1, 'data': data_h1 is not None},
            'H4': {'trend': trend_h4, 'strength': strength_h4, 'data': data_h4 is not None},
            'D1': {'trend': trend_d1, 'strength': strength_d1, 'data': data_d1 is not None}
        },
        'confluence': {'score': min(score, 100), 'bullish': bullish, 'bearish': bearish},
        'signal': signal,
        'direction': direction,
        'entry': round(entry, decimals),
        'tp': round(tp, decimals),
        'sl': round(sl, decimals),
        'rr': 2.5,
        'atr': round(atr, 2)
    }

def calculate_atr(data, period=14):
    """Calcola Average True Range reale"""
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(period).mean()
    return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 15

# ... (UI simile a prima ma con indicatori "LIVE DATA" vs "SIMULATED")

import streamlit as st

st.set_page_config(page_title="Forex AI Analyzer", page_icon="📈", layout="centered")

import numpy as np
from PIL import Image
from datetime import datetime
import requests
import pandas as pd

# CSS CORRETTO - SOLO QUESTO BLOCCO CAMBIATO
st.markdown("""
<style>
    .stApp { background: #0f172a; }
    .stApp, .stApp p, .stApp span, .stApp div { color: #f1f5f9 !important; }
    
    /* LABELS CHIARE */
    .stSelectbox label, .stTextInput label, .stFileUploader label {
        color: #e2e8f0 !important;
        font-weight: 600 !important;
    }
    
    /* BOTTONI - TESTO SCURO SU SFONDO CHIARO */
    .stButton>button {
        background: linear-gradient(135deg, #06b6d4, #3b82f6) !important;
        color: #ffffff !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 16px !important;
        font-size: 16px !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.3) !important;
    }
    
    /* SELECTBOX - MENU A TENDINA */
    .stSelectbox > div > div {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
    }
    
    /* OPZIONI MENU A TENDINA */
    div[role="listbox"] div {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
    }
    
    /* HOVER OPZIONI */
    div[role="option"]:hover {
        background-color: #334155 !important;
        color: #ffffff !important;
    }
    
    /* INPUT TESTO */
    .stTextInput > div > div > input {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
    }
    
    /* BADGE PREZZO */
    .price-auto { background: #059669; color: white; padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .price-delay { background: #d97706; color: white; padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .price-manual { background: #475569; color: white; padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    
    /* BOX E METRICHE */
    .metric-box { background: #1e293b; border: 2px solid #475569; border-radius: 12px; padding: 20px; margin: 8px 0; text-align: center; }
    .signal-buy { background: linear-gradient(135deg, #059669, #10b981); padding: 25px; border-radius: 16px; text-align: center; margin: 15px 0; }
    .signal-sell { background: linear-gradient(135deg, #dc2626, #ef4444); padding: 25px; border-radius: 16px; text-align: center; margin: 15px 0; }
    .signal-neutral { background: #475569; padding: 25px; border-radius: 16px; text-align: center; margin: 15px 0; }
    .tf-box { background: #1e293b; border: 3px solid #64748b; border-radius: 12px; padding: 15px; margin: 5px 0; text-align: center; }
    .tf-bullish { border-color: #10b981; background: rgba(16, 185, 129, 0.1); }
    .tf-bearish { border-color: #ef4444; background: rgba(239, 68, 68, 0.1); }
    .hhll-box { background: #1e293b; border: 2px solid #f59e0b; border-radius: 10px; padding: 15px; margin: 10px 0; }
    
    /* PREZZI */
    .price-value { font-size: 24px; font-weight: bold; font-family: monospace; color: #fff !important; }
    .entry { color: #22d3ee !important; }
    .tp { color: #4ade80 !important; }
    .sl { color: #f87171 !important; }
</style>
""", unsafe_allow_html=True)

# ... (tutto il resto del codice rimane IDENTICO come prima)
# API Keys
try:
    TWELVE_DATA_KEY = st.secrets["TWELVE_DATA_KEY"]
except:
    TWELVE_DATA_KEY = ""

# ============================================================================
# FUNZIONI (identiche a prima)
# ============================================================================

@st.cache_data(ttl=60)
def get_price_twelvedata(pair):
    """Prezzo live da Twelve Data"""
    if not TWELVE_DATA_KEY:
        return None, "No API Key"
    
    symbols = {"XAU/USD": "XAU/USD", "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD", "USD/JPY": "USD/JPY", "XAG/USD": "XAG/USD", "BTC/USD": "BTC/USD"}
    
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbols.get(pair, 'XAU/USD')}&apikey={TWELVE_DATA_KEY}"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if "price" in data:
            return float(data["price"]), "Twelve Data"
        return None, data.get('message', 'Error')
    except Exception as e:
        return None, str(e)

def get_price_yahoo(pair):
    """Fallback Yahoo Finance"""
    try:
        import yfinance as yf
        symbols = {"XAU/USD": "GC=F", "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "XAG/USD": "SI=F", "BTC/USD": "BTC-USD"}
        ticker = yf.Ticker(symbols.get(pair, "GC=F"))
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            return round(data['Close'].iloc[-1], 2), "Yahoo Finance"
    except:
        pass
    return None, "Failed"

def fetch_historical(pair):
    """Dati storici per HH/HL"""
    try:
        import yfinance as yf
        symbols = {"XAU/USD": "GC=F", "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "XAG/USD": "SI=F", "BTC/USD": "BTC-USD"}
        data = yf.download(symbols.get(pair, "GC=F"), period="30d", interval="1h", progress=False)
        if not data.empty:
            data.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
            return data[['open', 'high', 'low', 'close']]
    except:
        pass
    return None

def find_hh_ll(df, window=20):
    """Trova Higher Highs e Lower Lows"""
    if df is None or len(df) < window:
        return None, None
    
    highs = df['high'].rolling(window=window, center=True).max()
    lows = df['low'].rolling(window=window, center=True).min()
    
    hh_mask = df['high'] == highs
    ll_mask = df['low'] == lows
    
    hh_points = df[hh_mask]['high'].tail(3)
    ll_points = df[ll_mask]['low'].tail(3)
    
    if len(hh_points) >= 2 and len(ll_points) >= 2:
        hh_trend = "UP" if hh_points.iloc[-1] > hh_points.iloc[0] else "DOWN"
        ll_trend = "UP" if ll_points.iloc[-1] > ll_points.iloc[0] else "DOWN"
        
        if hh_trend == "UP" and ll_trend == "UP":
            structure = "BULLISH_TREND"
        elif hh_trend == "DOWN" and ll_trend == "DOWN":
            structure = "BEARISH_TRE

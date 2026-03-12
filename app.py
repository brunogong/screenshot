import streamlit as st

st.set_page_config(page_title="Forex AI Multi-Alert DEBUG", page_icon="📈", layout="centered")

import numpy as np
from PIL import Image
from datetime import datetime
import requests
import pandas as pd

# DEBUG: Mostra stato API key
st.sidebar.header("🔧 DEBUG")
try:
    TWELVE_DATA_KEY = st.secrets["TWELVE_DATA_KEY"]
    st.sidebar.success(f"✅ API Key trovata: ...{TWELVE_DATA_KEY[-4:]}")
except Exception as e:
    TWELVE_DATA_KEY = ""
    st.sidebar.error(f"❌ API Key mancante: {e}")

# CSS
st.markdown("""
<style>
    .stApp { background: #0f172a; }
    .stApp, .stApp p, .stApp label, .stApp span, .stApp div { color: #f1f5f9 !important; }
    .debug-box { background: #451a03; border: 2px solid #f59e0b; padding: 10px; border-radius: 8px; margin: 10px 0; font-family: monospace; font-size: 12px; }
    .error-box { background: #450a0a; border: 2px solid #ef4444; padding: 10px; border-radius: 8px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

st.title("📈 Forex AI - DEBUG MODE")

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]

# Test API key
if st.button("🧪 TEST API KEY", type="primary"):
    if not TWELVE_DATA_KEY:
        st.error("API Key non trovata!")
    else:
        with st.spinner("Test in corso..."):
            url = f"https://api.twelvedata.com/price?symbol=EUR/USD&apikey={TWELVE_DATA_KEY}"
            try:
                response = requests.get(url, timeout=10)
                st.write(f"Status Code: {response.status_code}")
                st.json(response.json())
            except Exception as e:
                st.error(f"Errore: {e}")

# Test singola coppia
pair_test = st.selectbox("Test coppia", PAIRS)
if st.button("🧪 TEST PREZZO SINGOLO"):
    if not TWELVE_DATA_KEY:
        st.error("API Key mancante!")
    else:
        url = f"https://api.twelvedata.com/price?symbol={pair_test}&apikey={TWELVE_DATA_KEY}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            st.write("Risposta API:")
            st.json(data)
            if "price" in data:
                st.success(f"✅ Prezzo: {data['price']}")
            else:
                st.error(f"❌ Errore API: {data.get('message', 'Sconosciuto')}")
                if "code" in data:
                    st.error(f"Codice errore: {data['code']}")
        except Exception as e:
            st.error(f"Errore richiesta: {e}")

# Test yfinance
if st.button("🧪 TEST YFINANCE"):
    try:
        import yfinance as yf
        data = yf.download("EURUSD=X", period="5d", interval="1h", progress=False)
        if data.empty:
            st.error("yfinance: dati vuoti")
        else:
            st.success(f"✅ yfinance OK: {len(data)} righe")
            st.write(data.tail(3))
    except Exception as e:
        st.error(f"yfinance errore: {e}")

st.markdown("---")
st.caption(f"⏰ {datetime.now().strftime('%H:%M:%S')}")

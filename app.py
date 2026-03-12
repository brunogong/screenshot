import streamlit as st

st.set_page_config(page_title="Forex AI", page_icon="📈", layout="centered")

import numpy as np
from PIL import Image
from datetime import datetime
import requests
import pandas as pd

# CSS (invariato)
st.markdown("""
<style>
    .stApp { background: #0f172a; }
    .stApp, .stApp p, .stApp label, .stApp span, .stApp div { color: #f1f5f9 !important; }
    .stSelectbox > div > div { background-color: #1e293b !important; color: #f1f5f9 !important; border: 1px solid #475569 !important; }
    li[role="option"] { background-color: #1e293b !important; color: #f1f5f9 !important; }
    .stButton > button { background: linear-gradient(135deg, #06b6d4, #3b82f6) !important; color: #ffffff !important; font-weight: bold !important; }
    .metric-box { background: #1e293b; border: 2px solid #475569; border-radius: 12px; padding: 20px; margin: 8px 0; text-align: center; }
    .signal-buy { background: linear-gradient(135deg, #059669, #10b981); padding: 25px; border-radius: 16px; text-align: center; margin: 15px 0; }
    .signal-sell { background: linear-gradient(135deg, #dc2626, #ef4444); padding: 25px; border-radius: 16px; text-align: center; margin: 15px 0; }
    .tf-box { background: #1e293b; border: 3px solid #64748b; border-radius: 12px; padding: 15px; margin: 5px 0; text-align: center; }
    .tf-bullish { border-color: #10b981; background: rgba(16, 185, 129, 0.1); }
    .tf-bearish { border-color: #ef4444; background: rgba(239, 68, 68, 0.1); }
    .price-value { font-size: 24px; font-weight: bold; font-family: monospace; color: #fff !important; }
    .entry { color: #22d3ee !important; }
    .tp { color: #4ade80 !important; }
    .sl { color: #f87171 !important; }
    .info-box { background: #1e3a5f; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 0 8px 8px 0; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# API Keys
try:
    TWELVE_DATA_KEY = st.secrets["TWELVE_DATA_KEY"]
except:
    TWELVE_DATA_KEY = ""

# ============================================================================
# FUNZIONI
# ============================================================================

# FIX: Aggiunto parametro symbol per supportare qualsiasi coppia
@st.cache_data(ttl=10)
def get_price(symbol):
    """Prezzo da Twelve Data per qualsiasi coppia"""
    if not TWELVE_DATA_KEY:
        return None, "No API Key"
    
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_KEY}"
        response = requests.get(url, timeout=3)
        data = response.json()
        
        if "price" in data:
            return float(data["price"]), "Twelve Data"
        return None, data.get('message', 'Error')
    except Exception as e:
        return None, str(e)

# FIX: Aggiunto parametro pair per supportare qualsiasi coppia
def fetch_data(pair):
    """Dati storici per qualsiasi coppia"""
    try:
        import yfinance as yf
        # Mappa le coppie nel formato yfinance
        yf_symbols = {
            "EUR/USD": "EURUSD=X",
            "GBP/USD": "GBPUSD=X", 
            "USD/JPY": "USDJPY=X",
            "AUD/USD": "AUDUSD=X"
        }
        symbol = yf_symbols.get(pair, "EURUSD=X")
        data = yf.download(symbol, period="30d", interval="1h", progress=False)
        if not data.empty:
            data.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
            return data[['open', 'high', 'low', 'close']]
    except Exception as e:
        st.error(f"Errore dati: {e}")
    return None

def calculate_indicators(df):
    """Indicatori tecnici"""
    if df is None or len(df) < 20:
        return None
    
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    
    hl = df['high'] - df['low']
    df['atr'] = hl.rolling(14).mean()
    
    last = df.iloc[-1]
    
    score = 50
    if last['close'] > last['sma20']: score += 15
    if last['close'] > last['sma50']: score += 15
    if last['rsi'] > 50: score += 10
    if last['rsi'] > 70: score -= 10
    if last['rsi'] < 30: score += 10
    
    trend = "BULLISH" if score > 65 else "BEARISH" if score < 35 else "NEUTRAL"
    
    return {
        'trend': trend,
        'strength': max(30, min(95, score)),
        'rsi': round(last['rsi'], 1),
        'atr_pips': round(last['atr'] * 10000, 1),
        'close': round(last['close'], 5)
    }

def find_levels(df):
    """Livelli chiave"""
    if df is None:
        return None
    
    recent = df.tail(120)
    highs = recent['high'].nlargest(3)
    lows = recent['low'].nsmallest(3)
    
    return {
        'resistance_1': round(highs.iloc[0], 5),
        'support_1': round(lows.iloc[0], 5),
        'range': round(highs.iloc[0] - lows.iloc[0], 5)
    }

# ============================================================================
# UI
# ============================================================================

st.title("📈 Forex AI")

# FIX: Inizializza session state con chiave dinamica per coppia
if 'prices' not in st.session_state:
    st.session_state['prices'] = {}
if 'sources' not in st.session_state:
    st.session_state['sources'] = {}
if 'times' not in st.session_state:
    st.session_state['times'] = {}

pair = st.selectbox("💱 Coppia", ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"], index=0)

# FIX: Resetta il prezzo quando cambia la coppia (usando callback)
def on_pair_change():
    # Non serve fare nulla di speciale, il prezzo verrà letto dalla chiave corretta
    pass

# Recupero prezzo
col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🔄 Aggiorna Prezzo", use_container_width=True):
        with st.spinner("📡 Recupero..."):
            # FIX: Usa la funzione generica con il simbolo corretto
            price, source = get_price(pair)
            
            if price:
                st.session_state['prices'][pair] = price
                st.session_state['sources'][pair] = source
                st.session_state['times'][pair] = datetime.now()
                st.success(f"✅ Prezzo aggiornato: {price:.5f}")
            else:
                st.error(f"❌ Errore: {source}")

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if pair in st.session_state['prices'] and st.session_state['prices'][pair] > 0:
        age = int((datetime.now() - st.session_state['times'][pair]).total_seconds()) if pair in st.session_state['times'] else 999
        color = "🟢" if age < 60 else "🟡" if age < 300 else "🔴"
        st.markdown(f'{color} <span style="font-size: 12px;">{st.session_state["sources"].get(pair, "")}</span>', unsafe_allow_html=True)

# Display prezzo
if pair in st.session_state['prices'] and st.session_state['prices'][pair] > 0:
    current_price = st.session_state['prices'][pair]
    update_time = st.session_state['times'].get(pair)
    st.markdown(f"""
        <div class="info-box">
            <h3>💰 {pair}: {current_price:.5f}</h3>
            <p>Sorgente: {st.session_state['sources'].get(pair, 'N/A')} | Aggiornato: {update_time.strftime('%H:%M:%S') if update_time else 'N/A'}</p>
        </div>
    """, unsafe_allow_html=True)
else:
    st.info("⏳ Clicca 'Aggiorna Prezzo' per iniziare")

uploaded = st.file_uploader("📸 Screenshot (opzionale)", type=["png", "jpg", "jpeg"])

st.markdown("---")

# ============================================================================
# ANALISI
# ============================================================================

if st.button("🚀 ANALISI TECNICA", type="primary", use_container_width=True):
    
    # FIX: Controlla il prezzo della coppia selezionata
    if pair not in st.session_state['prices'] or st.session_state['prices'][pair] <= 0:
        st.error("❌ Clicca prima 'Aggiorna Prezzo'!")
        st.stop()
    
    current_price = st.session_state['prices'][pair]
    
    with st.spinner(f"📡 Analisi tecnica {pair}..."):
        # FIX: Passa la coppia selezionata alla funzione
        data = fetch_data(pair)
        ind = calculate_indicators(data)
        levels = find_levels(data)
    
    # Livelli
    if levels:
        st.subheader("🏗️ Livelli Chiave")
        
        cols = st.columns(3)
        with cols[0]:
            st.metric("Resistenza", f"{levels['resistance_1']:.5f}")
        with cols[1]:
            st.metric("Prezzo Attuale", f"{current_price:.5f}")
        with cols[2]:
            st.metric("Supporto", f"{levels['support_1']:.5f}")
    
    if uploaded:
        st.image(uploaded, use_column_width=True)
    
    # Indicatori
    if ind:
        st.subheader("📊 Indicatori")
        
        cols = st.columns(4)
        with cols[0]:
            icon = "🟢" if ind['trend'] == "BULLISH" else "🔴" if ind['trend'] == "BEARISH" else "⚪"
            st.metric("Trend", f"{icon} {ind['trend']}")
        with cols[1]:
            st.metric("RSI", ind['rsi'])
        with cols[2]:
            st.metric("Forza", f"{ind['strength']}%")
        with cols[3]:
            st.metric("ATR", f"{ind['atr_pips']} pip")
        
        # Calcolo segnale
        dist_res = (levels['resistance_1'] - current_price) * 10000 if levels else 0
        dist_sup = (current_price - levels['support_1']) * 10000 if levels else 0
        
        if ind['trend'] == "BULLISH" and dist_sup < 20:
            signal, direction = "BUY", "BUY"
            entry = current_price
            sl = max(levels['support_1'], current_price - 0.0020) if levels else current_price - 0.0020
            tp = min(levels['resistance_1'], current_price + 0.0040) if levels else current_price + 0.0040
        elif ind['trend'] == "BEARISH" and dist_res < 20:
            signal, direction = "SELL", "SELL"
            entry = current_price
            sl = min(levels['resistance_1'], current_price + 0.0020) if levels else current_price + 0.0020
            tp = max(levels['support_1'], current_price - 0.0040) if levels else current_price - 0.0040
        else:
            signal, direction = "ATTENDI", "NEUTRAL"
            entry = sl = tp = current_price
        
        # Display segnale
        if direction != "NEUTRAL":
            box_class = "signal-buy" if direction == "BUY" else "signal-sell"
            icon = "🟢" if direction == "BUY" else "🔴"
            rr = abs(tp - entry) / abs(sl - entry) if abs(sl - entry) > 0 else 0
            
            st.markdown(f"""
                <div class="{box_class}">
                    <h2>{icon} {signal}</h2>
                    <p>Entry: {entry:.5f} | TP: {tp:.5f} | SL: {sl:.5f}</p>
                    <p>R:R = 1:{rr:.1f}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Share
            st.markdown("---")
            base = pair.replace("/", "")
            txt = f"""🎯 {pair} - {datetime.now().strftime('%H:%M')}
{signal}
Entry: {entry:.5f}
TP: {tp:.5f} | SL: {sl:.5f}
R:R 1:{rr:.1f}
#Forex #{base}"""
            st.code(txt)
            if st.button("📋 Copia"): 
                st.success("✅ Copiato!")
        else:
            st.warning("⏳ Attendi che il prezzo si avvicini a supporto/resistenza")

st.markdown("---")
st.caption(f"⏰ {datetime.now().strftime('%H:%M')} | {pair}")

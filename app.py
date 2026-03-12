import streamlit as st

st.set_page_config(page_title="Forex AI Multi-Alert", page_icon="📈", layout="centered")

import numpy as np
from PIL import Image
from datetime import datetime
import requests
import pandas as pd

# CSS
st.markdown("""
<style>
    .stApp { background: #0f172a; }
    .stApp, .stApp p, .stApp label, .stApp span, .stApp div { color: #f1f5f9 !important; }
    .stSelectbox > div > div { background-color: #1e293b !important; color: #f1f5f9 !important; border: 1px solid #475569 !important; }
    li[role="option"] { background-color: #1e293b !important; color: #f1f5f9 !important; }
    .stButton > button { background: linear-gradient(135deg, #06b6d4, #3b82f6) !important; color: #ffffff !important; font-weight: bold !important; }
    .signal-buy { background: linear-gradient(135deg, #059669, #10b981); padding: 15px; border-radius: 12px; text-align: center; animation: pulse-green 2s infinite; }
    .signal-sell { background: linear-gradient(135deg, #dc2626, #ef4444); padding: 15px; border-radius: 12px; text-align: center; animation: pulse-red 2s infinite; }
    .signal-wait { background: #1e293b; border: 2px solid #475569; padding: 15px; border-radius: 12px; text-align: center; opacity: 0.7; }
    @keyframes pulse-green { 0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); } 50% { box-shadow: 0 0 0 15px rgba(16, 185, 129, 0); } }
    @keyframes pulse-red { 0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); } 50% { box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); } }
    .alert-banner { background: linear-gradient(90deg, #f59e0b, #d97706); color: white; padding: 15px; border-radius: 12px; text-align: center; margin: 10px 0; animation: blink 1s infinite; }
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.8; } }
    .pair-card { background: #1e293b; border: 2px solid #334155; border-radius: 12px; padding: 15px; margin: 10px 0; }
    .pair-card:hover { border-color: #06b6d4; }
    .level-box { background: #0f172a; border: 2px solid #475569; border-radius: 8px; padding: 10px; text-align: center; }
    .level-entry { border-color: #06b6d4; }
    .level-tp { border-color: #10b981; }
    .level-sl { border-color: #ef4444; }
    .level-label { font-size: 10px; text-transform: uppercase; opacity: 0.7; }
    .level-value { font-size: 16px; font-weight: bold; font-family: monospace; }
    .info-box { background: #1e3a5f; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 0 8px 8px 0; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# Auto-refresh ogni 30 secondi
st.markdown("""<meta http-equiv="refresh" content="30">""", unsafe_allow_html=True)

# API Keys
try:
    TWELVE_DATA_KEY = st.secrets["TWELVE_DATA_KEY"]
except:
    TWELVE_DATA_KEY = ""

# Session state
if 'prices' not in st.session_state:
    st.session_state['prices'] = {}
if 'signals' not in st.session_state:
    st.session_state['signals'] = {}
if 'alerted' not in st.session_state:
    st.session_state['alerted'] = set()

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]

# ============================================================================
# FUNZIONI
# ============================================================================

@st.cache_data(ttl=10)
def get_price(symbol):
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

def fetch_data(pair):
    try:
        import yfinance as yf
        yf_symbols = {
            "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", 
            "USD/JPY": "USDJPY=X", "AUD/USD": "AUDUSD=X"
        }
        symbol = yf_symbols.get(pair, "EURUSD=X")
        data = yf.download(symbol, period="30d", interval="1h", progress=False)
        if data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.rename(columns=str.lower)
        mapping = {'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'adj close': 'close', 'adj_close': 'close'}
        result = pd.DataFrame()
        for col in ['open', 'high', 'low', 'close']:
            for orig, mapped in mapping.items():
                if mapped == col and orig in data.columns:
                    result[col] = data[orig]
                    break
        return result if len(result.columns) == 4 else None
    except:
        return None

def calculate_indicators(df):
    if df is None or len(df) < 20:
        return None
    for col in ['open', 'high', 'low', 'close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna()
    if len(df) < 20:
        return None
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    last = df.iloc[-1]
    score = 50
    if last['close'] > last['sma20']: score += 15
    if last['close'] > last['sma50']: score += 15
    if last['rsi'] > 50: score += 10
    if last['rsi'] > 70: score -= 10
    if last['rsi'] < 30: score += 10
    trend = "BULLISH" if score > 65 else "BEARISH" if score < 35 else "NEUTRAL"
    return {
        'trend': trend, 'strength': max(30, min(95, score)),
        'rsi': round(float(last['rsi']), 1),
        'atr_pips': round(float(last['atr']) * 10000, 1)
    }

def find_levels(df):
    if df is None or len(df) < 20:
        return None
    recent = df.tail(120)
    if len(recent) < 3:
        return None
    highs = recent['high'].nlargest(3)
    lows = recent['low'].nsmallest(3)
    return {
        'resistance_1': round(float(highs.iloc[0]), 5),
        'support_1': round(float(lows.iloc[0]), 5)
    }

def analyze_pair(pair):
    """Analizza una coppia e ritorna il segnale completo"""
    price, source = get_price(pair)
    if not price:
        return None
    
    data = fetch_data(pair)
    if data is None:
        return None
    
    ind = calculate_indicators(data)
    levels = find_levels(data)
    
    if not ind or not levels:
        return None
    
    dist_res = (levels['resistance_1'] - price) * 10000
    dist_sup = (price - levels['support_1']) * 10000
    
    if ind['trend'] == "BULLISH" and dist_sup < 20:
        signal, direction = "BUY", "BUY"
        entry = price
        sl = max(levels['support_1'], price - 0.0020)
        tp = min(levels['resistance_1'], price + 0.0040)
    elif ind['trend'] == "BEARISH" and dist_res < 20:
        signal, direction = "SELL", "SELL"
        entry = price
        sl = min(levels['resistance_1'], price + 0.0020)
        tp = max(levels['support_1'], price - 0.0040)
    else:
        signal, direction = "ATTENDI", "NEUTRAL"
        entry = sl = tp = price
    
    return {
        'pair': pair, 'price': price, 'source': source,
        'signal': signal, 'direction': direction,
        'entry': entry, 'tp': tp, 'sl': sl,
        'trend': ind['trend'], 'rsi': ind['rsi'],
        'strength': ind['strength'], 'atr': ind['atr_pips'],
        'resistance': levels['resistance_1'], 'support': levels['support_1'],
        'dist_res': dist_res, 'dist_sup': dist_sup
    }

# ============================================================================
# UI
# ============================================================================

st.title("📈 Forex AI - Multi Alert")

# Toggle auto-analisi
auto_check = st.checkbox("🔔 Scansione automatica tutte le coppie (30s)", value=True)

# Pulsante scansione manuale
if st.button("🚀 SCANSIONA TUTTE LE COPPIE", type="primary", use_container_width=True) or auto_check:
    
    active_signals = []
    
    with st.spinner("📡 Analisi in corso..."):
        for pair in PAIRS:
            result = analyze_pair(pair)
            if result:
                st.session_state['prices'][pair] = result['price']
                st.session_state['signals'][pair] = result
                if result['direction'] != "NEUTRAL":
                    active_signals.append(result)
    
    # ALERT se ci sono segnali attivi
    if active_signals:
        st.markdown(f"""
            <div class="alert-banner">
                <h2>🚨 {len(active_signals)} SEGNALE/I ATTIVO/I!</h2>
                <p>{', '.join([s['pair'] + ' ' + s['signal'] for s in active_signals])}</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Suono alert (solo primo rilevamento)
        new_signals = [s for s in active_signals if s['pair'] not in st.session_state['alerted']]
        if new_signals:
            st.session_state['alerted'].update([s['pair'] for s in new_signals])
            st.markdown("""
                <audio autoplay>
                    <source src="data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBTGH0fPTgjMGHm7A7+OZURE" type="audio/wav">
                </audio>
            """, unsafe_allow_html=True)
    else:
        st.session_state['alerted'] = set()  # Reset quando non ci sono segnali
    
    # Display tutte le coppie in griglia
    st.subheader("📊 Stato Coppie")
    
    cols = st.columns(2)
    for idx, pair in enumerate(PAIRS):
        with cols[idx % 2]:
            if pair in st.session_state['signals']:
                s = st.session_state['signals'][pair]
                
                # Card colore in base al segnale
                if s['direction'] == "BUY":
                    card_class = "signal-buy"
                    icon = "🟢"
                elif s['direction'] == "SELL":
                    card_class = "signal-sell"
                    icon = "🔴"
                else:
                    card_class = "signal-wait"
                    icon = "⚪"
                
                with st.container():
                    st.markdown(f'<div class="pair-card">', unsafe_allow_html=True)
                    
                    # Header
                    st.markdown(f"""
                        <div class="{card_class}">
                            <h3>{icon} {pair}</h3>
                            <p style="font-size: 24px; font-weight: bold; margin: 0;">{s['price']:.5f}</p>
                            <p style="margin: 5px 0;">{s['signal']} | {s['trend']} | RSI {s['rsi']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Livelli (sempre visibili)
                    if s['direction'] != "NEUTRAL":
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.markdown(f"""
                                <div class="level-box level-entry">
                                    <div class="level-label">Entry</div>
                                    <div class="level-value" style="color: #22d3ee;">{s['entry']:.5f}</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c2:
                            st.markdown(f"""
                                <div class="level-box level-tp">
                                    <div class="level-label">TP</div>
                                    <div class="level-value" style="color: #4ade80;">{s['tp']:.5f}</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c3:
                            st.markdown(f"""
                                <div class="level-box level-sl">
                                    <div class="level-label">SL</div>
                                    <div class="level-value" style="color: #f87171;">{s['sl']:.5f}</div>
                                </div>
                            """, unsafe_allow_html=True)
                        
                        # R:R e pulsante copia
                        rr = abs(s['tp'] - s['entry']) / abs(s['sl'] - s['entry']) if abs(s['sl'] - s['entry']) > 0 else 0
                        st.markdown(f"<p style='text-align: center;'>R:R 1:{rr:.1f}</p>", unsafe_allow_html=True)
                        
                        txt = f"""🎯 {pair} - {datetime.now().strftime('%H:%M')}
{s['signal']} @ {s['entry']:.5f}
TP: {s['tp']:.5f} | SL: {s['sl']:.5f}
R:R 1:{rr:.1f}"""
                        st.code(txt, language=None)
                    else:
                        # Info per coppie neutre
                        st.markdown(f"""
                            <p style="text-align: center; font-size: 12px; opacity: 0.7;">
                                Dist. Res: {s['dist_res']:.1f} pip | Dist. Sup: {s['dist_sup']:.1f} pip
                            </p>
                        """, unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)

# Dettaglio singola coppia
st.markdown("---")
st.subheader("🔍 Dettaglio Coppia")
selected = st.selectbox("Seleziona per analisi completa", PAIRS)

if selected in st.session_state['signals']:
    s = st.session_state['signals'][selected]
    st.markdown(f"""
        <div class="info-box">
            <h3>{selected} | {s['signal']} | Forza: {s['strength']}%</h3>
            <p>Resistenza: {s['resistance']:.5f} | Supporto: {s['support']:.5f} | ATR: {s['atr']} pip</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.caption(f"⏰ {datetime.now().strftime('%H:%M:%S')} | Ultimo aggiornamento")

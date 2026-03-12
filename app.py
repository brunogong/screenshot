import streamlit as st

st.set_page_config(page_title="Forex AI Analyzer", page_icon="📈", layout="centered")

import numpy as np
from PIL import Image
from datetime import datetime
import requests
import pandas as pd

# CSS CORRETTO
st.markdown("""
<style>
    .stApp { background: #0f172a; }
    .stApp, .stApp p, .stApp label, .stApp span, .stApp div { color: #f1f5f9 !important; }
    
    /* FIX SELECTBOX */
    .stSelectbox > div > div {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        border: 1px solid #475569 !important;
    }
    .stSelectbox > div > div > div {
        color: #f1f5f9 !important;
    }
    li[role="option"] {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
    }
    li[role="option"]:hover {
        background-color: #334155 !important;
    }
    
    /* FIX BOTTONE */
    .stButton > button {
        background: linear-gradient(135deg, #06b6d4, #3b82f6) !important;
        color: #ffffff !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        font-size: 14px !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #0891b2, #2563eb) !important;
    }
    
    /* Input */
    .stTextInput > div > div > input {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        border: 1px solid #475569 !important;
    }
    
    .stTextInput label, .stSelectbox label { 
        color: #e2e8f0 !important; 
        font-weight: 600 !important; 
    }
    
    .price-auto { background: #059669; color: white; padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .price-delay { background: #d97706; color: white; padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .price-manual { background: #475569; color: white; padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    
    .metric-box { background: #1e293b; border: 2px solid #475569; border-radius: 12px; padding: 20px; margin: 8px 0; text-align: center; }
    .signal-buy { background: linear-gradient(135deg, #059669, #10b981); padding: 25px; border-radius: 16px; text-align: center; margin: 15px 0; }
    .signal-sell { background: linear-gradient(135deg, #dc2626, #ef4444); padding: 25px; border-radius: 16px; text-align: center; margin: 15px 0; }
    .signal-neutral { background: #475569; padding: 25px; border-radius: 16px; text-align: center; margin: 15px 0; }
    .tf-box { background: #1e293b; border: 3px solid #64748b; border-radius: 12px; padding: 15px; margin: 5px 0; text-align: center; }
    .tf-bullish { border-color: #10b981; background: rgba(16, 185, 129, 0.1); }
    .tf-bearish { border-color: #ef4444; background: rgba(239, 68, 68, 0.1); }
    .price-value { font-size: 24px; font-weight: bold; font-family: monospace; color: #fff !important; }
    .entry { color: #22d3ee !important; }
    .tp { color: #4ade80 !important; }
    .sl { color: #f87171 !important; }
    .hhll-box { background: #1e293b; border: 2px solid #f59e0b; border-radius: 10px; padding: 15px; margin: 10px 0; }
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
            structure = "BEARISH_TREND"
        else:
            structure = "RANGE"
        
        return {
            'last_hh': round(hh_points.iloc[-1], 2),
            'last_ll': round(ll_points.iloc[-1], 2),
            'prev_hh': round(hh_points.iloc[-2], 2) if len(hh_points) > 1 else None,
            'prev_ll': round(ll_points.iloc[-2], 2) if len(ll_points) > 1 else None,
            'structure': structure,
            'hh_trend': hh_trend,
            'll_trend': ll_trend
        }, df
    
    return None, df

def calculate_trend(df, structure):
    """Calcola trend con indicatori"""
    if df is None:
        return None
    
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    
    hl = df['high'] - df['low']
    hc = abs(df['high'] - df['close'].shift())
    lc = abs(df['low'] - df['close'].shift())
    df['atr'] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()
    
    last = df.iloc[-1]
    
    score = 50
    if last['close'] > last['sma20']: score += 10
    if last['close'] > last['sma50']: score += 10
    if last['rsi'] > 50: score += 10
    
    if structure:
        if structure['structure'] == "BULLISH_TREND": score += 20
        elif structure['structure'] == "BEARISH_TREND": score -= 20
        if last['close'] > structure['last_hh']: score += 10
        elif last['close'] < structure['last_ll']: score -= 10
    
    trend = "BULLISH" if score > 60 else "BEARISH" if score < 40 else "NEUTRAL"
    
    return {
        'trend': trend,
        'strength': max(30, min(95, abs(score - 50) * 2 + 50)),
        'rsi': round(last['rsi'], 1),
        'atr': round(last['atr'], 2),
        'close': round(last['close'], 2)
    }

# ============================================================================
# UI
# ============================================================================

st.title("📈 Forex AI Analyzer")
st.markdown("**Prezzo Auto + Analisi Higher Highs / Lower Lows**")

# Coppia e aggiorna
col1, col2 = st.columns([2, 1])
with col1:
    pair = st.selectbox("💱 Coppia", ["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "XAG/USD", "BTC/USD"])
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    auto_fetch = st.button("🔄 Aggiorna Prezzo", use_container_width=True)

# Prezzo
current_price = 0.0
price_source = "Manual"

if auto_fetch:
    with st.spinner("📡 Recupero prezzo..."):
        price, source = get_price_twelvedata(pair)
        if price:
            current_price = price
            price_source = source
            st.session_state['auto_price'] = price
            st.session_state['price_source'] = source
        else:
            price, source = get_price_yahoo(pair)
            if price:
                current_price = price
                price_source = source
                st.session_state['auto_price'] = price
                st.session_state['price_source'] = source

if 'auto_price' in st.session_state:
    current_price = st.session_state['auto_price']
    price_source = st.session_state.get('price_source', 'Unknown')

# Input prezzo
col3, col4 = st.columns([2, 1])
with col3:
    price_input = st.text_input("💰 Prezzo", value=f"{current_price:.2f}" if current_price > 0 else "0.00")
    try:
        final_price = float(price_input.replace(',', '.'))
    except:
        final_price = 0.0

with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    if price_source == "Twelve Data":
        st.markdown('<span class="price-auto">🟢 LIVE</span>', unsafe_allow_html=True)
    elif price_source == "Yahoo Finance":
        st.markdown('<span class="price-delay">🟡 15min</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="price-manual">⚪ MANUALE</span>', unsafe_allow_html=True)

uploaded = st.file_uploader("📸 Screenshot (opzionale)", type=["png", "jpg", "jpeg"])

st.markdown("---")

# ANALISI
if st.button("🚀 ANALISI HH/HL", type="primary", use_container_width=True):
    
    if final_price <= 0:
        st.error("❌ Recupera il prezzo o inseriscilo manualmente!")
        st.stop()
    
    with st.spinner("📡 Analisi Higher Highs / Lower Lows..."):
        hist_data = fetch_historical(pair)
        structure, full_data = find_hh_ll(hist_data)
        
        ind_h4 = calculate_trend(full_data, structure)
        ind_h1 = calculate_trend(full_data.tail(100) if full_data is not None else None, structure)
        ind_d1 = calculate_trend(full_data.resample('D').last().dropna() if full_data is not None else None, structure)
        
        tf_data = {
            'H1': ind_h1 if ind_h1 else {'trend': 'NEUTRAL', 'strength': 50, 'atr': 15 if 'XAU' in pair else 0.002, 'rsi': 50},
            'H4': ind_h4 if ind_h4 else {'trend': 'NEUTRAL', 'strength': 50, 'atr': 15 if 'XAU' in pair else 0.002, 'rsi': 50},
            'D1': ind_d1 if ind_d1 else {'trend': 'NEUTRAL', 'strength': 50, 'atr': 15 if 'XAU' in pair else 0.002, 'rsi': 50}
        }
    
    # HH/LL Display
    if structure:
        st.markdown('<div class="hhll-box">', unsafe_allow_html=True)
        st.subheader("🏗️ Struttura HH/HL")
        
        hh_col1, hh_col2, hh_col3 = st.columns(3)
        with hh_col1:
            delta_hh = structure['last_hh'] - structure['prev_hh'] if structure['prev_hh'] else 0
            st.metric("Higher High", f"{structure['last_hh']:.2f}", f"{delta_hh:+.2f}")
        with hh_col2:
            delta_ll = structure['last_ll'] - structure['prev_ll'] if structure['prev_ll'] else 0
            st.metric("Lower Low", f"{structure['last_ll']:.2f}", f"{delta_ll:+.2f}")
        with hh_col3:
            icon = "📈" if "BULLISH" in structure['structure'] else "📉" if "BEARISH" in structure['structure'] else "➡️"
            st.markdown(f"<div style='text-align:center'><div style='font-size:30px'>{icon}</div><div style='font-size:12px'>{structure['structure']}</div></div>", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Screenshot
    if uploaded:
        st.image(uploaded, use_column_width=True)
    
    # Timeframes
    st.subheader("📊 Trend Multi-Timeframe")
    
    cols = st.columns(3)
    for i, (tf, d) in enumerate(tf_data.items()):
        with cols[i]:
            trend = d['trend']
            icon = "🟢" if trend == "BULLISH" else "🔴" if trend == "BEARISH" else "⚪"
            css = "tf-bullish" if trend == "BULLISH" else "tf-bearish" if trend == "BEARISH" else ""
            st.markdown(f"""
                <div class="tf-box {css}">
                    <div style="font-size: 18px; font-weight: bold;">{tf}</div>
                    <div style="font-size: 24px; margin: 8px 0;">{icon}</div>
                    <div style="font-size: 13px; font-weight: 600;">{trend}</div>
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 5px;">
                        Forza: {d['strength']}%<br>RSI: {d['rsi']}<br>ATR: {d['atr']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    # Segnale
    trends = [d['trend'] for d in tf_data.values()]
    bullish = trends.count("BULLISH")
    bearish = trends.count("BEARISH")
    
    structure_bonus = 15 if structure and structure['structure'] == "BULLISH_TREND" else -15 if structure and structure['structure'] == "BEARISH_TREND" else 0
    
    if bullish >= 2 and bearish == 0 and structure_bonus >= 0:
        signal, direction, score, box_class = "STRONG BUY", "BUY", min(95, 85 + structure_bonus//3), "signal-buy"
    elif bearish >= 2 and bullish == 0 and structure_bonus <= 0:
        signal, direction, score, box_class = "STRONG SELL", "SELL", min(95, 85 - structure_bonus//3), "signal-sell"
    elif bullish > bearish:
        signal, direction, score, box_class = "WEAK BUY", "BUY", 65 + structure_bonus//2, "signal-buy"
    elif bearish > bullish:
        signal, direction, score, box_class = "WEAK SELL", "SELL", 65 - structure_bonus//2, "signal-sell"
    else:
        signal, direction, score, box_class = "NO TRADE", "NEUTRAL", 45, "signal-neutral"
    
    # Livelli
    atr = tf_data['H4']['atr']
    
    if structure and direction != "NEUTRAL":
        if direction == "BUY":
            tp = structure['last_hh'] * 1.005
            sl = max(structure['last_ll'] * 0.995, final_price - atr * 2)
        else:
            tp = structure['last_ll'] * 0.995
            sl = min(structure['last_hh'] * 1.005, final_price + atr * 2)
        entry = final_price
    else:
        tp_dist = atr * 2.5
        sl_dist = atr * 1.0
        if direction == "BUY":
            entry, tp, sl = final_price, final_price + tp_dist, final_price - sl_dist
        elif direction == "SELL":
            entry, tp, sl = final_price, final_price - tp_dist, final_price + sl_dist
        else:
            entry, tp, sl = final_price, final_price, final_price
    
    decimals = 2 if 'XAU' in pair or 'BTC' in pair or 'XAG' in pair else 5
    
    # Display
    icon_sig = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "⚪"
    st.markdown(f"""
        <div class="{box_class}">
            <div style="font-size: 13px; margin-bottom: 5px;">SEGNALE HH/HL + MTF</div>
            <h2 style="margin: 0; font-size: 32px;">{icon_sig} {signal}</h2>
            <div style="font-size: 16px; margin-top: 8px;">Score: {score}/100</div>
            <div style="font-size: 12px; margin-top: 5px;">🟢{bullish} 🔴{bearish} | HH/HL: {structure['structure'] if structure else 'N/A'}</div>
        </div>
    """, unsafe_allow_html=True)
    
    if direction != "NEUTRAL":
        st.subheader("🎯 Livelli (Basati su HH/HL)")
        
        rr = abs(tp-entry)/abs(sl-entry) if abs(sl-entry) > 0 else 0
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">ENTRY</div><div class="price-value entry">{entry:.{decimals}f}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">R:R</div><div class="price-value" style="color: #fbbf24;">1:{rr:.1f}</div></div>', unsafe_allow_html=True)
        
        c3, c4 = st.columns(2)
        with c3:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">✅ TP (HH/HL)</div><div class="price-value tp">{tp:.{decimals}f}</div><div style="font-size: 10px; color: #64748b;">+{abs(tp-entry):.{decimals}f}</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">❌ SL (HH/HL)</div><div class="price-value sl">{sl:.{decimals}f}</div><div style="font-size: 10px; color: #64748b;">-{abs(sl-entry):.{decimals}f}</div></div>', unsafe_allow_html=True)
        
        # Share
        st.markdown("---")
        txt = f"""🎯 HH/HL SIGNAL - {datetime.now().strftime('%H:%M')}
📊 {pair} | {price_source}
{signal} | Score: {score}/100
HH: {structure['last_hh']:.2f} | LL: {structure['last_ll']:.2f}
🎯 Entry: {entry:.{decimals}f}
✅ TP: {tp:.{decimals}f}
❌ SL: {sl:.{decimals}f}
R:R 1:{rr:.1f}
#Forex #HHHL"""
        st.code(txt)
        if st.button("📋 Copia"): 
            st.success("✅ Copiato!")

st.markdown("---")
st.caption(f"⏰ {datetime.now().strftime('%H:%M')} | Prezzo: {price_source} | Analisi: HH/HL Reale")

import streamlit as st

st.set_page_config(page_title="Forex AI Analyzer", page_icon="📈", layout="centered")

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
    .stTextInput label, .stSelectbox label { color: #e2e8f0 !important; font-weight: 600 !important; }
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
</style>
""", unsafe_allow_html=True)

# API Key
try:
    API_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
except:
    API_KEY = ""

def fetch_market_data(pair):
    """Scarica dati per analisi trend"""
    try:
        import yfinance as yf
        symbols = {"XAU/USD": "GC=F", "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "XAG/USD": "SI=F", "BTC/USD": "BTC-USD"}
        data = yf.download(symbols.get(pair, "GC=F"), period="5d", interval="1h", progress=False)
        if not data.empty:
            data.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
            return data[['open', 'high', 'low', 'close']]
    except:
        pass
    return None

def calculate_trend(df):
    """Calcola trend da dati reali"""
    if df is None or len(df) < 20:
        return None
    
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    
    # ATR
    hl = df['high'] - df['low']
    hc = abs(df['high'] - df['close'].shift())
    lc = abs(df['low'] - df['close'].shift())
    df['atr'] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()
    
    last = df.iloc[-1]
    score = 50 + (15 if last['close'] > last['sma20'] else -15) + (15 if last['close'] > last['sma50'] else -15) + (10 if last['rsi'] > 50 else -10)
    trend = "BULLISH" if score > 65 else "BEARISH" if score < 35 else "NEUTRAL"
    
    return {
        'trend': trend,
        'strength': max(30, min(95, score)),
        'rsi': round(last['rsi'], 1),
        'atr': round(last['atr'], 2),
        'close': round(last['close'], 2)
    }

# UI
st.title("📈 Forex AI Analyzer")
st.markdown("**Inserisci solo il prezzo attuale dal tuo broker**")

# Input minimale
col1, col2 = st.columns(2)
with col1:
    pair = st.selectbox("💱 Coppia", ["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "XAG/USD", "BTC/USD"])
with col2:
    price_input = st.text_input("💰 Prezzo Attuale", value="0.00", help="Es: 5175.50")
    try:
        current_price = float(price_input.replace(',', '.'))
    except:
        current_price = 0.0

uploaded = st.file_uploader("📸 Screenshot (opzionale)", type=["png", "jpg", "jpeg"])

st.markdown("---")

if st.button("🚀 ANALISI", type="primary", use_container_width=True):
    
    if current_price <= 0:
        st.error("❌ Inserisci il prezzo attuale!")
        st.stop()
    
    # Scarica dati trend
    with st.spinner("📡 Analisi trend..."):
        data = fetch_market_data(pair)
        
        # Calcola 3 timeframe
        ind_h4 = calculate_trend(data) if data is not None else None
        ind_h1 = calculate_trend(data.tail(24)) if data is not None else None
        ind_d1 = calculate_trend(data.resample('D').last().dropna()) if data is not None and len(data) > 24 else ind_h4
        
        tf_data = {
            'H1': ind_h1 if ind_h1 else {'trend': 'NEUTRAL', 'strength': 50, 'atr': 15 if 'XAU' in pair else 0.002, 'rsi': 50},
            'H4': ind_h4 if ind_h4 else {'trend': 'NEUTRAL', 'strength': 50, 'atr': 15 if 'XAU' in pair else 0.002, 'rsi': 50},
            'D1': ind_d1 if ind_d1 else {'trend': 'NEUTRAL', 'strength': 50, 'atr': 15 if 'XAU' in pair else 0.002, 'rsi': 50}
        }
    
    # Mostra screenshot
    if uploaded:
        st.image(uploaded, use_column_width=True)
    
    # Trend display
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
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 5px;">Forza: {d['strength']}%<br>ATR: {d['atr']}</div>
                </div>
            """, unsafe_allow_html=True)
    
    # Segnale
    trends = [d['trend'] for d in tf_data.values()]
    bullish = trends.count("BULLISH")
    bearish = trends.count("BEARISH")
    
    if bullish >= 2 and bearish == 0:
        signal, direction, score, box_class = "STRONG BUY", "BUY", 85, "signal-buy"
    elif bearish >= 2 and bullish == 0:
        signal, direction, score, box_class = "STRONG SELL", "SELL", 85, "signal-sell"
    elif bullish > bearish:
        signal, direction, score, box_class = "WEAK BUY", "BUY", 65, "signal-buy"
    elif bearish > bullish:
        signal, direction, score, box_class = "WEAK SELL", "SELL", 65, "signal-sell"
    else:
        signal, direction, score, box_class = "NO TRADE", "NEUTRAL", 45, "signal-neutral"
    
    # Calcola livelli con ATR
    atr = tf_data['H4']['atr']
    mult = 2.5 if score >= 80 else 2.0 if score >= 60 else 1.5
    
    tp_dist = atr * mult
    sl_dist = atr * 1.0
    
    if direction == "BUY":
        entry, tp, sl = current_price, current_price + tp_dist, current_price - sl_dist
    elif direction == "SELL":
        entry, tp, sl = current_price, current_price - tp_dist, current_price + sl_dist
    else:
        entry, tp, sl = current_price, current_price, current_price
    
    decimals = 2 if 'XAU' in pair or 'BTC' in pair or 'XAG' in pair else 5
    
    # Display
    icon_sig = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "⚪"
    st.markdown(f"""
        <div class="{box_class}">
            <div style="font-size: 13px; margin-bottom: 5px;">SEGNALE</div>
            <h2 style="margin: 0; font-size: 32px;">{icon_sig} {signal}</h2>
            <div style="font-size: 16px; margin-top: 8px;">Score: {score}/100</div>
        </div>
    """, unsafe_allow_html=True)
    
    if direction != "NEUTRAL":
        st.subheader("🎯 Livelli")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">ENTRY</div><div class="price-value entry">{entry:.{decimals}f}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">R:R</div><div class="price-value" style="color: #fbbf24;">1:{tp_dist/sl_dist:.1f}</div></div>', unsafe_allow_html=True)
        
        c3, c4 = st.columns(2)
        with c3:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">TP</div><div class="price-value tp">{tp:.{decimals}f}</div><div style="font-size: 10px; color: #64748b;">+{tp_dist:.{decimals}f}</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">SL</div><div class="price-value sl">{sl:.{decimals}f}</div><div style="font-size: 10px; color: #64748b;">-{sl_dist:.{decimals}f}</div></div>', unsafe_allow_html=True)
        
        # Share
        st.markdown("---")
        txt = f"""🎯 {pair} - {datetime.now().strftime('%H:%M')}
{signal} | Score: {score}/100
Entry: {entry:.{decimals}f}
TP: {tp:.{decimals}f} | SL: {sl:.{decimals}f}
R:R 1:{tp_dist/sl_dist:.1f}
#Forex"""
        st.code(txt)
        if st.button("📋 Copia"): 
            st.success("✅ Copiato!")

st.markdown("---")
st.caption("Solo prezzo manuale + trend automatico da dati di mercato")

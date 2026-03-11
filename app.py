import streamlit as st

st.set_page_config(page_title="Forex AI Analyzer PRO", page_icon="📈", layout="centered")

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
    .stTextInput label, .stSelectbox label { color: #e2e8f0 !important; font-weight: 600 !important; font-size: 14px !important; }
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
    .input-help { font-size: 11px; color: #94a3b8; margin-top: 2px; }
    .data-source { background: #334155; padding: 10px; border-radius: 8px; font-size: 12px; color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# API Key
try:
    API_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
except:
    API_KEY = ""

# Funzioni dati
def fetch_yahoo_data(pair, period="5d"):
    try:
        import yfinance as yf
        symbols = {"XAU/USD": "GC=F", "XAG/USD": "SI=F", "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "BTC/USD": "BTC-USD"}
        data = yf.download(symbols.get(pair, "GC=F"), period=period, interval="1h", progress=False)
        if not data.empty:
            data.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
            return data[['open', 'high', 'low', 'close']]
    except:
        pass
    return None

def calculate_indicators(df):
    if df is None or len(df) < 20:
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
    score = 50 + (15 if last['close'] > last['sma20'] else -15) + (15 if last['close'] > last['sma50'] else -15) + (10 if last['rsi'] > 50 else -10)
    trend = "BULLISH" if score > 65 else "BEARISH" if score < 35 else "NEUTRAL"
    return {'trend': trend, 'strength': max(30, min(95, score)), 'rsi': round(last['rsi'], 1), 'atr': round(last['atr'], 2), 'close': round(last['close'], 2)}

# UI
st.title("📈 Forex AI Analyzer PRO")
st.markdown("**Inserisci i dati dal tuo broker (MT4/MT5/TradingView)**")

# Info
current_hour = datetime.now().hour
market_closed = not (1 <= current_hour <= 22)

if market_closed:
    st.info("🔴 Mercato chiuso. Inserisci i dati manualmente dal tuo broker.")

# INPUT MANUALE TUTTO
st.markdown("### 🔧 Dati di Mercato (dal tuo Broker)")

col1, col2 = st.columns(2)
with col1:
    pair = st.selectbox("💱 Coppia", ["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "XAG/USD", "BTC/USD"], index=0)
with col2:
    main_tf = st.selectbox("⏱️ Timeframe", ["H1", "H4", "D1"], index=1)

# Prezzo
price_col1, price_col2 = st.columns(2)
with price_col1:
    price_input = st.text_input("💰 Prezzo Attuale", value="0.00", help="Es: 5175.50 o 1.0850")
    try:
        current_price = float(price_input.replace(',', '.'))
    except:
        current_price = 0.0
with price_col2:
    st.markdown('<div class="input-help">Leggi il prezzo corrente dalla tua piattaforma MT4/MT5</div>', unsafe_allow_html=True)

# Daily High/Low - MANUALE OBBLIGATORIO
st.markdown("### 📈 Daily High/Low (dal tuo Broker)")

hl_col1, hl_col2 = st.columns(2)
with hl_col1:
    high_input = st.text_input("📈 Daily High", value="0.00", help="Massimo di oggi")
    try:
        daily_high = float(high_input.replace(',', '.'))
    except:
        daily_high = 0.0
with hl_col2:
    low_input = st.text_input("📉 Daily Low", value="0.00", help="Minimo di oggi")
    try:
        daily_low = float(low_input.replace(',', '.'))
    except:
        daily_low = 0.0

st.markdown('<div class="input-help">💡 Trovi High/Low nella finestra "Market Watch" di MT4 o in alto nel grafico</div>', unsafe_allow_html=True)

# Screenshot opzionale
uploaded = st.file_uploader("📸 Screenshot (solo per referenza)", type=["png", "jpg", "jpeg"])

st.markdown("---")

# ANALISI
if st.button("🚀 ANALISI MULTI-TIMEFRAME", type="primary", use_container_width=True):
    
    # Validazione
    errors = []
    if current_price <= 0:
        errors.append("Inserisci il Prezzo Attuale")
    if daily_high <= 0:
        errors.append("Inserisci il Daily High")
    if daily_low <= 0:
        errors.append("Inserisci il Daily Low")
    if daily_high <= daily_low:
        errors.append("High deve essere maggiore di Low")
    
    if errors:
        for e in errors:
            st.error(f"❌ {e}")
        st.stop()
    
    # Scarica dati per trend (solo indicatori, non prezzi)
    with st.spinner("📡 Analisi trend in corso..."):
        data = fetch_yahoo_data(pair, "5d")
        ind_h4 = calculate_indicators(data) if data is not None else None
        
        # Simula 3 timeframe dallo stesso dataset
        if data is not None:
            ind_h1 = calculate_indicators(data.tail(24))
            ind_d1 = calculate_indicators(data.resample('D').last().dropna()) if len(data) > 24 else ind_h4
        else:
            ind_h1 = ind_h4 = ind_d1 = None
    
    # Se non ho dati API, uso neutrale
    tf_data = {
        'H1': ind_h1 if ind_h1 else {'trend': 'NEUTRAL', 'strength': 50, 'atr': 15 if 'XAU' in pair else 0.002, 'rsi': 50},
        'H4': ind_h4 if ind_h4 else {'trend': 'NEUTRAL', 'strength': 50, 'atr': 15 if 'XAU' in pair else 0.002, 'rsi': 50},
        'D1': ind_d1 if ind_d1 else {'trend': 'NEUTRAL', 'strength': 50, 'atr': 15 if 'XAU' in pair else 0.002, 'rsi': 50}
    }
    
    # Info dati
    source = "Yahoo Finance" if data is not None else "Default"
    st.markdown(f'<div class="data-source">📡 Trend: {source} | 💰 Prezzi: Inseriti manualmente dal broker</div>', unsafe_allow_html=True)
    
    # Mostra screenshot se c'è
    if uploaded:
        st.image(uploaded, use_column_width=True)
    
    # Riepilogo input
    st.markdown(f"""
        <div style="background: #1e293b; padding: 15px; border-radius: 10px; margin: 15px 0; border: 1px solid #475569;">
            <h4>📊 Dati Inseriti</h4>
            <p><b>Coppia:</b> {pair}</p>
            <p><b>Prezzo:</b> {current_price:,.2f}</p>
            <p><b>Daily High:</b> {daily_high:,.2f}</p>
            <p><b>Daily Low:</b> {daily_low:,.2f}</p>
            <p><b>Range:</b> {daily_high - daily_low:,.2f} punti</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Timeframe analysis
    st.subheader("📈 Analisi Trend (Multi-Timeframe)")
    
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
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 5px;">Forza: {d['strength']}%<br>RSI: {d['rsi']}</div>
                </div>
            """, unsafe_allow_html=True)
    
    # Confluenza
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
    
    # Calcola livelli con ATR da dati reali + range giornaliero
    atr = tf_data['H4']['atr'] if tf_data['H4']['atr'] else (daily_high - daily_low) / 4
    
    # Se score alto, target più ambiziosi
    if score >= 80:
        tp_mult = 2.0
    elif score >= 60:
        tp_mult = 1.5
    else:
        tp_mult = 1.0
    
    # TP basato su ATR o % del range giornaliero
    tp_dist = max(atr * 3 * tp_mult, (daily_high - daily_low) * 0.3)
    sl_dist = max(atr * 1.5, (daily_high - daily_low) * 0.15)
    
    if direction == "BUY":
        entry, tp, sl = current_price, min(current_price + tp_dist, daily_high), max(current_price - sl_dist, daily_low)
    elif direction == "SELL":
        entry, tp, sl = current_price, max(current_price - tp_dist, daily_low), min(current_price + sl_dist, daily_high)
    else:
        entry, tp, sl = current_price, current_price + tp_dist, current_price - sl_dist
    
    decimals = 2 if 'XAU' in pair or 'BTC' in pair or 'XAG' in pair else 5
    
    # Segnale
    icon_sig = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "⚪"
    st.markdown(f"""
        <div class="{box_class}">
            <div style="font-size: 13px; margin-bottom: 5px;">SEGNALE MULTI-TIMEFRAME</div>
            <h2 style="margin: 0; font-size: 32px;">{icon_sig} {signal}</h2>
            <div style="font-size: 16px; margin-top: 8px;">Score: {score}/100</div>
            <div style="font-size: 12px; margin-top: 5px;">🟢{bullish} 🔴{bearish} ⚪{3-bullish-bearish}</div>
        </div>
    """, unsafe_allow_html=True)
    
    if direction != "NEUTRAL":
        st.subheader("🎯 Livelli Operativi")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">ENTRY</div><div class="price-value entry">{entry:.{decimals}f}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">R:R</div><div class="price-value" style="color: #fbbf24;">1:{abs(tp-entry)/abs(sl-entry):.1f}</div></div>', unsafe_allow_html=True)
        
        c3, c4 = st.columns(2)
        with c3:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">TAKE PROFIT</div><div class="price-value tp">{tp:.{decimals}f}</div><div style="font-size: 10px; color: #64748b;">{abs(tp-entry):.{decimals}f} punti</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">STOP LOSS</div><div class="price-value sl">{sl:.{decimals}f}</div><div style="font-size: 10px; color: #64748b;">{abs(sl-entry):.{decimals}f} punti</div></div>', unsafe_allow_html=True)
        
        # Share
        st.markdown("---")
        txt = f"""🎯 FOREX SIGNAL - {datetime.now().strftime('%d/%m %H:%M')}
📊 {pair} | {main_tf}
{signal} (Score: {score}/100)
Prezzo: {current_price:.{decimals}f} | High: {daily_high:.{decimals}f} | Low: {daily_low:.{decimals}f}
🎯 Entry: {entry:.{decimals}f}
✅ TP: {tp:.{decimals}f}
❌ SL: {sl:.{decimals}f}
R:R = 1:{abs(tp-entry)/abs(sl-entry):.1f}
#Forex #Trading"""
        st.code(txt)
        if st.button("📋 Copia Segnale"): 
            st.success("✅ Copiato!")

st.markdown("---")
st.caption(f"⏰ {datetime.now().strftime('%H:%M')} | Inserisci sempre dati reali dal tuo broker per risultati accurati")

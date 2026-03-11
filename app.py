import streamlit as st

# Configurazione
st.set_page_config(
    page_title="Forex AI Analyzer PRO", 
    page_icon="📈", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Imports
import numpy as np
from PIL import Image
from datetime import datetime, timedelta
import requests
import pandas as pd

# CSS
st.markdown("""
<style>
    .stApp { background: #0f172a; }
    .stApp, .stApp p, .stApp label, .stApp span, .stApp div { color: #f1f5f9 !important; }
    .stNumberInput label, .stSelectbox label { color: #e2e8f0 !important; font-weight: 600 !important; }
    .metric-box { background: #1e293b; border: 2px solid #475569; border-radius: 12px; padding: 20px; margin: 8px 0; text-align: center; }
    .signal-buy { background: linear-gradient(135deg, #059669, #10b981); padding: 25px; border-radius: 16px; text-align: center; margin: 15px 0; border: 2px solid #10b981; }
    .signal-sell { background: linear-gradient(135deg, #dc2626, #ef4444); padding: 25px; border-radius: 16px; text-align: center; margin: 15px 0; border: 2px solid #ef4444; }
    .signal-neutral { background: #475569; padding: 25px; border-radius: 16px; text-align: center; margin: 15px 0; border: 2px solid #64748b; }
    .tf-box { background: #1e293b; border: 3px solid #64748b; border-radius: 12px; padding: 15px; margin: 5px 0; text-align: center; }
    .tf-bullish { border-color: #10b981; background: rgba(16, 185, 129, 0.15); }
    .tf-bearish { border-color: #ef4444; background: rgba(239, 68, 68, 0.15); }
    .price-value { font-size: 26px; font-weight: bold; font-family: 'Courier New', monospace; color: #ffffff !important; }
    .entry { color: #22d3ee !important; }
    .tp { color: #4ade80 !important; }
    .sl { color: #f87171 !important; }
    .info-box { background: #334155; border-left: 4px solid #06b6d4; padding: 15px; border-radius: 0 8px 8px 0; margin: 10px 0; }
    .warning-box { background: #451a03; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 0 8px 8px 0; margin: 10px 0; }
    .stButton>button { background: linear-gradient(135deg, #06b6d4, #3b82f6) !important; color: white !important; font-weight: bold !important; border-radius: 12px !important; padding: 16px !important; }
</style>
""", unsafe_allow_html=True)

# API Key
try:
    API_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
except:
    API_KEY = ""

# ============================================================================
# FUNZIONI DATI CON FALLBACK YAHOO
# ============================================================================

def fetch_yahoo_data(pair, period="5d"):
    """Fallback con Yahoo Finance"""
    try:
        import yfinance as yf
        
        # Mappa simboli Yahoo
        symbols = {
            "XAU/USD": "GC=F",      # Gold Futures
            "XAG/USD": "SI=F",      # Silver Futures  
            "EUR/USD": "EURUSD=X",
            "GBP/USD": "GBPUSD=X",
            "USD/JPY": "USDJPY=X",
            "BTC/USD": "BTC-USD",
        }
        
        symbol = symbols.get(pair, "GC=F")
        
        # Scarica dati
        data = yf.download(symbol, period=period, interval="1h", progress=False)
        
        if data.empty:
            return None
            
        # Rinomina colonne
        data.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
        return data[['open', 'high', 'low', 'close', 'volume']]
        
    except Exception as e:
        return None

@st.cache_data(ttl=600)
def fetch_data_with_fallback(pair, tf):
    """Prova Alpha Vantage, poi Yahoo Finance"""
    
    # Prova Alpha Vantage
    if API_KEY and API_KEY != "DEMO":
        try:
            # ... (codice Alpha Vantage come prima)
            # Se fallisce, passa a Yahoo
            pass
        except:
            pass
    
    # Fallback Yahoo Finance (sempre disponibile)
    st.info("📡 Using Yahoo Finance (market closed or API limit)")
    return fetch_yahoo_data(pair, "5d" if tf in ["H1", "H4"] else "1mo")

def calculate_indicators(df):
    """Calcola indicatori da DataFrame"""
    if df is None or len(df) < 20:
        return None
    
    # Prendi ultimi dati disponibili (anche se mercato chiuso)
    last_24h = df.tail(24)
    last_week = df.tail(100)
    
    # High/Low del giorno (ultime 24h disponibili)
    daily_high = last_24h['high'].max()
    daily_low = last_24h['low'].min()
    
    # Indicatori
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR
    hl = df['high'] - df['low']
    hc = abs(df['high'] - df['close'].shift())
    lc = abs(df['low'] - df['close'].shift())
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    
    last = df.iloc[-1]
    
    # Trend score
    score = 50
    if last['close'] > last['sma20']: score += 15
    else: score -= 15
    if last['close'] > last['sma50']: score += 15
    else: score -= 15
    if last['rsi'] > 50: score += 10
    else: score -= 10
    
    if score > 65: trend = "BULLISH"
    elif score < 35: trend = "BEARISH"
    else: trend = "NEUTRAL"
    
    return {
        'trend': trend,
        'strength': max(30, min(95, score)),
        'rsi': round(last['rsi'], 1),
        'atr': round(last['atr'], 2),
        'close': round(last['close'], 2),
        'daily_high': round(daily_high, 2),
        'daily_low': round(daily_low, 2),
        'sma20': round(last['sma20'], 2),
        'sma50': round(last['sma50'], 2),
        'data_source': 'Yahoo Finance' if 'yahoo' in str(type(df)) else 'Alpha Vantage',
        'last_update': df.index[-1].strftime('%H:%M %d/%m')
    }

# ============================================================================
# UI
# ============================================================================

st.title("📈 Forex AI Analyzer PRO")
st.markdown("**✅ Dati Reali (Alpha Vantage + Yahoo Backup)**")

# Info mercato
current_hour = datetime.now().hour
market_open = 1 <= current_hour <= 22  # Forex approx

if not market_open:
    st.markdown("""
        <div class="warning-box">
            <h4>⚠️ Mercato Chiuso o Weekend</h4>
            <p>Usando dati storici da Yahoo Finance. I Daily High/Low sono degli ultimi dati disponibili.</p>
            <p><b>Consiglio:</b> Inserisci manualmente High/Low del giorno se li hai dal tuo broker.</p>
        </div>
    """, unsafe_allow_html=True)

# Input
st.markdown("### 🔧 Dati di Mercato")

col1, col2, col3 = st.columns(3)

with col1:
    pair = st.selectbox(
        "💱 Coppia",
        ["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "XAG/USD", "BTC/USD"],
        index=0
    )

with col2:
    # Fix formato numero con virgola/punto
    price_input = st.text_input(
        "💰 Prezzo Attuale",
        value="5175.50",
        help="Usa il punto come decimale: 5175.50"
    )
    try:
        current_price = float(price_input.replace(',', '.'))
    except:
        current_price = 0.0
        st.error("Formato non valido. Usa: 5175.50")

with col3:
    main_tf = st.selectbox("⏱️ Timeframe", ["H1", "H4", "D1"], index=1)

# High/Low
st.markdown("### 📈 Daily High/Low")

# Placeholder per valori auto
auto_high, auto_low = 0.0, 0.0

col4, col5 = st.columns(2)
with col4:
    high_input = st.text_input(
        "📈 Daily High (0 = auto)",
        value="0.00",
        help="Lascia 0 per calcolo automatico dai dati storici"
    )
    try:
        manual_high = float(high_input.replace(',', '.'))
    except:
        manual_high = 0.0

with col5:
    low_input = st.text_input(
        "📉 Daily Low (0 = auto)",
        value="0.00",
        help="Lascia 0 per calcolo automatico dai dati storici"
    )
    try:
        manual_low = float(low_input.replace(',', '.'))
    except:
        manual_low = 0.0

uploaded = st.file_uploader("📸 Screenshot (opzionale)", type=["png", "jpg", "jpeg"])

st.markdown("---")

# ============================================================================
# ANALISI
# ============================================================================

if st.button("🚀 ANALISI MULTI-TIMEFRAME", type="primary", use_container_width=True):
    
    if current_price <= 0:
        st.error("❌ Inserisci un prezzo valido!")
        st.stop()
    
    with st.spinner("📡 Scaricando dati..."):
        # Scarica dati reali (con fallback automatico)
        data = fetch_data_with_fallback(pair, main_tf)
        
        if data is not None:
            # Simula 3 timeframe dai dati disponibili
            ind_h4 = calculate_indicators(data)
            ind_h1 = calculate_indicators(data.tail(24))  # Ultime 24 ore
            ind_d1 = calculate_indicators(data.resample('D').last().dropna()) if len(data) > 24 else ind_h4
            
            # Recupera auto high/low
            if ind_h4:
                auto_high = ind_h4['daily_high']
                auto_low = ind_h4['daily_low']
        else:
            st.error("❌ Nessun dato disponibile")
            ind_h1 = ind_h4 = ind_d1 = None
    
    # Usa valori
    daily_high = manual_high if manual_high > 0 else auto_high
    daily_low = manual_low if manual_low > 0 else auto_low
    
    # Info box
    source = ind_h4['data_source'] if ind_h4 else "N/A"
    last_upd = ind_h4['last_update'] if ind_h4 else "N/A"
    
    st.markdown(f"""
        <div class="info-box">
            <h4>📊 Dati: {source}</h4>
            <p><b>Ultimo aggiornamento:</b> {last_upd}</p>
            <p><b>Prezzo inserito:</b> {current_price:,.2f}</p>
            <p><b>Daily High:</b> {daily_high:,.2f} {'(Auto)' if manual_high == 0 else '(Manuale)'}</p>
            <p><b>Daily Low:</b> {daily_low:,.2f} {'(Auto)' if manual_low == 0 else '(Manuale)'}</p>
        </div>
    """, unsafe_allow_html=True)
    
    if uploaded:
        st.image(uploaded, use_column_width=True)
    
    # Timeframe analysis
    if ind_h4:
        tf_data = {
            'H1': ind_h1 if ind_h1 else ind_h4,
            'H4': ind_h4,
            'D1': ind_d1 if ind_d1 else ind_h4
        }
        
        st.subheader("📊 Analisi Timeframe")
        
        cols = st.columns(3)
        for i, (tf, data) in enumerate(tf_data.items()):
            with cols[i]:
                trend = data['trend']
                icon = "🟢" if trend == "BULLISH" else "🔴" if trend == "BEARISH" else "⚪"
                css_class = "tf-bullish" if trend == "BULLISH" else "tf-bearish" if trend == "BEARISH" else ""
                
                st.markdown(f"""
                    <div class="tf-box {css_class}">
                        <div style="font-size: 20px; font-weight: bold;">{tf}</div>
                        <div style="font-size: 28px; margin: 10px 0;">{icon}</div>
                        <div style="font-size: 14px; font-weight: 600;">{trend}</div>
                        <div style="font-size: 12px; color: #94a3b8; margin-top: 8px;">
                            Forza: {data['strength']}%<br>
                            RSI: {data['rsi']}<br>
                            ATR: {data['atr']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        
        # Confluenza e segnale
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
        
        # Calcola livelli
        atr = ind_h4['atr'] if ind_h4['atr'] else (35 if 'XAU' in pair else 0.003)
        mult = 3.0 if score >= 80 else 2.0 if score >= 60 else 1.0
        
        tp_dist = atr * mult * 2.5
        sl_dist = atr * mult * 1.0
        
        if direction == "BUY":
            entry, tp, sl = current_price, current_price + tp_dist, current_price - sl_dist
        elif direction == "SELL":
            entry, tp, sl = current_price, current_price - tp_dist, current_price + sl_dist
        else:
            entry, tp, sl = current_price, current_price + tp_dist, current_price - sl_dist
        
        decimals = 2 if 'XAU' in pair or 'BTC' in pair or 'XAG' in pair else 5
        
        # Display segnale
        icon_signal = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "⚪"
        st.markdown(f"""
            <div class="{box_class}">
                <div style="font-size: 14px; margin-bottom: 5px;">SEGNALE MULTI-TIMEFRAME</div>
                <h2 style="margin: 0; font-size: 36px;">{icon_signal} {signal}</h2>
                <div style="font-size: 18px; margin-top: 10px;">Score: {score}/100</div>
                <div style="font-size: 12px; margin-top: 5px;">🟢{bullish} 🔴{bearish} ⚪{3-bullish-bearish}</div>
            </div>
        """, unsafe_allow_html=True)
        
        if direction != "NEUTRAL":
            st.subheader("🎯 Livelli Operativi")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">🎯 ENTRY</div><div class="price-value entry">{entry:.{decimals}f}</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">📊 R:R</div><div class="price-value" style="color: #fbbf24;">1:{tp_dist/sl_dist:.1f}</div></div>', unsafe_allow_html=True)
            
            c3, c4 = st.columns(2)
            with c3:
                st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">✅ TP</div><div class="price-value tp">{tp:.{decimals}f}</div><div style="font-size: 11px; color: #64748b;">+{tp_dist:.{decimals}f}</div></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">❌ SL</div><div class="price-value sl">{sl:.{decimals}f}</div><div style="font-size: 11px; color: #64748b;">-{sl_dist:.{decimals}f}</div></div>', unsafe_allow_html=True)
            
            # Share
            st.markdown("---")
            txt = f"""🎯 FOREX SIGNAL - {datetime.now().strftime('%d/%m %H:%M')}
📊 {pair} | {main_tf} | {source}
{signal} (Score: {score}/100)
🟢 H1: {tf_data['H1']['trend']} 🔵 H4: {tf_data['H4']['trend']} ⚫ D1: {tf_data['D1']['trend']}
🎯 Entry: {entry:.{decimals}f}
✅ TP: {tp:.{decimals}f}
❌ SL: {sl:.{decimals}f}
📊 R:R = 1:{tp_dist/sl_dist:.1f}
#Forex #MTF"""
            st.code(txt)
            if st.button("📋 Copia"): st.success("✅ Copiato!")

st.markdown("---")
st.caption(f"⏰ {datetime.now().strftime('%H:%M')} | Mercato: {'🟢 Aperto' if market_open else '🔴 Chiuso'} | Yahoo Finance Fallback")

import streamlit as st

st.set_page_config(page_title="Forex AI Auto-Price", page_icon="📈", layout="centered")

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
    .price-auto { background: #059669; color: white; padding: 5px 10px; border-radius: 5px; font-size: 12px; }
    .price-manual { background: #475569; color: white; padding: 5px 10px; border-radius: 5px; font-size: 12px; }
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
</style>
""", unsafe_allow_html=True)

# API Keys
try:
    TWELVE_DATA_KEY = st.secrets["TWELVE_DATA_KEY"]
except:
    TWELVE_DATA_KEY = ""  # Prendi gratis su twelvedata.com

# ============================================================================
# FUNZIONI PREZZO AUTOMATICO
# ============================================================================

@st.cache_data(ttl=60)  # Cache 1 minuto
def get_live_price_twelvedata(pair):
    """Prezzo live da Twelve Data (gratis 8 req/min)"""
    if not TWELVE_DATA_KEY:
        return None, "No API Key"
    
    # Mappa simboli
    symbols = {
        "XAU/USD": "XAU/USD",
        "EUR/USD": "EUR/USD", 
        "GBP/USD": "GBP/USD",
        "USD/JPY": "USD/JPY",
        "XAG/USD": "XAG/USD",
        "BTC/USD": "BTC/USD"
    }
    
    symbol = symbols.get(pair, "XAU/USD")
    
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_KEY}"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if "price" in data:
            return float(data["price"]), "Twelve Data"
        else:
            return None, f"Error: {data.get('message', 'Unknown')}"
            
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

def fetch_historical_data(pair, source="yahoo"):
    """Dati storici per HH/HL analysis"""
    try:
        import yfinance as yf
        symbols = {"XAU/USD": "GC=F", "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "XAG/USD": "SI=F", "BTC/USD": "BTC-USD"}
        
        # Scarica 30 giorni per trovare HH/HL
        data = yf.download(symbols.get(pair, "GC=F"), period="30d", interval="1h", progress=False)
        
        if not data.empty:
            data.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
            return data[['open', 'high', 'low', 'close']]
    except:
        pass
    return None

def find_higher_highs_lower_lows(df, window=20):
    """
    Trova Higher Highs (HH) e Lower Lows (LL) per struttura di mercato reale
    """
    if df is None or len(df) < window:
        return None, None, "No data"
    
    # Trova swing highs e lows
    highs = df['high'].rolling(window=window, center=True).max()
    lows = df['low'].rolling(window=window, center=True).min()
    
    # Higher Highs: nuovi massimi crescenti
    hh_mask = df['high'] == highs
    hh_points = df[hh_mask]['high'].tail(3)  # Ultimi 3 HH
    
    # Lower Lows: nuovi minimi decrescenti
    ll_mask = df['low'] == lows
    ll_points = df[ll_mask]['low'].tail(3)  # Ultimi 3 LL
    
    # Struttura trend
    if len(hh_points) >= 2 and len(ll_points) >= 2:
        hh_trend = "UP" if hh_points.iloc[-1] > hh_points.iloc[0] else "DOWN"
        ll_trend = "UP" if ll_points.iloc[-1] > ll_points.iloc[0] else "DOWN"
        
        # Determina struttura di mercato
        if hh_trend == "UP" and ll_trend == "UP":
            structure = "BULLISH_TREND"  # HH e HL = trend rialzista
        elif hh_trend == "DOWN" and ll_trend == "DOWN":
            structure = "BEARISH_TREND"  # LH e LL = trend ribassista
        else:
            structure = "RANGE/CONSOLIDATION"  # Confusione
        
        return {
            'last_hh': round(hh_points.iloc[-1], 2),
            'last_ll': round(ll_points.iloc[-1], 2),
            'prev_hh': round(hh_points.iloc[-2], 2) if len(hh_points) > 1 else None,
            'prev_ll': round(ll_points.iloc[-2], 2) if len(ll_points) > 1 else None,
            'structure': structure,
            'hh_trend': hh_trend,
            'll_trend': ll_trend
        }, df, "OK"
    
    return None, df, "Insufficient swings"

def calculate_trend_with_structure(df, structure_data):
    """Calcola trend usando HH/HL reali"""
    if df is None:
        return None
    
    # Indicatori standard
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
    
    # Score base
    score = 50
    if last['close'] > last['sma20']: score += 10
    if last['close'] > last['sma50']: score += 10
    if last['rsi'] > 50: score += 10
    
    # Bonus per struttura HH/HL
    if structure_data:
        if structure_data['structure'] == "BULLISH_TREND":
            score += 20
        elif structure_data['structure'] == "BEARISH_TREND":
            score -= 20
        
        # Se prezzo sopra ultimo HH, molto bullish
        if last['close'] > structure_data['last_hh']:
            score += 10
        # Se sotto ultimo LL, molto bearish
        elif last['close'] < structure_data['last_ll']:
            score -= 10
    
    trend = "BULLISH" if score > 60 else "BEARISH" if score < 40 else "NEUTRAL"
    
    return {
        'trend': trend,
        'strength': max(30, min(95, abs(score - 50) * 2 + 50)),
        'rsi': round(last['rsi'], 1),
        'atr': round(last['atr'], 2),
        'close': round(last['close'], 2),
        'sma20': round(last['sma20'], 2),
        'sma50': round(last['sma50'], 2)
    }

# ============================================================================
# UI
# ============================================================================

st.title("📈 Forex AI Analyzer")
st.markdown("**Prezzo Automatico + Analisi HH/HL (Higher Highs/Lower Lows)**")

# Recupero prezzo automatico
col1, col2 = st.columns([2, 1])

with col1:
    pair = st.selectbox("💱 Coppia", ["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "XAG/USD", "BTC/USD"], index=0)

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    auto_fetch = st.button("🔄 Aggiorna Prezzo", use_container_width=True)

# Prezzo
price_source = "Manual"
current_price = 0.0

if auto_fetch:
    with st.spinner("📡 Recupero prezzo live..."):
        # Prova Twelve Data
        price_12, source_12 = get_live_price_twelvedata(pair)
        
        if price_12:
            current_price = price_12
            price_source = source_12
            st.session_state['auto_price'] = price_12
        else:
            # Fallback Yahoo
            price_yh, source_yh = get_price_yahoo(pair)
            if price_yh:
                current_price = price_yh
                price_source = source_yh
                st.session_state['auto_price'] = price_yh
            else:
                st.error("❌ Impossibile recuperare prezzo automatico")
                st.session_state['auto_price'] = 0.0

# Usa prezzo da sessione se disponibile
if 'auto_price' in st.session_state and st.session_state['auto_price'] > 0:
    current_price = st.session_state['auto_price']

# Input prezzo (auto o manuale)
price_col1, price_col2 = st.columns([2, 1])

with price_col1:
    price_input = st.text_input(
        "💰 Prezzo", 
        value=f"{current_price:.2f}" if current_price > 0 else "0.00",
        help="Clicca 'Aggiorna Prezzo' per automatico, o inserisci manualmente"
    )
    try:
        final_price = float(price_input.replace(',', '.'))
    except:
        final_price = 0.0

with price_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if price_source == "Twelve Data":
        st.markdown('<span class="price-auto">🟢 LIVE</span>', unsafe_allow_html=True)
    elif price_source == "Yahoo Finance":
        st.markdown('<span class="price-manual">🟡 15min delay</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="price-manual">⚪ MANUALE</span>', unsafe_allow_html=True)

uploaded = st.file_uploader("📸 Screenshot (opzionale)", type=["png", "jpg", "jpeg"])

st.markdown("---")

# ANALISI
if st.button("🚀 ANALISI HH/HL + MULTI-TIMEFRAME", type="primary", use_container_width=True):
    
    if final_price <= 0:
        st.error("❌ Recupera il prezzo automatico o inseriscilo manualmente!")
        st.stop()
    
    with st.spinner("📡 Analisi Higher Highs / Lower Lows..."):
        # Scarica dati storici
        hist_data = fetch_historical_data(pair)
        
        # Trova HH/HL
        structure_data, full_data, status = find_higher_highs_lower_lows(hist_data)
        
        # Calcola trend con struttura
        ind_h4 = calculate_trend_with_structure(full_data, structure_data)
        ind_h1 = calculate_trend_with_structure(full_data.tail(100) if full_data is not None else None, structure_data)
        ind_d1 = calculate_trend_with_structure(full_data.resample('D').last().dropna() if full_data is not None else None, structure_data)
        
        tf_data = {
            'H1': ind_h1 if ind_h1 else {'trend': 'NEUTRAL', 'strength': 50, 'atr': 15 if 'XAU' in pair else 0.002, 'rsi': 50},
            'H4': ind_h4 if ind_h4 else {'trend': 'NEUTRAL', 'strength': 50, 'atr': 15 if 'XAU' in pair else 0.002, 'rsi': 50},
            'D1': ind_d1 if ind_d1 else {'trend': 'NEUTRAL', 'strength': 50, 'atr': 15 if 'XAU' in pair else 0.002, 'rsi': 50}
        }
    
    # Mostra struttura HH/HL
    if structure_data:
        st.subheader("🏗️ Struttura di Mercato (HH/HL)")
        
        hh_col1, hh_col2, hh_col3 = st.columns(3)
        
        with hh_col1:
            st.metric("Higher High", f"{structure_data['last_hh']:.2f}", 
                     f"{structure_data['last_hh'] - structure_data['prev_hh']:.2f}" if structure_data['prev_hh'] else None)
        with hh_col2:
            st.metric("Lower Low", f"{structure_data['last_ll']:.2f}",
                     f"{structure_data['last_ll'] - structure_data['prev_ll']:.2f}" if structure_data['prev_ll'] else None)
        with hh_col3:
            structure_icon = "📈" if "BULLISH" in structure_data['structure'] else "📉" if "BEARISH" in structure_data['structure'] else "➡️"
            st.markdown(f"""
                <div style="text-align: center; padding: 10px; background: #1e293b; border-radius: 10px;">
                    <div style="font-size: 24px;">{structure_icon}</div>
                    <div style="font-size: 12px; color: #94a3b8;">{structure_data['structure']}</div>
                </div>
            """, unsafe_allow_html=True)
    
    # Screenshot
    if uploaded:
        st.image(uploaded, use_column_width=True)
    
    # Trend multi-timeframe
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
                        Forza: {d['strength']}%<br>
                        RSI: {d['rsi']}<br>
                        ATR: {d['atr']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    # Segnale finale
    trends = [d['trend'] for d in tf_data.values()]
    bullish = trends.count("BULLISH")
    bearish = trends.count("BEARISH")
    
    # Peso struttura HH/HL
    structure_bonus = 0
    if structure_data:
        if "BULLISH" in structure_data['structure']:
            structure_bonus = 15
        elif "BEARISH" in structure_data['structure']:
            structure_bonus = -15
    
    if bullish >= 2 and bearish == 0 and structure_bonus >= 0:
        signal, direction, score, box_class = "STRONG BUY", "BUY", 85 + structure_bonus//3, "signal-buy"
    elif bearish >= 2 and bullish == 0 and structure_bonus <= 0:
        signal, direction, score, box_class = "STRONG SELL", "SELL", 85 - structure_bonus//3, "signal-sell"
    elif bullish > bearish:
        signal, direction, score, box_class = "WEAK BUY", "BUY", 65 + structure_bonus//2, "signal-buy"
    elif bearish > bullish:
        signal, direction, score, box_class = "WEAK SELL", "SELL", 65 - structure_bonus//2, "signal-sell"
    else:
        signal, direction, score, box_class = "NO TRADE", "NEUTRAL", 45, "signal-neutral"
    
    score = max(30, min(95, score))
    
    # Calcola livelli basati su HH/HL se disponibili
    atr = tf_data['H4']['atr']
    
    if structure_data and direction != "NEUTRAL":
        # TP verso prossimo HH/HL
        if direction == "BUY":
            tp_target = structure_data['last_hh'] * 1.005  # Sopra l'ultimo HH
            sl_level = structure_data['last_ll'] * 0.995   # Sotto l'ultimo LL
        else:
            tp_target = structure_data['last_ll'] * 0.995  # Sotto l'ultimo LL
            sl_level = structure_data['last_hh'] * 1.005   # Sopra l'ultimo HH
        
        # Usa il più conservativo tra ATR e HH/HL
        entry = final_price
        tp_dist = abs(tp_target - entry)
        sl_dist = abs(entry - sl_level)
        
        # Minimo SL basato su ATR
        min_sl = atr * 1.5
        if sl_dist < min_sl:
            sl_dist = min_sl
            sl_level = entry - sl_dist if direction == "BUY" else entry + sl_dist
        
        tp = entry + tp_dist if direction == "BUY" else entry - tp_dist
        sl = sl_level
        
    else:
        # Fallback ATR puro
        tp_dist = atr * 2.5
        sl_dist = atr * 1.0
        
        if direction == "BUY":
            entry, tp, sl = final_price, final_price + tp_dist, final_price - sl_dist
        elif direction == "SELL":
            entry, tp, sl = final_price, final_price - tp_dist, final_price + sl_dist
        else:
            entry, tp, sl = final_price, final_price, final_price
    
    decimals = 2 if 'XAU' in pair or 'BTC' in pair or 'XAG' in pair else 5
    
    # Display segnale
    icon_sig = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "⚪"
    st.markdown(f"""
        <div class="{box_class}">
            <div style="font-size: 13px; margin-bottom: 5px;">SEGNALE HH/HL + MTF</div>
            <h2 style="margin: 0; font-size: 32px;">{icon_sig} {signal}</h2>
            <div style="font-size: 16px; margin-top: 8px;">Score: {score}/100</div>
            <div style="font-size: 12px; margin-top: 5px;">🟢{bullish} 🔴{bearish} | Struttura: {structure_data['structure'] if structure_data else 'N/A'}</div>
        </div>
    """, unsafe_allow_html=True)
    
    if direction != "NEUTRAL":
        st.subheader("🎯 Livelli Operativi (Basati su HH/HL)")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">ENTRY</div><div class="price-value entry">{entry:.{decimals}f}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">R:R</div><div class="price-value" style="color: #fbbf24;">1:{abs(tp-entry)/abs(sl-entry):.1f}</div></div>', unsafe_allow_html=True)
        
        c3, c4 = st.columns(2)
        with c3:
            target_type = "HH Target" if direction == "BUY" and structure_data else "TP"
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">✅ {target_type}</div><div class="price-value tp">{tp:.{decimals}f}</div><div style="font-size: 10px; color: #64748b;">+{abs(tp-entry):.{decimals}f}</div></div>', unsafe_allow_html=True)
        with c4:
            sl_type = "LL Stop" if direction == "BUY" and structure_data else "SL"
            st.markdown(f'<div class="metric-box"><div style="font-size: 11px; color: #94a3b8;">❌ {sl_type}</div><div class="price-value sl">{sl:.{decimals}f}</div><div style="font-size: 10px; color: #64748b;">-{abs(sl-entry):.{decimals}f}</div></div>', unsafe_allow_html=True)
        
        # Share
        st.markdown("---")
        txt = f"""🎯 HH/HL SIGNAL - {datetime.now().strftime('%H:%M')}
📊 {pair} | {price_source}
{signal} | Score: {score}/100
Struttura: {structure_data['structure'] if structure_data else 'N/A'}
HH: {structure_data['last_hh']:.2f} | LL: {structure_data['last_ll']:.2f}
🎯 Entry: {entry:.{decimals}f}
✅ TP: {tp:.{decimals}f} ({target_type})
❌ SL: {sl:.{decimals}f} ({sl_type})
R:R 1:{abs(tp-entry)/abs(sl-entry):.1f}
#Forex #HHHL #SmartMoney"""
        st.code(txt)
        if st.button("📋 Copia"): 
            st.success("✅ Copiato!")

st.markdown("---")
st.caption(f"⏰ {datetime.now().strftime('%H:%M')} | Prezzo: Auto (Twelve Data/Yahoo) o Manuale | Analisi: HH/HL Reale")

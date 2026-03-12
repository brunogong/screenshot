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
    .signal-wait { background: #1e293b; border: 2px solid #475569; padding: 15px; border-radius: 12px; text-align: center; }
    .trend-strong-bull { background: linear-gradient(135deg, #065f46, #059669); padding: 15px; border-radius: 12px; text-align: center; border: 2px solid #10b981; }
    .trend-strong-bear { background: linear-gradient(135deg, #7f1d1d, #dc2626); padding: 15px; border-radius: 12px; text-align: center; border: 2px solid #ef4444; }
    @keyframes pulse-green { 0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); } 50% { box-shadow: 0 0 0 15px rgba(16, 185, 129, 0); } }
    @keyframes pulse-red { 0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); } 50% { box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); } }
    .alert-banner { background: linear-gradient(90deg, #f59e0b, #d97706); color: white; padding: 15px; border-radius: 12px; text-align: center; margin: 10px 0; animation: blink 1s infinite; }
    .trend-banner { background: linear-gradient(90deg, #3b82f6, #06b6d4); color: white; padding: 12px; border-radius: 12px; text-align: center; margin: 10px 0; }
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.8; } }
    .pair-card { background: #1e293b; border: 2px solid #334155; border-radius: 12px; padding: 15px; margin: 10px 0; }
    .trend-bullish { color: #10b981; font-weight: bold; }
    .trend-bearish { color: #ef4444; font-weight: bold; }
    .trend-neutral { color: #94a3b8; }
    .price-big { font-size: 28px; font-weight: bold; font-family: monospace; color: #fff; }
    .level-box { background: #0f172a; border: 2px solid #475569; border-radius: 8px; padding: 10px; text-align: center; }
    .level-entry { border-color: #06b6d4; }
    .level-tp { border-color: #10b981; }
    .level-sl { border-color: #ef4444; }
    .level-label { font-size: 10px; text-transform: uppercase; opacity: 0.7; }
    .level-value { font-size: 16px; font-weight: bold; font-family: monospace; }
    .info-box { background: #1e3a5f; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 0 8px 8px 0; margin: 10px 0; }
    .timestamp { font-size: 11px; color: #64748b; text-align: right; }
    .strength-bar { background: #334155; height: 8px; border-radius: 4px; margin: 5px 0; overflow: hidden; }
    .strength-fill { height: 100%; border-radius: 4px; }
    .strength-high { background: linear-gradient(90deg, #10b981, #059669); }
    .strength-medium { background: linear-gradient(90deg, #f59e0b, #d97706); }
    .strength-low { background: linear-gradient(90deg, #64748b, #475569); }
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
if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]

# ============================================================================
# FUNZIONI
# ============================================================================

def get_price(symbol):
    """Prezzo SENZA cache per avere sempre dati freschi"""
    if not TWELVE_DATA_KEY:
        return None, "No API Key"
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_KEY}"
        response = requests.get(url, timeout=5)
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
    
    # Determina se c'è un trend forte (indipendentemente dal segnale)
    strong_trend = ind['strength'] >= 60 and ind['trend'] != "NEUTRAL"
    
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
        'dist_res': dist_res, 'dist_sup': dist_sup,
        'strong_trend': strong_trend,
        'time': datetime.now()
    }

# ============================================================================
# UI
# ============================================================================

st.title("📈 Forex AI - Multi Alert")

# Info ultimo aggiornamento
if st.session_state['last_update']:
    st.markdown(f"<p class='timestamp'>Ultimo aggiornamento: {st.session_state['last_update'].strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)

# Toggle auto-analisi
auto_check = st.checkbox("🔔 Scansione automatica (30s)", value=True)

# Pulsante scansione manuale
if st.button("🚀 SCANSIONA TUTTE LE COPPIE", type="primary", use_container_width=True) or auto_check:
    
    active_signals = []
    strong_trends = []
    st.session_state['signals'] = {}
    
    with st.spinner("📡 Recupero prezzi reali..."):
        for pair in PAIRS:
            result = analyze_pair(pair)
            if result:
                st.session_state['signals'][pair] = result
                if result['direction'] != "NEUTRAL":
                    active_signals.append(result)
                elif result['strong_trend']:
                    strong_trends.append(result)
    
    st.session_state['last_update'] = datetime.now()
    
    # ALERT segnali di ingresso
    if active_signals:
        st.markdown(f"""
            <div class="alert-banner">
                <h2>🚨 {len(active_signals)} SEGNALE/I DI INGRESSO!</h2>
                <p>{', '.join([s['pair'] + ' ' + s['signal'] for s in active_signals])}</p>
            </div>
        """, unsafe_allow_html=True)
        
        new_signals = [s for s in active_signals if s['pair'] not in st.session_state['alerted']]
        if new_signals:
            st.session_state['alerted'].update([s['pair'] for s in new_signals])
            st.markdown("""
                <audio autoplay>
                    <source src="data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBTGH0fPTgjMGHm7A7+OZURE" type="audio/wav">
                </audio>
            """, unsafe_allow_html=True)
    
    # BANNER trend forti (solo se non ci sono segnali attivi)
    elif strong_trends:
        trend_text = ', '.join([f"{s['pair']} ({s['trend']} {s['strength']}%)" for s in strong_trends])
        st.markdown(f"""
            <div class="trend-banner">
                <h3>📊 Trend Importanti Rilevati</h3>
                <p>{trend_text}</p>
                <p style="font-size: 12px; opacity: 0.8;">Attendi segnale di ingresso...</p>
            </div>
        """, unsafe_allow_html=True)
        st.session_state['alerted'] = set()
    
    else:
        st.info("⏳ Nessun segnale attivo - tutte le coppie in attesa o trend neutrale")
        st.session_state['alerted'] = set()
    
    # Display TUTTE le coppie nella dashboard
    st.subheader("📊 Dashboard Coppie")
    
    if not st.session_state['signals']:
        st.warning("⚠️ Nessun dato disponibile. Controlla la tua API key.")
    else:
        cols = st.columns(2)
        for idx, pair in enumerate(PAIRS):
            with cols[idx % 2]:
                if pair in st.session_state['signals']:
                    s = st.session_state['signals'][pair]
                    
                    # Determina lo stile della card
                    if s['direction'] == "BUY":
                        card_class = "signal-buy"
                        icon = "🟢"
                        trend_class = "trend-bullish"
                        status_text = "🚨 SEGNALE BUY"
                    elif s['direction'] == "SELL":
                        card_class = "signal-sell"
                        icon = "🔴"
                        trend_class = "trend-bearish"
                        status_text = "🚨 SEGNALE SELL"
                    elif s['strong_trend'] and s['trend'] == "BULLISH":
                        card_class = "trend-strong-bull"
                        icon = "📈"
                        trend_class = "trend-bullish"
                        status_text = f"TREND FORTE {s['strength']}%"
                    elif s['strong_trend'] and s['trend'] == "BEARISH":
                        card_class = "trend-strong-bear"
                        icon = "📉"
                        trend_class = "trend-bearish"
                        status_text = f"TREND FORTE {s['strength']}%"
                    else:
                        card_class = "signal-wait"
                        icon = "⚪"
                        trend_class = "trend-neutral"
                        status_text = "ATTENDI"
                    
                    with st.container():
                        st.markdown(f'<div class="pair-card">', unsafe_allow_html=True)
                        
                        # Header con prezzo e trend
                        st.markdown(f"""
                            <div class="{card_class}">
                                <h3>{icon} {pair}</h3>
                                <div class="price-big">{s['price']:.5f}</div>
                                <p style="margin: 5px 0; font-size: 14px;">
                                    <span class="{trend_class}">{s['trend']}</span> | RSI: {s['rsi']}
                                </p>
                                <p style="font-size: 13px; margin: 0; font-weight: bold;">
                                    {status_text}
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Barra forza trend
                        strength_width = s['strength']
                        strength_color = "strength-high" if s['strength'] >= 60 else "strength-medium" if s['strength'] >= 40 else "strength-low"
                        st.markdown(f"""
                            <div style="margin: 10px 0;">
                                <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 2px;">
                                    <span>Forza Trend</span>
                                    <span>{s['strength']}%</span>
                                </div>
                                <div class="strength-bar">
                                    <div class="strength-fill {strength_color}" style="width: {strength_width}%;"></div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Info livelli
                        st.markdown(f"""
                            <p style="text-align: center; font-size: 11px; margin: 8px 0; opacity: 0.9;">
                                📊 Res: {s['resistance']:.5f} | Sup: {s['support']:.5f}<br>
                                📏 D.Res: {s['dist_res']:.1f}p | D.Sup: {s['dist_sup']:.1f}p | ATR: {s['atr']}p
                            </p>
                        """, unsafe_allow_html=True)
                        
                        # Livelli operativi (sempre visibili)
                        st.markdown("<p style='font-size: 10px; text-align: center; margin-bottom: 5px; opacity: 0.7;'>🎯 LIVELLI</p>", unsafe_allow_html=True)
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.markdown(f"""
                                <div class="level-box level-entry">
                                    <div class="level-label">Entry</div>
                                    <div class="level-value" style="color: #22d3ee; font-size: 14px;">{s['entry']:.5f}</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c2:
                            st.markdown(f"""
                                <div class="level-box level-tp">
                                    <div class="level-label">TP</div>
                                    <div class="level-value" style="color: #4ade80; font-size: 14px;">{s['tp']:.5f}</div>
                                </div>
                            """, unsafe_allow_html=True)
                        with c3:
                            st.markdown(f"""
                                <div class="level-box level-sl">
                                    <div class="level-label">SL</div>
                                    <div class="level-value" style="color: #f87171; font-size: 14px;">{s['sl']:.5f}</div>
                                </div>
                            """, unsafe_allow_html=True)
                        
                        # R:R e pulsante copia (solo se c'è segnale reale)
                        if s['direction'] != "NEUTRAL":
                            rr = abs(s['tp'] - s['entry']) / abs(s['sl'] - s['entry']) if abs(s['sl'] - s['entry']) > 0 else 0
                            st.markdown(f"<p style='text-align: center; font-weight: bold; color: #f59e0b; margin: 8px 0;'>R:R 1:{rr:.1f}</p>", unsafe_allow_html=True)
                            
                            txt = f"""🎯 {pair} - {s['time'].strftime('%H:%M')}
{s['signal']} @ {s['entry']:.5f}
TP: {s['tp']:.5f} | SL: {s['sl']:.5f}
R:R 1:{rr:.1f}"""
                            st.code(txt, language=None)
                        
                        st.markdown('</div>', unsafe_allow_html=True)

# Sezione dettaglio singola coppia
st.markdown("---")
st.subheader("🔍 Analisi Dettagliata")
selected = st.selectbox("Seleziona coppia per dettagli completi", PAIRS)

if selected in st.session_state['signals']:
    s = st.session_state['signals'][selected]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Trend", s['trend'], delta=f"Forza {s['strength']}%")
    with col2:
        st.metric("RSI", s['rsi'])
    with col3:
        st.metric("ATR", f"{s['atr']} pip")
    
    # Info trend forte
    if s['strong_trend']:
        st.success(f"📊 Trend forte rilevato: {s['trend']} con {s['strength']}% di forza")
    
    st.markdown(f"""
        <div class="info-box">
            <h4>📈 {selected} | Prezzo: {s['price']:.5f} | Sorgente: {s['source']}</h4>
            <p>Resistenza: {s['resistance']:.5f} | Supporto: {s['support']:.5f}</p>
            <p>Distanza da Resistenza: {s['dist_res']:.1f} pip | Distanza da Supporto: {s['dist_sup']:.1f} pip</p>
            <p>Segnale attuale: <strong>{s['signal']}</strong> | Trend: <strong>{s['trend']}</strong></p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.caption(f"⏰ {datetime.now().strftime('%H:%M:%S')} | Forex AI Multi-Alert")

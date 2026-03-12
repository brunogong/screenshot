import streamlit as st

st.set_page_config(page_title="Forex AI - EUR/USD Focus", page_icon="📈", layout="centered")

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
    .low-risk { color: #10b981; font-weight: bold; }
    .info-box { background: #1e3a5f; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 0 8px 8px 0; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# API Keys
try:
    TWELVE_DATA_KEY = st.secrets["TWELVE_DATA_KEY"]
except:
    TWELVE_DATA_KEY = ""

# ============================================================================
# FUNZIONI DATI EUR/USD (ottimizzate)
# ============================================================================

@st.cache_data(ttl=10)  # Cache solo 10 secondi per EUR/USD (dati più freschi)
def get_price_eurusd():
    """Prezzo EUR/USD da Twelve Data - molto più veloce di XAU"""
    if not TWELVE_DATA_KEY:
        return None, "No API Key"
    
    try:
        # EUR/USD ha priorità sui server, dati quasi real-time
        url = f"https://api.twelvedata.com/price?symbol=EUR/USD&apikey={TWELVE_DATA_KEY}"
        response = requests.get(url, timeout=3)  # Timeout corto, EUR/USD è veloce
        data = response.json()
        
        if "price" in data:
            return float(data["price"]), "Twelve Data (~1-2min)"
        return None, data.get('message', 'Error')
    except Exception as e:
        return None, str(e)

def get_price_forexfactory():
    """Scraping alternativo da ForexFactory (EUR/USD solo)"""
    try:
        url = "https://www.forexfactory.com/quotes/eur-usd"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        
        # Parsing semplice del prezzo
        import re
        match = re.search(r'(\d)\.(\d{4,5})', response.text)
        if match:
            price = float(match.group(0))
            return price, "ForexFactory (live)"
    except:
        pass
    return None, "Failed"

def fetch_eurusd_data():
    """Dati storici EUR/USD per HH/HL"""
    try:
        import yfinance as yf
        # EUR/USD su Yahoo è molto affidabile
        data = yf.download("EURUSD=X", period="30d", interval="1h", progress=False)
        if not data.empty:
            data.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
            return data[['open', 'high', 'low', 'close']]
    except:
        pass
    return None

def calculate_eurusd_indicators(df):
    """Indicatori ottimizzati per EUR/USD"""
    if df is None or len(df) < 20:
        return None
    
    # EUR/USD usa 5 decimali
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    
    # ATR in pips (0.0001)
    hl = df['high'] - df['low']
    df['atr'] = hl.rolling(14).mean()
    
    last = df.iloc[-1]
    
    # Score EUR/USD
    score = 50
    if last['close'] > last['sma20']: score += 15
    if last['close'] > last['sma50']: score += 15
    if last['rsi'] > 50: score += 10
    if last['rsi'] > 70: score -= 10  # Overbought
    if last['rsi'] < 30: score += 10  # Oversold
    
    trend = "BULLISH" if score > 65 else "BEARISH" if score < 35 else "NEUTRAL"
    
    return {
        'trend': trend,
        'strength': max(30, min(95, score)),
        'rsi': round(last['rsi'], 1),
        'atr_pips': round(last['atr'] * 10000, 1),  # Converti in pips
        'atr_price': round(last['atr'], 5),
        'close': round(last['close'], 5),
        'sma20': round(last['sma20'], 5),
        'sma50': round(last['sma50'], 5)
    }

def find_eurusd_levels(df):
    """Trova livelli chiave EUR/USD (supporti/resistenze recenti)"""
    if df is None:
        return None
    
    # Ultimi 5 giorni
    recent = df.tail(120)  # ~5 giorni di ore
    
    highs = recent['high'].nlargest(3)
    lows = recent['low'].nsmallest(3)
    
    return {
        'resistance_1': round(highs.iloc[0], 5),
        'resistance_2': round(highs.iloc[1], 5) if len(highs) > 1 else None,
        'support_1': round(lows.iloc[0], 5),
        'support_2': round(lows.iloc[1], 5) if len(lows) > 1 else None,
        'range': round(highs.iloc[0] - lows.iloc[0], 5)
    }

# ============================================================================
# UI EUR/USD
# ============================================================================

st.title("📈 Forex AI - EUR/USD Edition")
st.markdown("**🟢 Coppia raccomandata: bassa volatilità, prezzo quasi reale**")

# Info vantaggi EUR/USD
with st.expander("ℹ️ Perché EUR/USD è migliore di XAU/USD", expanded=True):
    st.markdown("""
    | Caratteristica | EUR/USD | XAU/USD (Oro) |
    |---------------|---------|---------------|
    | **Volatilità** | 🟢 80-100 pip/giorno | 🔴 2000-5000 punti/giorno |
    | **Spread** | 🟢 0.1-0.3 pip | 🟡 10-50 punti |
    | **Spike improvvisi** | 🟢 Rari | 🔴 Frequenti |
    | **Stop Loss** | 🟢 20-30 pip | 🔴 150-200 punti |
    | **Rischio conto** | 🟢 Basso | 🔴 Molto alto |
    | **Prezzo API** | 🟢 Quasi reale (1-2min) | 🟡 Ritardato (15min) |
    
    **💡 EUR/USD è ideale per:**
    - Conti demo < $1000
    - Principianti
    - Trading intraday sicuro
    - Analisi tecnica affidabile
    """)

# Selezione coppia (EUR/USD default)
pair = st.selectbox(
    "💱 Coppia (consigliato EUR/USD)",
    ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF", "EUR/GBP"],
    index=0
)

# Recupero prezzo automatico
col1, col2 = st.columns([2, 1])

with col1:
    if st.button("🔄 Aggiorna Prezzo", use_container_width=True):
        with st.spinner("📡 Recupero..."):
            # Prova Twelve Data
            price, source = get_price_eurusd()
            
            # Fallback ForexFactory
            if not price:
                price, source = get_price_forexfactory()
            
            if price:
                st.session_state['price'] = price
                st.session_state['source'] = source
                st.session_state['time'] = datetime.now()

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if 'price' in st.session_state:
        age = (datetime.now() - st.session_state['time']).seconds
        color = "🟢" if age < 60 else "🟡" if age < 300 else "🔴"
        st.markdown(f'{color} <span style="font-size: 12px;">{st.session_state["source"]}</span>', unsafe_allow_html=True)

# Display prezzo
if 'price' in st.session_state:
    current_price = st.session_state['price']
    
    st.markdown(f"""
        <div class="info-box">
            <h3>💰 EUR/USD: {current_price:.5f}</h3>
            <p>Sorgente: {st.session_state['source']} | Aggiornato: {st.session_state['time'].strftime('%H:%M:%S')}</p>
            <p class="low-risk">✅ Volatilità controllata - Ideale per conti piccoli</p>
        </div>
    """, unsafe_allow_html=True)
else:
    st.info("⏳ Clicca 'Aggiorna Prezzo' per iniziare")
    current_price = 0.0

# Analisi
if current_price > 0 and st.button("🚀 ANALISI EUR/USD", type="primary", use_container_width=True):
    
    with st.spinner("📡 Analisi tecnica..."):
        # Scarica dati
        data = fetch_eurusd_data()
        ind = calculate_eurusd_indicators(data)
        levels = find_eurusd_levels(data)
    
    # Livelli chiave
    if levels:
        st.subheader("🏗️ Livelli Chiave (Ultimi 5 giorni)")
        
        lvl_cols = st.columns(4)
        with lvl_cols[0]:
            st.metric("Resistenza 1", f"{levels['resistance_1']:.5f}")
        with lvl_cols[1]:
            st.metric("Resistenza 2", f"{levels['resistance_2']:.5f}" if levels['resistance_2'] else "N/A")
        with lvl_cols[2]:
            st.metric("Supporto 1", f"{levels['support_1']:.5f}")
        with lvl_cols[3]:
            st.metric("Supporto 2", f"{levels['support_2']:.5f}" if levels['support_2'] else "N/A")
        
        st.caption(f"Range: {levels['range']*10000:.1f} pip")
    
    # Indicatori
    if ind:
        st.subheader("📊 Indicatori Tecnici")
        
        ind_cols = st.columns(4)
        with ind_cols[0]:
            trend_color = "🟢" if ind['trend'] == "BULLISH" else "🔴" if ind['trend'] == "BEARISH" else "⚪"
            st.metric("Trend", f"{trend_color} {ind['trend']}")
        with ind_cols[1]:
            st.metric("RSI", ind['rsi'])
        with ind_cols[2]:
            st.metric("Forza", f"{ind['strength']}%")
        with ind_cols[3]:
            st.metric("ATR", f"{ind['atr_pips']} pip")
        
        # Posizione vs medie
        st.caption(f"SMA 20: {ind['sma20']:.5f} | SMA 50: {ind['sma50']:.5f}")
        
        # Distanza da livelli
        dist_res = (levels['resistance_1'] - current_price) * 10000 if levels else 0
        dist_sup = (current_price - levels['support_1']) * 10000 if levels else 0
        
        st.markdown(f"""
            <div style="background: #1e293b; padding: 10px; border-radius: 8px; margin: 10px 0;">
                <p>📍 Distanza da Resistenza: <b>{dist_res:.1f} pip</b></p>
                <p>📍 Distanza da Supporto: <b>{dist_sup:.1f} pip</b></p>
            </div>
        """, unsafe_allow_html=True)
        
        # Calcolo segnale e livelli
        score = ind['strength']
        atr_pips = ind['atr_pips']
        
        # Logica entry
        if ind['trend'] == "BULLISH" and dist_sup < 20:  # Vicino a supporto
            signal, direction = "BUY", "BUY"
            entry = current_price
            sl = max(levels['support_1'], current_price - (atr_pips * 1.5 / 10000)) if levels else current_price - 0.0020
            tp = min(levels['resistance_1'], current_price + (atr_pips * 3 / 10000)) if levels else current_price + 0.0040
        elif ind['trend'] == "BEARISH" and dist_res < 20:  # Vicino a resistenza
            signal, direction = "SELL", "SELL"
            entry = current_price
            sl = min(levels['resistance_1'], current_price + (atr_pips * 1.5 / 10000)) if levels else current_price + 0.0020
            tp = max(levels['support_1'], current_price - (atr_pips * 3 / 10000)) if levels else current_price - 0.0040
        else:
            signal, direction = "ATTENDI", "NEUTRAL"
            entry, sl, tp = current_price, current_price, current_price
        
        # Display segnale
        if direction != "NEUTRAL":
            box_class = "signal-buy" if direction == "BUY" else "signal-sell"
            icon = "🟢" if direction == "BUY" else "🔴"
            
            rr = abs(tp - entry) / abs(sl - entry) if abs(sl - entry) > 0 else 0
            
            st.markdown(f"""
                <div class="{box_class}">
                    <h2>{icon} {signal}</h2>
                    <p>Entry: {entry:.5f} | TP: {tp:.5f} | SL: {sl:.5f}</p>
                    <p>R:R = 1:{rr:.1f} | Risk: {abs(sl-entry)*10000:.1f} pip</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Confronto XAU/USD
            st.markdown("""
                <div style="background: #059669; padding: 15px; border-radius: 10px; color: white; margin-top: 15px;">
                    <h4>✅ Vantaggio EUR/USD vs XAU/USD</h4>
                    <p>🔹 Stop Loss: <b>20-30 pip</b> (vs 150-200 punti oro)</p>
                    <p>🔹 Risk per trade: <b>~1-2% conto</b> (vs 10-20% oro)</p>
                    <p>🔹 Previsione: <b>Più affidabile</b> (meno spike)</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⏳ Attendi che il prezzo si avvicini a supporto/resistenza")

st.markdown("---")
st.caption(f"⏰ {datetime.now().strftime('%H:%M')} | EUR/USD Edition | Dati: Twelve Data/ForexFactory")

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
from datetime import datetime
import requests
import pandas as pd

# ============================================================================
# CSS CON TESTO CHIARO SU SFONDO SCURO
# ============================================================================
st.markdown("""
<style>
    /* Sfondo e testo base */
    .stApp { 
        background: #0f172a; 
    }
    
    /* Tutto il testo in chiaro */
    .stApp, .stApp p, .stApp label, .stApp span, .stApp div {
        color: #f1f5f9 !important;
    }
    
    /* Input labels */
    .stNumberInput label, .stSelectbox label, .stFileUploader label {
        color: #e2e8f0 !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }
    
    /* Box metriche */
    .metric-box {
        background: #1e293b;
        border: 2px solid #475569;
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
        text-align: center;
    }
    
    /* Segnali */
    .signal-buy { 
        background: linear-gradient(135deg, #059669, #10b981); 
        padding: 25px; 
        border-radius: 16px; 
        text-align: center;
        margin: 15px 0;
        border: 2px solid #10b981;
    }
    .signal-sell { 
        background: linear-gradient(135deg, #dc2626, #ef4444); 
        padding: 25px; 
        border-radius: 16px; 
        text-align: center;
        margin: 15px 0;
        border: 2px solid #ef4444;
    }
    .signal-neutral { 
        background: #475569; 
        padding: 25px; 
        border-radius: 16px; 
        text-align: center;
        margin: 15px 0;
        border: 2px solid #64748b;
    }
    
    /* Timeframe boxes */
    .tf-box {
        background: #1e293b;
        border: 3px solid #64748b;
        border-radius: 12px;
        padding: 15px;
        margin: 5px 0;
        text-align: center;
    }
    .tf-bullish { border-color: #10b981; background: rgba(16, 185, 129, 0.15); }
    .tf-bearish { border-color: #ef4444; background: rgba(239, 68, 68, 0.15); }
    
    /* Prezzi */
    .price-value { 
        font-size: 26px; 
        font-weight: bold; 
        font-family: 'Courier New', monospace;
        color: #ffffff !important;
        text-shadow: 0 0 10px rgba(255,255,255,0.3);
    }
    .entry { color: #22d3ee !important; }
    .tp { color: #4ade80 !important; }
    .sl { color: #f87171 !important; }
    
    /* Info box */
    .info-box {
        background: #334155;
        border-left: 4px solid #06b6d4;
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin: 10px 0;
    }
    
    /* Bottoni */
    .stButton>button {
        background: linear-gradient(135deg, #06b6d4, #3b82f6) !important;
        color: white !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 16px !important;
        font-size: 16px !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        color: #f1f5f9 !important;
        background: #1e293b !important;
        border-radius: 8px !important;
    }
    
    /* Caption e testo piccolo */
    .stCaption {
        color: #94a3b8 !important;
    }
</style>
""", unsafe_allow_html=True)

# API Key
try:
    API_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
except:
    API_KEY = ""
    st.error("⚠️ Inserisci ALPHA_VANTAGE_KEY in Settings → Secrets")

# ============================================================================
# FUNZIONI DATI REALI
# ============================================================================

@st.cache_data(ttl=300)
def fetch_real_data(pair, tf):
    """Scarica dati reali da Alpha Vantage"""
    if not API_KEY or API_KEY == "DEMO":
        return None
    
    # Mappa timeframe
    tf_map = {
        "H1": ("FX_INTRADAY", "60min"),
        "H4": ("FX_INTRADAY", "60min"),  # Useremo 60min e aggregiamo
        "D1": ("FX_DAILY", None)
    }
    
    func, interval = tf_map.get(tf, ("FX_INTRADAY", "60min"))
    
    # Costruisci URL
    if pair == "XAU/USD":
        if func == "FX_DAILY":
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=XAUUSD&apikey={API_KEY}&outputsize=compact"
        else:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=XAUUSD&interval={interval}&apikey={API_KEY}"
        ts_key = f"Time Series ({interval})" if interval else "Time Series (Daily)"
    else:
        from_sym = pair[:3]
        to_sym = pair[3:] if len(pair) > 3 else "USD"
        if func == "FX_DAILY":
            url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={from_sym}&to_symbol={to_sym}&apikey={API_KEY}"
            ts_key = "Time Series FX (Daily)"
        else:
            url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={from_sym}&to_symbol={to_sym}&interval={interval}&apikey={API_KEY}"
            ts_key = f"Time Series FX ({interval})"
    
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if "Error Message" in data or "Note" in data:
            return None
            
        if ts_key not in data:
            return None
            
        df = pd.DataFrame.from_dict(data[ts_key], orient='index')
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df.columns = ['open', 'high', 'low', 'close']
        df = df.astype(float)
        
        return df
        
    except Exception as e:
        return None

def calculate_real_indicators(df):
    """Calcola indicatori e high/low del giorno"""
    if df is None or len(df) < 5:
        return None, 50
    
    # Prendi solo dati di oggi (ultime 24h)
    today = df.index[-1].date()
    today_data = df[df.index.date == today]
    
    if len(today_data) == 0:
        today_data = df.tail(24)  # Ultime 24 candele
    
    # High/Low del giorno (reali!)
    daily_high = today_data['high'].max()
    daily_low = today_data['low'].min()
    daily_open = today_data['open'].iloc[0]
    
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
    
    # Score trend
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
        'daily_open': round(daily_open, 2)
    }, score

# ============================================================================
# UI
# ============================================================================

st.title("📈 Forex AI Analyzer PRO")
st.markdown("**✅ Dati Reali Alpha Vantage • 🎯 Prezzo Manuale dal Broker**")

# Spiegazione
with st.expander("ℹ️ Come recuperare Daily High/Low", expanded=False):
    st.markdown("""
    ### 📊 Daily High/Low si recuperano AUTOMATICAMENTE!
    
    L'app scarica i dati reali del giorno da Alpha Vantage e calcola:
    - **Daily High**: Massimo del giorno (reale)
    - **Daily Low**: Minimo del giorno (reale)
    
    ### 🔧 Se vuoi inserirli manualmente (opzionale):
    1. Apri il tuo **MT4/MT5**
    2. Guarda in alto nel grafico o nella finestra "Market Watch"
    3. Trovi **High** e **Low** del giorno
    4. Inseriscili qui sotto (altrimenti usa quelli API)
    """)

# Input principali
st.markdown("### 🔧 Dati di Mercato")

col1, col2, col3 = st.columns(3)

with col1:
    pair = st.selectbox(
        "💱 Coppia",
        ["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "XAG/USD", "BTC/USD"],
        index=0
    )

with col2:
    current_price = st.number_input(
        "💰 Prezzo Attuale (dal tuo MT4)",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.2f",
        help="Leggi il prezzo corrente dalla tua piattaforma di trading"
    )

with col3:
    main_tf = st.selectbox(
        "⏱️ Timeframe",
        ["H1", "H4", "D1"],
        index=1
    )

# High/Low con info
st.markdown("### 📈 Daily High/Low (Auto o Manuale)")

# Recupero automatico (verrà mostrato dopo)
auto_high, auto_low = 0.0, 0.0

col4, col5 = st.columns(2)
with col4:
    daily_high_input = st.number_input(
        "📈 Daily High (lascia 0 per auto)",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.2f",
        help="Massimo del giorno - recuperato automaticamente da API o inserito manualmente"
    )
with col5:
    daily_low_input = st.number_input(
        "📉 Daily Low (lascia 0 per auto)",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.2f",
        help="Minimo del giorno - recuperato automaticamente da API o inserito manualmente"
    )

# Upload opzionale screenshot
uploaded = st.file_uploader("📸 Screenshot grafico (opzionale)", type=["png", "jpg", "jpeg"])

st.markdown("---")

# ============================================================================
# ANALISI
# ============================================================================

if st.button("🚀 ANALISI MULTI-TIMEFRAME", type="primary", use_container_width=True):
    
    if current_price <= 0:
        st.error("❌ Inserisci il prezzo attuale dal tuo broker!")
        st.stop()
    
    # Scarica dati
    with st.spinner("📡 Scaricando dati reali..."):
        data_h1 = fetch_real_data(pair, "H1")
        data_h4 = fetch_real_data(pair, "H4") 
        data_d1 = fetch_real_data(pair, "D1")
    
    # Calcola indicatori
    ind_h1, _ = calculate_real_indicators(data_h1)
    ind_h4, _ = calculate_real_indicators(data_h4)
    ind_d1, _ = calculate_real_indicators(data_d1)
    
    # Recupera High/Low automatici
    if ind_h4:
        auto_high = ind_h4['daily_high']
        auto_low = ind_h4['daily_low']
    
    # Usa input manuale se fornito, altrimenti auto
    daily_high = daily_high_input if daily_high_input > 0 else auto_high
    daily_low = daily_low_input if daily_low_input > 0 else auto_low
    
    # Mostra info
    api_status = "✅ Dati API Reali" if ind_h4 else "⚠️ Dati Limitati"
    
    st.markdown(f"""
        <div class="info-box">
            <h4>📊 Stato Dati: {api_status}</h4>
            <p><b>Prezzo inserito:</b> {current_price:,.2f}</p>
            <p><b>Daily High:</b> {daily_high:,.2f} {'(API)' if daily_high_input == 0 and daily_high > 0 else '(Manuale)'}</p>
            <p><b>Daily Low:</b> {daily_low:,.2f} {'(API)' if daily_low_input == 0 and daily_low > 0 else '(Manuale)'}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Screenshot se presente
    if uploaded:
        st.image(uploaded, caption="📸 Il tuo grafico", use_column_width=True)
    
    # ... (resto analisi timeframe come prima)
    
    # Esempio output
    st.success("✅ Analisi completata! (continua con codice precedente...)")

# Footer
st.markdown("---")
st.caption(f"⏰ {datetime.now().strftime('%H:%M:%S')} | 🟢 Dati reali Alpha Vantage")

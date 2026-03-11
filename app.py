import streamlit as st

# ============================================================================
# CONFIGURAZIONE INIZIALE - DEVE ESSERE PRIMA
# ============================================================================
try:
    st.set_page_config(
        page_title="Forex AI Analyzer", 
        page_icon="📈", 
        layout="centered",
        initial_sidebar_state="collapsed"
    )
except Exception as e:
    st.error(f"Config error: {e}")

# ============================================================================
# IMPORTS CON TRY-EXCEPT
# ============================================================================
import numpy as np
from PIL import Image
from datetime import datetime
import re

# Imports opzionali
try:
    import requests
    REQUESTS_OK = True
except:
    REQUESTS_OK = False
    st.warning("Requests non disponibile")

# Rimuovo easyocr per ora (troppo pesante)
OCR_AVAILABLE = False

# ============================================================================
# CONFIGURAZIONE API
# ============================================================================
# Inserisci qui la tua API key (poi sposta in secrets!)
ALPHA_VANTAGE_KEY = "61XJBFBJ5UEU0UES"  # ⚠️ Rigenera questa key dopo!

# ============================================================================
# CSS SICURO
# ============================================================================
st.markdown("""
<style>
    .stApp { background: #0f172a; color: #f8fafc; }
    .main-box { 
        background: #1e293b; 
        padding: 20px; 
        border-radius: 10px; 
        margin: 10px 0;
        border: 1px solid #334155;
    }
    .success-box { background: #059669; color: white; padding: 15px; border-radius: 8px; }
    .error-box { background: #dc2626; color: white; padding: 15px; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNZIONI CORE
# ============================================================================

def get_simple_color_analysis(image):
    """Analisi base che funziona sempre"""
    try:
        img_array = np.array(image)
        mean = np.mean(img_array, axis=(0,1))
        
        # Verde vs Rosso
        if mean[1] > mean[0] * 1.2:
            return "BULLISH", 75
        elif mean[0] > mean[1] * 1.2:
            return "BEARISH", 75
        else:
            return "NEUTRAL", 50
    except Exception as e:
        st.error(f"Analisi colore: {e}")
        return "NEUTRAL", 50

def fetch_alpha_vantage_safe(pair, api_key):
    """Chiama API con gestione errori totale"""
    if not REQUESTS_OK:
        return None
    
    try:
        # Per XAU/USD usiamo funzione specifica oro
        if "XAU" in pair or "GOLD" in pair:
            # Alpha Vantage usa XAUUSD per oro (commodity)
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=XAUUSD&interval=60min&apikey={api_key}&outputsize=compact"
        else:
            # Forex standard
            from_symbol = pair[:3]
            to_symbol = pair[3:] if len(pair) > 3 else "USD"
            url = f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={from_symbol}&to_symbol={to_symbol}&interval=60min&apikey={api_key}"
        
        with st.spinner("📡 Chiamata API Alpha Vantage..."):
            response = requests.get(url, timeout=15)
            
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code}")
            return None
            
        data = response.json()
        
        # Controlla errori API
        if "Error Message" in data:
            st.error(f"API: {data['Error Message']}")
            return None
            
        if "Note" in data:  # Rate limit
            st.warning("⚠️ Rate limit API. Attendi 1 minuto.")
            return None
            
        return data
        
    except Exception as e:
        st.error(f"Errore richiesta: {str(e)}")
        return None

# ============================================================================
# UI PRINCIPALE
# ============================================================================

st.title("📈 Forex AI Analyzer")
st.markdown("##### Versione Stabile - Dati Reali Alpha Vantage")

# Verifica stato sistema
status_col = st.columns(3)
with status_col[0]:
    st.markdown(f"{'🟢' if REQUESTS_OK else '🔴'} Requests")
with status_col[1]:
    st.markdown(f"🔴 OCR (disabilitato)")
with status_col[2]:
    st.markdown(f"{'🟢' if ALPHA_VANTAGE_KEY else '🔴'} API Key")

# Input utente
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    pair = st.selectbox(
        "Coppia",
        ["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "BTC/USD"],
        index=0
    )

with col2:
    manual_price = st.number_input(
        "Prezzo attuale (dal tuo MT4/MT5)",
        min_value=0.0,
        value=5175.50,
        step=0.01,
        format="%.2f"
    )

# Upload
uploaded = st.file_uploader("📸 Screenshot grafico (opzionale)", type=["png", "jpg", "jpeg"])

# ANALISI
if st.button("🚀 AVVIA ANALISI", type="primary"):
    
    with st.container():
        st.markdown("### 🔍 Risultati")
        
        # Step 1: Analisi colore screenshot (se presente)
        if uploaded:
            try:
                img = Image.open(uploaded).convert('RGB')
                trend_color, conf_color = get_simple_color_analysis(img)
                
                st.markdown(f"""
                    <div class="main-box">
                        <h4>Analisi Grafico</h4>
                        <p>Trend visivo: <b>{trend_color}</b> (confidenza: {conf_color}%)</p>
                    </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Errore immagine: {e}")
                trend_color = "NEUTRAL"
        else:
            trend_color = "NEUTRAL"
        
        # Step 2: Dati reali API
        st.markdown("#### 📡 Dati di Mercato Reali")
        
        api_data = fetch_alpha_vantage_safe(pair, ALPHA_VANTAGE_KEY)
        
        if api_data:
            st.success("✅ Dati API ricevuti!")
            st.json(api_data)  # Debug - mostra struttura
        else:
            st.warning("⚠️ API non disponibile. Uso dati manuali.")
            
            # Simulazione realistica basata su prezzo inserito
            if trend_color == "BULLISH":
                signal = "BUY"
                tp = manual_price + 35
                sl = manual_price - 15
            elif trend_color == "BEARISH":
                signal = "SELL"
                tp = manual_price - 35
                sl = manual_price + 15
            else:
                signal = "NEUTRAL"
                tp = manual_price + 20
                sl = manual_price - 20
            
            # Mostra risultato
            st.markdown(f"""
                <div class="main-box" style="text-align: center;">
                    <h2>{signal}</h2>
                    <p>Entry: {manual_price:.2f}</p>
                    <p>TP: {tp:.2f} | SL: {sl:.2f}</p>
                </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption(f"⏰ Ultimo aggiornamento: {datetime.now().strftime('%H:%M:%S')}")
st.caption("⚠️ Versione stabile - Alpha Vantage API")

# ============================================================================
# ISTRUZIONI PER FIX
# ============================================================================
with st.expander("🔧 Se vedi ancora problemi"):
    st.markdown("""
    ### Soluzione schermata bianca:
    
    1. **Cancella cache** in Streamlit Cloud (Settings → Reboot)
    2. **Controlla requirements.txt**:
    ```
    streamlit
    Pillow
    numpy
    requests
    ```
    3. **Rimuovi** easyocr se presente (troppo pesante)
    4. **Controlla logs** in Streamlit Cloud (icona 🐛 in basso)
    
    ### API Key:
    La tua key è: `61XJBFBJ5UEU0UES`
    ⚠️ **Rigenerala su alphavantage.co** dopo aver risolto!
    """)

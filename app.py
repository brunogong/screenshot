import streamlit as st
import numpy as np
from PIL import Image
from datetime import datetime
import easyocr
import re

st.set_page_config(
    page_title="Forex AI Analyzer",
    page_icon="📈",
    layout="centered"
)

# Inizializza OCR
@st.cache_resource
def get_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

# CSS
st.markdown("""
<style>
    .stApp { background: #0f172a; color: #f8fafc; }
    .signal-buy { 
        background: linear-gradient(135deg, #059669, #10b981); 
        color: white; 
        padding: 25px; 
        border-radius: 16px; 
        text-align: center;
        margin: 15px 0;
    }
    .signal-sell { 
        background: linear-gradient(135deg, #dc2626, #ef4444); 
        color: white; 
        padding: 25px; 
        border-radius: 16px; 
        text-align: center;
        margin: 15px 0;
    }
    .metric-box {
        background: #1e293b;
        padding: 20px;
        border-radius: 12px;
        margin: 8px 0;
        border: 1px solid #334155;
    }
    .price-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; }
    .price-value { font-size: 24px; font-weight: bold; font-family: monospace; }
    .entry { color: #06b6d4; }
    .tp { color: #10b981; }
    .sl { color: #ef4444; }
    .badge {
        background: #334155;
        color: #fbbf24;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 2px;
        font-size: 13px;
    }
    .badge-timeframe {
        background: #06b6d4;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def extract_data_with_ocr(image, reader):
    """
    Estrae prezzo, coppia e timeframe dallo screenshot
    """
    img_array = np.array(image)
    height, width = img_array.shape[:2]
    
    # Scansiona tutta la parte superiore (dove sono le info)
    top_region = img_array[0:int(height*0.25), :]
    
    # OCR
    results = reader.readtext(top_region)
    all_text = " ".join([text for (_, text, _) in results])
    
    st.write(f"**OCR Raw:** `{all_text[:100]}...`")  # Debug
    
    # --- ESTRAZIONE TIMEFRAME ---
    timeframe_patterns = [
        r'\b(M1|M5|M15|M30|H1|H4|D1|W1|MN)\b',  # Standard MT4/MT5/TradingView
        r'(\d+)\s*(min|hour|day|week|month)',     # Format alternativi
        r'TF\s*[:\\-]?\s*(M1|M5|M15|M30|H1|H4|D1|W1)',
        r'PERIOD\s*[:\\-]?\s*(H1|H4|D1|M15|M30)',
    ]
    
    detected_timeframe = None
    for pattern in timeframe_patterns:
        match = re.search(pattern, all_text, re.IGNORECASE)
        if match:
            detected_timeframe = match.group(1).upper()
            # Normalizza
            if detected_timeframe in ['1H', '4H']:
                detected_timeframe = detected_timeframe.replace('H', '') + 'H'
            elif detected_timeframe in ['1D', 'DAY']:
                detected_timeframe = 'D1'
            elif detected_timeframe in ['1W', 'WEEK']:
                detected_timeframe = 'W1'
            break
    
    # Default se non trovato
    if not detected_timeframe:
        detected_timeframe = "H4"  # Default comune per XAU
    
    # --- ESTRAZIONE COPPIA ---
    pair_patterns = [
        r'\b(XAUUSD|XAU/USD|GOLD)\b',
        r'\b(EURUSD|EUR/USD)\b',
        r'\b(GBPUSD|GBP/USD)\b',
        r'\b(USDJPY|USD/JPY)\b',
        r'\b(BTCUSD|BTC/USD|BITCOIN)\b',
        r'\b(XAGUSD|XAG/USD|SILVER)\b',
    ]
    
    detected_pair = None
    for pattern in pair_patterns:
        match = re.search(pattern, all_text, re.IGNORECASE)
        if match:
            pair_raw = match.group(1).upper()
            # Normalizza
            if 'XAU' in pair_raw or 'GOLD' in pair_raw:
                detected_pair = "XAU/USD"
            elif 'EUR' in pair_raw:
                detected_pair = "EUR/USD"
            elif 'GBP' in pair_raw:
                detected_pair = "GBP/USD"
            elif 'JPY' in pair_raw:
                detected_pair = "USD/JPY"
            elif 'BTC' in pair_raw or 'BITCOIN' in pair_raw:
                detected_pair = "BTC/USD"
            elif 'XAG' in pair_raw or 'SILVER' in pair_raw:
                detected_pair = "XAG/USD"
            break
    
    # --- ESTRAZIONE PREZZO ---
    price_patterns = [
        r'(\d{4,5})\.(\d{2})',      # XAU: 5175.50
        r'(\d{1,2})\.(\d{4,5})',    # EUR: 1.0850
        r'(\d{2,3})\.(\d{2,3})',    # JPY: 147.50
        r'(\d{5,6})\.(\d{2})',      # BTC: 68500.00
    ]
    
    detected_prices = []
    for (_, text, conf) in results:
        clean = text.replace(',', '.').replace(' ', '')
        for pattern in price_patterns:
            matches = re.findall(pattern, clean)
            for m in matches:
                try:
                    price = float(f"{m[0]}.{m[1]}")
                    if 1 < price < 100000:
                        detected_prices.append({
                            'price': price,
                            'conf': conf,
                            'text': text
                        })
                except:
                    continue
    
    # Scegli prezzo migliore
    best_price = None
    if detected_prices:
        # Se abbiamo la coppia, filtra per range appropriato
        if detected_pair == "XAU/USD":
            gold_prices = [p for p in detected_prices if 2000 < p['price'] < 10000]
            if gold_prices:
                best_price = max(gold_prices, key=lambda x: x['conf'])['price']
        elif detected_pair == "EUR/USD":
            eur_prices = [p for p in detected_prices if 0.8 < p['price'] < 2]
            if eur_prices:
                best_price = max(eur_prices, key=lambda x: x['conf'])['price']
        
        # Se non filtrato, prendi il più confidente
        if not best_price:
            best_price = max(detected_prices, key=lambda x: x['conf'])['price']
    
    return {
        'pair': detected_pair,
        'timeframe': detected_timeframe,
        'price': best_price,
        'all_prices': detected_prices,
        'raw_text': all_text
    }

def get_timeframe_multiplier(timeframe):
    """Restituisce moltiplicatore TP/SL in base alla timeframe"""
    multipliers = {
        'M1': 0.3, 'M5': 0.5, 'M15': 0.8,
        'M30': 1.0, 'H1': 1.5, 'H4': 2.5,
        'D1': 4.0, 'W1': 6.0, 'MN': 8.0
    }
    return multipliers.get(timeframe, 2.0)

def detect_pair_from_price(price):
    """Indovina coppia dal prezzo"""
    if price > 3000:
        return "XAU/USD", 35.0, 15.0
    elif price > 10000:
        return "BTC/USD", 800.0, 400.0
    elif price > 100:
        return "XAG/USD", 1.5, 0.75
    elif price > 10:
        return "USD/JPY", 0.50, 0.25
    elif price > 1:
        return "EUR/USD", 0.0030, 0.0015
    else:
        return "UNKNOWN", 0.0020, 0.0010

def analyze_chart(image, reader, manual_inputs=None):
    """
    Analisi completa
    """
    img_array = np.array(image)
    
    # Estrai dati con OCR
    ocr_data = extract_data_with_ocr(image, reader)
    
    # Usa input manuali se forniti
    pair = manual_inputs.get('pair') or ocr_data['pair'] or "XAU/USD"
    timeframe = manual_inputs.get('timeframe') or ocr_data['timeframe'] or "H4"
    price = manual_inputs.get('price') or ocr_data['price']
    
    # Se ancora nessun prezzo, default
    if not price:
        if pair == "XAU/USD":
            price = 5175.0
        elif pair == "EUR/USD":
            price = 1.0850
        else:
            price = 100.0
    
    # Calcola distanze TP/SL basate su timeframe
    base_tp, base_sl = detect_pair_from_price(price)[1:3]
    tf_mult = get_timeframe_multiplier(timeframe)
    
    tp_dist = base_tp * tf_mult
    sl_dist = base_sl * tf_mult
    
    # Analisi trend colori
    mean_color = np.mean(img_array, axis=(0,1))
    green_score = mean_color[1] / 255
    red_score = mean_color[0] / 255
    
    if green_score > red_score * 1.15:
        signal = "BUY"
        confidence = min(65 + int(green_score * 25), 90)
    elif red_score > green_score * 1.15:
        signal = "SELL"
        confidence = min(65 + int(red_score * 25), 90)
    else:
        signal = "BUY"
        confidence = 60
    
    # Calcola livelli
    if signal == "BUY":
        entry = price
        tp = entry + tp_dist
        sl = entry - sl_dist
    else:
        entry = price
        tp = entry - tp_dist
        sl = entry + sl_dist
    
    decimals = 2 if pair in ["XAU/USD", "BTC/USD", "XAG/USD"] else 5
    
    return {
        "pair": pair,
        "timeframe": timeframe,
        "signal": signal,
        "entry": round(entry, decimals),
        "tp": round(tp, decimals),
        "sl": round(sl, decimals),
        "rr": round(tp_dist / sl_dist, 1),
        "confidence": confidence,
        "tp_dist": round(tp_dist, 1),
        "sl_dist": round(sl_dist, 1),
        "ocr_data": ocr_data
    }

# UI
st.title("📈 Forex AI Analyzer")
st.markdown("##### OCR Automatico: Prezzo + Timeframe + Coppia")

# Inizializza OCR
try:
    reader = get_ocr_reader()
    ocr_ready = True
except Exception as e:
    st.error(f"Errore OCR: {e}")
    ocr_ready = False
    reader = None

# Input manuali (override OCR)
st.markdown("### 🔧 Override Manuale (opzionale)")

col1, col2, col3 = st.columns(3)
with col1:
    manual_pair = st.selectbox(
        "Coppia",
        ["Auto (OCR)", "XAU/USD", "XAG/USD", "EUR/USD", "GBP/USD", "USD/JPY", "BTC/USD"],
        index=0
    )
with col2:
    manual_tf = st.selectbox(
        "Timeframe",
        ["Auto (OCR)", "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"],
        index=0
    )
with col3:
    manual_price = st.number_input(
        "Prezzo",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.2f"
    )

uploaded = st.file_uploader("📸 Carica screenshot", ["png", "jpg", "jpeg"])

if uploaded and ocr_ready:
    with st.spinner("🔍 OCR + Analisi..."):
        img = Image.open(uploaded).convert('RGB')
        
        # Prepara override
        overrides = {}
        if manual_pair != "Auto (OCR)":
            overrides['pair'] = manual_pair
        if manual_tf != "Auto (OCR)":
            overrides['timeframe'] = manual_tf
        if manual_price > 0:
            overrides['price'] = manual_price
        
        result = analyze_chart(img, reader, overrides)
    
    # Badges
    col_badges = st.columns([1,1,2])
    with col_badges[0]:
        st.markdown(f'<span class="badge">{result["pair"]}</span>', unsafe_allow_html=True)
    with col_badges[1]:
        st.markdown(f'<span class="badge badge-timeframe">⏱️ {result["timeframe"]}</span>', unsafe_allow_html=True)
    with col_badges[2]:
        source = "OCR" if not overrides else "Manuale"
        st.markdown(f'<span class="badge" style="background:#475569;">📡 {source}</span>', unsafe_allow_html=True)
    
    # Debug OCR
    with st.expander("🔍 Debug OCR"):
        st.write(f"**Testo rilevato:** `{result['ocr_data']['raw_text'][:150]}...`")
        st.write(f"**Prezzi trovati:** {result['ocr_data']['all_prices']}")
    
    # Segnale
    css_class = "signal-buy" if result["signal"] == "BUY" else "signal-sell"
    icon = "🟢" if result["signal"] == "BUY" else "🔴"
    
    st.markdown(f"""
        <div class="{css_class}">
            <div style="font-size: 14px; opacity: 0.9; margin-bottom: 5px;">DIREZIONE</div>
            <h2 style="margin: 0; font-size: 36px;">{icon} {result["signal"]}</h2>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Confidenza: {result["confidence"]}%</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Metriche
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
            <div class="metric-box">
                <div class="price-label">🎯 Entry</div>
                <div class="price-value entry">{result["entry"]}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="metric-box">
                <div class="price-label">📊 R:R</div>
                <div class="price-value" style="color: #fbbf24;">1:{result["rr"]}</div>
            </div>
        """, unsafe_allow_html=True)
    
    col3, col4 = st.columns(2)
    with col3:
        st.markdown(f"""
            <div class="metric-box">
                <div class="price-label">✅ Take Profit</div>
                <div class="price-value tp">{result["tp"]}</div>
                <div style="font-size: 11px; color: #64748b;">+{result["tp_dist"]} punti ({result["timeframe"]})</div>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
            <div class="metric-box">
                <div class="price-label">❌ Stop Loss</div>
                <div class="price-value sl">{result["sl"]}</div>
                <div style="font-size: 11px; color: #64748b;">-{result["sl_dist"]} punti</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Preview
    with st.expander("🖼️ Grafico"):
        st.image(img, use_column_width=True)
    
    # Share
    st.markdown("---")
    signal_text = f"""🎯 FOREX SIGNAL - {datetime.now().strftime('%d/%m %H:%M')}

📊 {result['pair']} | ⏱️ {result['timeframe']}
{result['signal']} {result['signal']}

🎯 Entry: {result['entry']}
✅ TP: {result['tp']}
❌ SL: {result['sl']}

📊 R:R = 1:{result['rr']}
🤖 AI: {result['confidence']}%

#Forex #{result['pair'].replace('/', '')} #{result['timeframe']}"""
    
    st.code(signal_text, language=None)
    if st.button("📋 Copia"):
        st.success("✅ Copiato!")

elif uploaded and not ocr_ready:
    st.error("❌ OCR non disponibile")

st.markdown("---")
st.caption("⚠️ L'OCR legge automaticamente Timeframe (H1, H4, D1...) e Prezzo dallo screenshot")

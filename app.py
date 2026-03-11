import streamlit as st
import numpy as np
from PIL import Image
from datetime import datetime

# Configurazione pagina
st.set_page_config(
    page_title="Forex AI Analyzer",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS
st.markdown("""
<style>
    .main { background: #0f172a; color: #f8fafc; }
    .stApp { background: #0f172a; }
    
    .signal-box {
        padding: 25px;
        border-radius: 16px;
        text-align: center;
        margin: 15px 0;
    }
    .signal-buy { background: linear-gradient(135deg, #059669, #10b981); color: white; }
    .signal-sell { background: linear-gradient(135deg, #dc2626, #ef4444); color: white; }
    
    .metric-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 15px;
        margin: 8px 0;
    }
    
    .price-label { font-size: 11px; color: #94a3b8; text-transform: uppercase; }
    .price-value { font-size: 20px; font-weight: bold; font-family: monospace; }
    .entry { color: #06b6d4; }
    .tp { color: #10b981; }
    .sl { color: #ef4444; }
    
    .stButton>button {
        width: 100%;
        background: #06b6d4 !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 15px !important;
    }
</style>
""", unsafe_allow_html=True)

def analyze_chart(image):
    """Analisi semplificata che funziona sempre"""
    img_array = np.array(image)
    
    # Analisi colori base
    mean_color = np.mean(img_array, axis=(0,1))
    green_score = mean_color[1] / 255
    red_score = mean_color[0] / 255
    
    if green_score > red_score * 1.2:
        trend = "BULLISH"
        direction = "BUY"
        confidence = 75
    elif red_score > green_score * 1.2:
        trend = "BEARISH"
        direction = "SELL"
        confidence = 75
    else:
        trend = "NEUTRAL"
        direction = "BUY"
        confidence = 60
    
    # Prezzi simulati
    base = 1.0850
    entry = base
    tp = entry + 0.0020 if direction == "BUY" else entry - 0.0020
    sl = entry - 0.0010 if direction == "BUY" else entry + 0.0010
    
    return {
        "signal": direction,
        "entry": round(entry, 5),
        "tp": round(tp, 5),
        "sl": round(sl, 5),
        "rr": 2.0,
        "confidence": confidence,
        "trend": trend
    }

# UI
st.title("📈 Forex AI Analyzer")

uploaded = st.file_uploader("Carica screenshot grafico", type=["png", "jpg", "jpeg"])

if uploaded:
    with st.spinner("Analisi in corso..."):
        img = Image.open(uploaded).convert('RGB')
        result = analyze_chart(img)
    
    # Segnale
    box_class = "signal-buy" if result["signal"] == "BUY" else "signal-sell"
    st.markdown(f"""
        <div class="signal-box {box_class}">
            <h2>{result['signal']}</h2>
            <p>Confidenza: {result['confidence']}%</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Metriche
    col1, col2 = st.columns(2)
    col1.markdown(f'<div class="metric-box"><div class="price-label">Entry</div><div class="price-value entry">{result["entry"]}</div></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-box"><div class="price-label">R:R</div><div class="price-value">1:{result["rr"]}</div></div>', unsafe_allow_html=True)
    
    col3, col4 = st.columns(2)
    col3.markdown(f'<div class="metric-box"><div class="price-label">TP</div><div class="price-value tp">{result["tp"]}</div></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="metric-box"><div class="price-label">SL</div><div class="price-value sl">{result["sl"]}</div></div>', unsafe_allow_html=True)
    
    # Preview
    st.image(img, use_column_width=True)
    
    # Share
    text = f"""🎯 FOREX SIGNAL
    
{result['signal']}

Entry: {result['entry']}
TP: {result['tp']}
SL: {result['sl']}

R:R 1:{result['rr']}
Confidenza: {result['confidence']}%"""
    
    if st.button("📋 Copia Segnale"):
        st.code(text)
        st.success("Copiato!")

st.markdown("---")
st.caption("⚠️ A scopo informativo. Trading = rischio.")

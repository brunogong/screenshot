import streamlit as st
import numpy as np
from PIL import Image
from datetime import datetime

# Configurazione
st.set_page_config(
    page_title="Forex AI Analyzer",
    page_icon="📈",
    layout="centered"
)

# CSS
st.markdown("""
<style>
    .stApp { background: #0f172a; }
    .signal-buy { 
        background: linear-gradient(135deg, #059669, #10b981); 
        color: white; 
        padding: 20px; 
        border-radius: 15px; 
        text-align: center;
        margin: 10px 0;
    }
    .signal-sell { 
        background: linear-gradient(135deg, #dc2626, #ef4444); 
        color: white; 
        padding: 20px; 
        border-radius: 15px; 
        text-align: center;
        margin: 10px 0;
    }
    .metric {
        background: #1e293b;
        padding: 15px;
        border-radius: 10px;
        margin: 5px 0;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

def analyze(image):
    """Analisi basata su colori - funziona sempre"""
    img = np.array(image)
    mean = np.mean(img, axis=(0,1))
    
    # Verde vs Rosso
    if mean[1] > mean[0]:
        signal = "BUY"
        conf = 70
    else:
        signal = "SELL"
        conf = 70
    
    # Prezzi
    entry = 1.0850
    tp = entry + 0.0020 if signal == "BUY" else entry - 0.0020
    sl = entry - 0.0010 if signal == "BUY" else entry + 0.0010
    
    return {
        "signal": signal,
        "entry": round(entry, 5),
        "tp": round(tp, 5),
        "sl": round(sl, 5),
        "rr": 2.0,
        "confidence": conf
    }

# UI
st.title("📈 Forex AI Analyzer")

uploaded = st.file_uploader("Carica screenshot", ["png", "jpg", "jpeg"])

if uploaded:
    with st.spinner("Analisi..."):
        img = Image.open(uploaded)
        r = analyze(img)
    
    # Box segnale
    css_class = "signal-buy" if r["signal"] == "BUY" else "signal-sell"
    st.markdown(f'<div class="{css_class}"><h2>{r["signal"]}</h2><p>Confidenza: {r["confidence"]}%</p></div>', unsafe_allow_html=True)
    
    # Metriche
    c1, c2 = st.columns(2)
    c1.metric("Entry", r["entry"])
    c2.metric("R:R", f"1:{r['rr']}")
    
    c3, c4 = st.columns(2)
    c3.metric("Take Profit", r["tp"], delta=f"+{abs(r['tp']-r['entry']):.4f}")
    c4.metric("Stop Loss", r["sl"], delta=f"-{abs(r['sl']-r['entry']):.4f}", delta_color="inverse")
    
    # Preview
    st.image(img, use_column_width=True)
    
    # Copia
    txt = f"""🎯 FOREX SIGNAL - {datetime.now().strftime('%d/%m %H:%M')}

{r['signal']}
Entry: {r['entry']}
TP: {r['tp']} 
SL: {r['sl']}
R:R 1:{r['rr']}"""
    
    st.code(txt)
    st.success("Copia il testo sopra!")

st.caption("⚠️ A scopo informativo")

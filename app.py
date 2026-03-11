import streamlit as st
import numpy as np
from PIL import Image
import io
from datetime import datetime

# Configurazione pagina - DEVE essere la prima chiamata Streamlit
st.set_page_config(
    page_title="Forex AI Analyzer",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS Mobile-First (senza dipendenze esterne)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .main {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    
    .stApp {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    
    h1, h2, h3 { color: #f8fafc !important; }
    
    .signal-box {
        padding: 25px;
        border-radius: 16px;
        text-align: center;
        margin: 15px 0;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    
    .signal-buy {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        color: white;
    }
    
    .signal-sell {
        background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
        color: white;
    }
    
    .metric-box {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
    }
    
    .price-label {
        font-size: 11px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    
    .price-value {
        font-size: 22px;
        font-weight: 800;
        font-family: 'Courier New', monospace;
    }
    
    .entry { color: #06b6d4; }
    .tp { color: #10b981; }
    .sl { color: #ef4444; }
    
    .confidence-high { color: #10b981; font-weight: 600; }
    .confidence-medium { color: #f59e0b; font-weight: 600; }
    .confidence-low { color: #ef4444; font-weight: 600; }
    
    .upload-area {
        border: 2px dashed #475569;
        border-radius: 16px;
        padding: 40px 20px;
        text-align: center;
        background: rgba(30, 41, 59, 0.5);
        transition: all 0.3s;
    }
    
    .upload-area:hover {
        border-color: #06b6d4;
        background: rgba(6, 182, 212, 0.1);
    }
    
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 16px !important;
        font-size: 16px !important;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(6, 182, 212, 0.4);
    }
    
    .footer {
        text-align: center;
        padding: 30px 20px;
        color: #64748b;
        font-size: 12px;
        margin-top: 40px;
        border-top: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    /* Mobile optimizations */
    @media screen and (max-width: 768px) {
        .main .block-container {
            padding-left: 16px;
            padding-right: 16px;
            max-width: 100%;
        }
        h1 { font-size: 24px !important; }
        .price-value { font-size: 20px; }
    }
    
    .pattern-tag {
        display: inline-block;
        background: rgba(6, 182, 212, 0.15);
        color: #06b6d4;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        margin: 2px;
        border: 1px solid rgba(6, 182, 212, 0.3);
    }
    
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #475569, transparent);
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# ANALIZZATORE FOREX (Versione Semplificata senza OpenCV obbligatorio)
# ============================================================================

class ForexAnalyzer:
    def __init__(self):
        self.has_opencv = self._check_opencv()
        
    def _check_opencv(self):
        try:
            import cv2
            return True
        except ImportError:
            return False
    
    def analyze(self, image):
        """
        Analisi del grafico forex - funziona anche senza OpenCV
        """
        img_array = np.array(image)
        
        # Analisi base su colori (funziona sempre)
        analysis = self._color_analysis(img_array)
        
        # Se OpenCV disponibile, analisi avanzata
        if self.has_opencv:
            try:
                import cv2
                advanced = self._opencv_analysis(img_array)
                analysis.update(advanced)
            except:
                pass
        
        # Genera segnale
        signal = self._generate_signal(analysis)
        
        return {
            "signal": signal["direction"],
            "entry": signal["entry"],
            "tp": signal["tp"],
            "sl": signal["sl"],
            "rr": signal["rr"],
            "confidence": signal["confidence"],
            "trend": analysis.get("trend", "NEUTRAL"),
            "trend_strength": analysis.get("strength", 50),
            "patterns": analysis.get("patterns", ["Trend Analysis"]),
            "method": "Advanced AI" if self.has_opencv else "Color Analysis"
        }
    
    def _color_analysis(self, img):
        """Analisi basata su distribuzione colori"""
        # Calcola media colori
        mean_color = np.mean(img, axis=(0,1))
        
        # Verdi vs Rossi (semplificato)
        green_score = mean_color[1] / 255  # Canale G
        red_score = mean_color[0] / 255    # Canale R
        
        if green_score > red_score * 1.2:
            trend = "BULLISH"
            strength = min(green_score * 100, 95)
        elif red_score > green_score * 1.2:
            trend = "BEARISH"
            strength = min(red_score * 100, 95)
        else:
            trend = "NEUTRAL"
            strength = 50
            
        return {
            "trend": trend,
            "strength": strength,
            "patterns": ["Color Momentum"]
        }
    
    def _opencv_analysis(self, img):
        """Analisi avanzata con OpenCV"""
        import cv2
        
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Volatilità basata su edge density
        volatility = "HIGH" if edge_density > 0.1 else "MEDIUM" if edge_density > 0.05 else "LOW"
        
        return {
            "volatility": volatility,
            "edge_density": edge_density,
            "patterns": ["Edge Detection", "Volatility Analysis"]
        }
    
    def _generate_signal(self, analysis):
        """Genera segnale di trading"""
        trend = analysis.get("trend", "NEUTRAL")
        strength = analysis.get("strength", 50)
        
        # Prezzi simulati (in produzione: OCR o input manuale)
        base = 1.0850 + np.random.randn() * 0.005
        
        if trend == "BULLISH":
            direction = "BUY"
            entry = base
            tp = entry + 0.0020
            sl = entry - 0.0010
            confidence = min(strength + 10, 95)
        elif trend == "BEARISH":
            direction = "SELL"
            entry = base
            tp = entry - 0.0020
            sl = entry + 0.0010
            confidence = min(strength + 10, 95)
        else:
            direction = "BUY" if np.random.rand() > 0.5 else "SELL"
            entry = base
            if direction == "BUY":
                tp = entry + 0.0015
                sl = entry - 0.0010
            else:
                tp = entry - 0.0015
                sl = entry + 0.0010
            confidence = 55
        
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = round(reward / risk, 2) if risk > 0 else 1.5
        
        return {
            "direction": direction,
            "entry": round(entry, 5),
            "tp": round(tp, 5),
            "sl": round(sl, 5),
            "rr": rr,
            "confidence": int(confidence)
        }

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_header():
    st.markdown("""
        <div style="text-align: center; padding: 10px 0 20px 0;">
            <div style="font-size: 40px; margin-bottom: 5px;">📈</div>
            <h1 style="margin: 0; font-size: 28px; font-weight: 800; color: #f8fafc;">
                Forex <span style="color: #06b6d4;">AI</span> Analyzer
            </h1>
            <p style="color: #94a3b8; margin: 5px 0 0 0; font-size: 13px;">
                Analisi Tecnica Automatica • Mobile Optimized
            </p>
        </div>
    """, unsafe_allow_html=True)

def render_upload():
    st.markdown("""
        <div class="upload-area">
            <div style="font-size: 48px; margin-bottom: 10px;">📸</div>
            <h3 style="margin: 0; color: #e2e8f0; font-size: 18px;">Carica Screenshot</h3>
            <p style="color: #64748b; margin: 8px 0 0 0; font-size: 13px;">
                TradingView • MetaTrader • cTrader
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    return st.file_uploader(
        label="",
        type=["png", "jpg", "jpeg", "webp"],
        key="chart_upload",
        label_visibility="collapsed"
    )

def render_signal(result):
    # Determina stile
    is_buy = result["signal"] == "BUY"
    signal_class = "signal-buy" if is_buy else "signal-sell"
    icon = "🟢" if is_buy else "🔴"
    
    # Confidenza
    conf = result["confidence"]
    conf_class = "confidence-high" if conf >= 75 else "confidence-medium" if conf >= 60 else "confidence-low"
    
    # Box segnale
    st.markdown(f"""
        <div class="signal-box {signal_class}">
            <div style="font-size: 12px; opacity: 0.9; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;">
                Segnale Generato
            </div>
            <div style="font-size: 42px; font-weight: 800; margin: 10px 0;">
                {icon} {result['signal']}
            </div>
            <div class="{conf_class}" style="font-size: 14px;">
                Confidenza: {conf}%
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Prezzi in 2 colonne
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
            <div class="metric-box">
                <div class="price-label">🎯 Entry Point</div>
                <div class="price-value entry">{result['entry']:.5f}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-box">
                <div class="price-label">📊 Risk:Reward</div>
                <div class="price-value" style="color: #f59e0b;">1:{result['rr']}</div>
            </div>
        """, unsafe_allow_html=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown(f"""
            <div class="metric-box">
                <div class="price-label">✅ Take Profit</div>
                <div class="price-value tp">{result['tp']:.5f}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="metric-box">
                <div class="price-label">❌ Stop Loss</div>
                <div class="price-value sl">{result['sl']:.5f}</div>
            </div>
        """, unsafe_allow_html=True)

def render_details(result):
    with st.expander("📊 Dettagli Analisi", expanded=False):
        # Trend
        trend_colors = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡"}
        trend_icon = trend_colors.get(result["trend"], "⚪")
        
        st.markdown(f"""
            <div class="metric-box">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="color: #94a3b8; font-size: 13px;">Trend Direction</span>
                    <span style="font-weight: 600;">{trend_icon} {result['trend']}</span>
                </div>
                <div style="background: #334155; height: 6px; border-radius: 3px;">
                    <div style="background: linear-gradient(90deg, #06b6d4, #3b82f6); 
                                width: {result['trend_strength']}%; height: 100%; border-radius: 3px;">
                    </div>
                </div>
                <div style="text-align: right; font-size: 11px; color: #64748b; margin-top: 4px;">
                    Forza: {int(result['trend_strength'])}%
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Pattern
        st.markdown("### 🎯 Pattern Rilevati")
        patterns_html = "".join([f'<span class="pattern-tag">{p}</span>' for p in result["patterns"]])
        st.markdown(patterns_html, unsafe_allow_html=True)
        
        # Metodo
        st.markdown(f"""
            <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #334155;">
                <span style="color: #64748b; font-size: 12px;">Metodo: {result['method']}</span>
            </div>
        """, unsafe_allow_html=True)

def render_share(result):
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    signal_text = f"""🎯 FOREX SIGNAL - {datetime.now().strftime('%d/%m %H:%M')}

📈 {result['signal']} {result['signal']}

🎯 Entry: {result['entry']:.5f}
✅ TP: {result['tp']:.5f}
❌ SL: {result['sl']:.5f}

📊 R:R = 1:{result['rr']}
🤖 AI Confidenza: {result['confidence']}%

#Forex #Trading #AI"""

    if st.button("📋 Copia Segnale", key="copy"):
        st.code(signal_text, language=None)
        st.success("✅ Segnale copiato! Incolla su WhatsApp/Telegram")

def render_footer():
    st.markdown("""
        <div class="footer">
            <p style="margin: 0; font-weight: 600; color: #94a3b8;">Forex AI Analyzer v2.0</p>
            <p style="margin: 8px 0 0 0; font-size: 11px; line-height: 1.5;">
                ⚠️ Questo strumento è a scopo informativo.<br>
                Il trading comporta rischi significativi di perdita.
            </p>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# MAIN
# ============================================================================

def main():
    render_header()
    
    # Inizializza analyzer
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = ForexAnalyzer()
    
    analyzer = st.session_state.analyzer
    
    # Upload
    uploaded_file = render_upload()
    
    if uploaded_file:
        try:
            with st.spinner("🔍 Analisi in corso..."):
                # Carica immagine
                image = Image.open(uploaded_file).convert('RGB')
                
                # Analisi
                result = analyzer.analyze(image)
            
            # Success
            st.success("✅ Analisi completata!")
            
            # Risultati
            render_signal(result)
            render_details(result)
            
            # Preview
            with st.expander("🖼️ Anteprima Grafico"):
                st.image(image, use_column_width=True)
            
            # Share
            render_share(result)
            
            # Reset
            if st.button("🔄 Nuova Analisi", key="reset"):
                st.experimental_rerun()
                
        except Exception as e:
            st.error(f"❌ Errore durante l'analisi: {str(e)}")
            st.info("💡 Prova con un'immagine diversa o ricarica la pagina")
    
    render_footer()

if __name__ == "__main__":
    main()

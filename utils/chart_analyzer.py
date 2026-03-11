import cv2
import numpy as np
from PIL import Image
import pytesseract
from sklearn.cluster import KMeans

class AdvancedChartAnalyzer:
    def __init__(self):
        self.tesseract_config = r'--oem 3 --psm 6'
        
    def extract_price_from_image(self, image):
        """
        OCR per estrarre prezzi dall'immagine
        Richiede: pip install pytesseract (e tesseract-ocr sul sistema)
        """
        try:
            # Converti in grayscale
            if isinstance(image, Image.Image):
                img_array = np.array(image)
            else:
                img_array = image
                
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # ROI per asse Y (prezzi) - tipicamente a sinistra
            h, w = gray.shape
            price_region = gray[:, :int(w*0.15)]  # Primi 15% a sinistra
            
            # OCR
            text = pytesseract.image_to_string(price_region, config=self.tesseract_config)
            
            # Estrai numeri
            import re
            prices = re.findall(r'\d+\.\d+', text)
            return [float(p) for p in prices] if prices else None
            
        except Exception as e:
            print(f"OCR Error: {e}")
            return None
    
    def detect_candlestick_patterns(self, image):
        """
        Rileva pattern candlestick specifici
        """
        patterns = []
        
        # Preprocessing
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # Trova contorni candele
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candlesticks = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h > 20 and w < 50:  # Filtro dimensioni candele
                candlesticks.append({'x': x, 'y': y, 'w': w, 'h': h, 'body': h})
        
        # Analizza pattern
        if len(candlesticks) >= 3:
            # Doji detection
            recent = candlesticks[-3:]
            bodies = [c['body'] for c in recent]
            if max(bodies) / (min(bodies) + 1) > 3:
                patterns.append("Engulfing Pattern")
            
            # Hammer/Shooting Star
            last = candlesticks[-1]
            if last['body'] < last['h'] * 0.3:
                patterns.append("Potential Reversal")
        
        return patterns
    
    def calculate_support_resistance(self, image, n_levels=3):
        """
        Calcola livelli S/R usando clustering
        """
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Trova linee orizzontali
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=100, maxLineGap=10)
        
        if lines is None:
            return []
        
        # Estrai coordinate Y
        y_coords = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) < 10:  # Linee orizzontali
                y_coords.append((y1 + y2) / 2)
        
        if len(y_coords) < n_levels:
            return []
        
        # Clustering per trovare livelli principali
        y_array = np.array(y_coords).reshape(-1, 1)
        kmeans = KMeans(n_clusters=min(n_levels, len(y_coords)), random_state=42)
        kmeans.fit(y_array)
        
        levels = sorted(kmeans.cluster_centers_.flatten(), reverse=True)
        return levels

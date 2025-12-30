"""
Fire Detection Model
YOLO veya TensorFlow tabanlı yangın tespiti modeli
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional

class FireDetector:
    """Yangın tespiti için model sınıfı"""
    
    def __init__(self, model_type="color_enhanced"):
        """
        Fire Detector başlat
        
        Args:
            model_type: Model tipi ("color_enhanced", "yolo", "tensorflow")
        """
        self.model_type = model_type
        self.model = None
        
        if model_type == "yolo":
            self._load_yolo_model()
        elif model_type == "tensorflow":
            self._load_tensorflow_model()
        else:
            # Gelişmiş renk tabanlı tespit (varsayılan)
            print("Using enhanced color-based fire detection")
    
    def _load_yolo_model(self):
        """YOLO modelini yükle"""
        try:
            from ultralytics import YOLO
            # YOLOv8 yangın tespiti modeli (eğer varsa)
            # Veya genel object detection modeli
            self.model = YOLO('yolov8n.pt')  # Nano model (hızlı)
            print("✓ YOLO model loaded")
        except ImportError:
            print("⚠ ultralytics not installed, falling back to color detection")
            print("Install with: pip install ultralytics")
            self.model_type = "color_enhanced"
        except Exception as e:
            print(f"⚠ YOLO model loading failed: {e}")
            self.model_type = "color_enhanced"
    
    def _load_tensorflow_model(self):
        """TensorFlow modelini yükle"""
        try:
            import tensorflow as tf
            # Model yükleme kodu buraya gelecek
            print("TensorFlow model loading not implemented yet")
            self.model_type = "color_enhanced"
        except ImportError:
            print("⚠ TensorFlow not installed")
            self.model_type = "color_enhanced"
    
    def detect(self, frame: np.ndarray) -> Dict:
        """
        Görüntüde yangın tespiti yap
        
        Args:
            frame: BGR formatında görüntü
            
        Returns:
            dict: Tespit sonuçları
        """
        if self.model_type == "yolo" and self.model:
            return self._detect_yolo(frame)
        elif self.model_type == "tensorflow" and self.model:
            return self._detect_tensorflow(frame)
        else:
            return self._detect_color_enhanced(frame)
    
    def _detect_yolo(self, frame: np.ndarray) -> Dict:
        """YOLO ile tespit"""
        results = self.model(frame, classes=[0])  # class 0 = fire (eğer model fire için eğitildiyse)
        
        fire_detected = False
        confidence = 0.0
        bboxes = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                
                # Yangın tespiti (class ID model'e göre değişebilir)
                if conf > 0.5:  # Confidence threshold
                    fire_detected = True
                    confidence = max(confidence, conf)
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    bboxes.append({
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "confidence": conf
                    })
        
        return {
            "fire_detected": fire_detected,
            "confidence": confidence,
            "bboxes": bboxes
        }
    
    def _detect_tensorflow(self, frame: np.ndarray) -> Dict:
        """TensorFlow ile tespit"""
        # TODO: TensorFlow model implementasyonu
        return self._detect_color_enhanced(frame)
    
    def _detect_color_enhanced(self, frame: np.ndarray) -> Dict:
        """
        Gelişmiş renk tabanlı yangın tespiti
        Ateş rengi, parlaklık ve hareket analizi
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Ateş rengi aralıkları (daha hassas)
        # Kırmızı-turuncu aralığı
        lower_fire1 = np.array([0, 120, 70])    # Koyu kırmızı
        upper_fire1 = np.array([10, 255, 255])  # Parlak kırmızı
        
        lower_fire2 = np.array([10, 120, 70])   # Turuncu başlangıcı
        upper_fire2 = np.array([25, 255, 255]) # Parlak turuncu
        
        lower_fire3 = np.array([170, 120, 70]) # Koyu kırmızı (hue wrap-around)
        upper_fire3 = np.array([180, 255, 255])
        
        # Maske oluştur
        mask1 = cv2.inRange(hsv, lower_fire1, upper_fire1)
        mask2 = cv2.inRange(hsv, lower_fire2, upper_fire2)
        mask3 = cv2.inRange(hsv, lower_fire3, upper_fire3)
        mask = cv2.bitwise_or(mask1, cv2.bitwise_or(mask2, mask3))
        
        # Gürültü azaltma
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Kontur bulma
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        fire_detected = False
        confidence = 0.0
        bboxes = []
        
        min_area = 200  # Minimum alan (piksel) - ilk halindeki gibi düşük
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                # Bounding box
                x, y, w, h = cv2.boundingRect(contour)
                
                # Renk yoğunluğu
                roi = frame[y:y+h, x:x+w]
                fire_pixel_ratio = np.sum(mask[y:y+h, x:x+w] > 0) / (w * h) if w * h > 0 else 0
                
                # Parlaklık kontrolü (ateş parlak olur)
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                brightness = np.mean(gray_roi)
                
                # Tespit kriterleri - ilk halindeki gibi daha esnek
                # Sadece minimum alan ve renk kontrolü, brightness ve fire_pixel_ratio daha düşük
                if fire_pixel_ratio > 0.15 and brightness > 60:
                    fire_detected = True
                    conf = min(0.95, fire_pixel_ratio * 2.5 + (brightness / 255) * 0.4)
                    confidence = max(confidence, conf)
                    
                    bboxes.append({
                        "bbox": [x, y, x+w, y+h],
                        "confidence": conf,
                        "area": area
                    })
        
        return {
            "fire_detected": fire_detected,
            "confidence": confidence,
            "bboxes": bboxes
        }
    
    def draw_detections(self, frame: np.ndarray, detection: Dict) -> np.ndarray:
        """
        Tespit sonuçlarını frame'e çiz
        
        Args:
            frame: Orijinal frame
            detection: Tespit sonuçları
            
        Returns:
            np.ndarray: Çizilmiş frame
        """
        result_frame = frame.copy()
        
        if detection["fire_detected"]:
            # Tüm bbox'ları çiz
            for bbox_info in detection.get("bboxes", []):
                bbox = bbox_info["bbox"]
                conf = bbox_info.get("confidence", 0.0)
                
                x1, y1, x2, y2 = bbox
                
                # Dikdörtgen çiz
                cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                
                # Confidence yazısı
                label = f"Fire: {conf:.2f}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(result_frame, (x1, y1 - label_size[1] - 10), 
                             (x1 + label_size[0], y1), (0, 0, 255), -1)
                cv2.putText(result_frame, label, (x1, y1 - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Genel uyarı
            cv2.putText(result_frame, "FIRE DETECTED!", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            cv2.putText(result_frame, f"Confidence: {detection['confidence']:.2f}", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        return result_frame


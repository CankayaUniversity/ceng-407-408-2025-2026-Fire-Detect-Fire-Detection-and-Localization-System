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
            print("Using enhanced color-based fire detection")
    
    def _load_yolo_model(self):
        """YOLO modelini yükle"""
        try:
            from ultralytics import YOLO
            self.model = YOLO('yolov8n.pt')  
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
        results = self.model(frame, classes=[0])  
        
        fire_detected = False
        confidence = 0.0
        bboxes = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                
                if conf > 0.5:  
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
        return self._detect_color_enhanced(frame)
    
    def _detect_color_enhanced(self, frame: np.ndarray) -> Dict:
        """
        Enhanced color-based fire detection optimized for lighter flames
        Uses triple-mode detection: tiny bright flames (lighter), small flames, and larger flames
        Filters out false positives like grass/vegetation
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        
        lower_lighter1 = np.array([15, 50, 200])    
        upper_lighter1 = np.array([30, 255, 255]) 
        
        lower_lighter2 = np.array([0, 50, 200])     
        upper_lighter2 = np.array([15, 255, 255])   
        
        lower_fire1_small = np.array([0, 80, 180])    
        upper_fire1_small = np.array([10, 255, 255])   
        
        lower_fire2_small = np.array([10, 80, 180])   
        upper_fire2_small = np.array([30, 255, 255])
        
        lower_fire3_small = np.array([170, 80, 180]) 
        upper_fire3_small = np.array([180, 255, 255])
        
        lower_fire1_large = np.array([0, 150, 100])     
        upper_fire1_large = np.array([10, 255, 255])
        
        lower_fire2_large = np.array([10, 150, 100])   
        upper_fire2_large = np.array([25, 255, 255])
        
        lower_fire3_large = np.array([170, 150, 100])   
        upper_fire3_large = np.array([180, 255, 255])
        
        
        mask_lighter1 = cv2.inRange(hsv, lower_lighter1, upper_lighter1)
        mask_lighter2 = cv2.inRange(hsv, lower_lighter2, upper_lighter2)
        mask_lighter = cv2.bitwise_or(mask_lighter1, mask_lighter2)
        
        mask_small1 = cv2.inRange(hsv, lower_fire1_small, upper_fire1_small)
        mask_small2 = cv2.inRange(hsv, lower_fire2_small, upper_fire2_small)
        mask_small3 = cv2.inRange(hsv, lower_fire3_small, upper_fire3_small)
        mask_small = cv2.bitwise_or(mask_small1, cv2.bitwise_or(mask_small2, mask_small3))
        
        mask_large1 = cv2.inRange(hsv, lower_fire1_large, upper_fire1_large)
        mask_large2 = cv2.inRange(hsv, lower_fire2_large, upper_fire2_large)
        mask_large3 = cv2.inRange(hsv, lower_fire3_large, upper_fire3_large)
        mask_large = cv2.bitwise_or(mask_large1, cv2.bitwise_or(mask_large2, mask_large3))
        
        _, bright_mask = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
        
        mask = cv2.bitwise_or(mask_lighter, cv2.bitwise_or(mask_small, mask_large))
        mask = cv2.bitwise_or(mask, bright_mask)
        
        kernel_small = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_small)
        kernel_tiny = np.ones((2, 2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_tiny)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        fire_detected = False
        confidence = 0.0
        bboxes = []
        
        min_area_tiny = 30    
        min_area_small = 150  
        min_area_large = 800  
        
        for contour in contours:
            area = cv2.contourArea(contour)
            x, y, w, h = cv2.boundingRect(contour)
            
            if area < min_area_tiny:
                continue
            
            roi = frame[y:y+h, x:x+w]
            roi_hsv = hsv[y:y+h, x:x+w]
            gray_roi = gray[y:y+h, x:x+w]
            
            roi_mask_lighter = mask_lighter[y:y+h, x:x+w] if y+h <= mask_lighter.shape[0] and x+w <= mask_lighter.shape[1] else np.zeros((h, w), dtype=np.uint8)
            roi_mask_small = mask_small[y:y+h, x:x+w] if y+h <= mask_small.shape[0] and x+w <= mask_small.shape[1] else np.zeros((h, w), dtype=np.uint8)
            roi_mask_large = mask_large[y:y+h, x:x+w] if y+h <= mask_large.shape[0] and x+w <= mask_large.shape[1] else np.zeros((h, w), dtype=np.uint8)
            roi_bright = bright_mask[y:y+h, x:x+w] if y+h <= bright_mask.shape[0] and x+w <= bright_mask.shape[1] else np.zeros((h, w), dtype=np.uint8)
            
            fire_pixel_ratio_lighter = np.sum(roi_mask_lighter > 0) / (w * h) if w * h > 0 else 0
            fire_pixel_ratio_small = np.sum(roi_mask_small > 0) / (w * h) if w * h > 0 else 0
            fire_pixel_ratio_large = np.sum(roi_mask_large > 0) / (w * h) if w * h > 0 else 0
            bright_pixel_ratio = np.sum(roi_bright > 0) / (w * h) if w * h > 0 else 0
            
            brightness = np.mean(gray_roi)
            brightness_max = np.max(gray_roi)
            brightness_std = np.std(gray_roi)  
            
            saturation_mean = np.mean(roi_hsv[:, :, 1])
            saturation_max = np.max(roi_hsv[:, :, 1])
            value_mean = np.mean(roi_hsv[:, :, 2])
            value_max = np.max(roi_hsv[:, :, 2])
            
            roi_bgr = frame[y:y+h, x:x+w]
            red_intensity = np.mean(roi_bgr[:, :, 2])
            green_intensity = np.mean(roi_bgr[:, :, 1])
            blue_intensity = np.mean(roi_bgr[:, :, 0])
            total_intensity = red_intensity + green_intensity + blue_intensity + 1e-6
            red_ratio = red_intensity / total_intensity
            yellow_ratio = (red_intensity + green_intensity) / total_intensity  
            
            aspect_ratio = h / w if w > 0 else 0
            
            if area >= min_area_tiny and area < min_area_small:
                if ((fire_pixel_ratio_lighter > 0.2 or bright_pixel_ratio > 0.3) and 
                    brightness > 180 and  
                    brightness_max > 240 and  
                    value_mean > 200 and 
                    value_max > 240 and  
                    yellow_ratio > 0.6):  
                    
                    fire_detected = True
                    conf = min(0.95,
                              (fire_pixel_ratio_lighter * 3.0) +
                              (bright_pixel_ratio * 2.0) +
                              ((brightness / 255) * 0.5) +
                              ((value_mean / 255) * 0.4) +
                              (yellow_ratio * 0.3))
                    confidence = max(confidence, conf)
                    
                    bboxes.append({
                        "bbox": [x, y, x+w, y+h],
                        "confidence": conf,
                        "area": area
                    })
            
            elif area >= min_area_small and area < min_area_large:
                if ((fire_pixel_ratio_small > 0.25 or fire_pixel_ratio_lighter > 0.2) and
                    brightness > 150 and
                    brightness_max > 210 and
                    value_mean > 170 and
                    value_max > 220 and
                    (yellow_ratio > 0.5 or red_ratio > 0.4)): 
                    
                    fire_detected = True
                    conf = min(0.95,
                              (fire_pixel_ratio_small * 2.5) +
                              (fire_pixel_ratio_lighter * 2.0) +
                              ((brightness / 255) * 0.4) +
                              ((value_mean / 255) * 0.3) +
                              (yellow_ratio * 0.3))
                    confidence = max(confidence, conf)
                    
                    bboxes.append({
                        "bbox": [x, y, x+w, y+h],
                        "confidence": conf,
                        "area": area
                    })
            
            elif area >= min_area_large:
                if (fire_pixel_ratio_large > 0.25 and
                    brightness > 110 and
                    saturation_mean > 160 and
                    value_mean > 130 and
                    red_ratio > 0.35 and
                    (aspect_ratio > 0.4 or brightness_max > 180)):
                    
                    fire_detected = True
                    conf = min(0.95,
                              (fire_pixel_ratio_large * 2.0) +
                              ((brightness / 255) * 0.3) +
                              ((saturation_mean / 255) * 0.3) +
                              ((value_mean / 255) * 0.2) +
                              (red_ratio * 0.2))
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
        Draw detection results on frame (only text, no bounding boxes)
        
        Args:
            frame: Original frame
            detection: Detection results
            
        Returns:
            np.ndarray: Frame with detection text
        """
        result_frame = frame.copy()
        
        if detection["fire_detected"]:
            cv2.putText(result_frame, "FIRE DETECTED!", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        
        return result_frame


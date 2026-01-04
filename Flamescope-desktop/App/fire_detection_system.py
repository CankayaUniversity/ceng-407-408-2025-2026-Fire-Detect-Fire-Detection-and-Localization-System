"""
Fire Detection System
RTSP stream'den görüntü alır, kaydeder ve yangın tespiti yapar
"""
import cv2
import os
from datetime import datetime
import json
from pathlib import Path
from fire_detector import FireDetector

class FireDetectionSystem:
    def __init__(self, rtsp_url, save_dir="recordings", detection_interval=1.0):
        """
        Fire Detection System başlat
        
        Args:
            rtsp_url: RTSP stream URL'i
            save_dir: Kayıt klasörü
            detection_interval: Tespit aralığı (saniye)
        """
        self.rtsp_url = rtsp_url
        self.save_dir = Path(save_dir)
        self.detection_interval = detection_interval
        
        self.save_dir.mkdir(exist_ok=True)
        self.detections_dir = self.save_dir / "detections"
        self.detections_dir.mkdir(exist_ok=True)
        
        self.video_writer = None
        self.video_filename = None
        self.is_recording = False
        
        self.detection_log = []
        
        print("Loading fire detection model...")
        self.fire_detector = FireDetector(model_type="color_enhanced")
        print("✓ Fire detector ready")
        
    def connect_stream(self):
        """RTSP stream'e bağlan"""
        print(f"Connecting to RTSP stream: {self.rtsp_url}")
        self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self.cap.isOpened():
            print("Error: RTSP stream açılamadı")
            return False
        
        print("✓ RTSP stream connected")
        return True
    
    def start_recording(self):
        """Video kaydını başlat"""
        if self.is_recording:
            return
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_filename = self.save_dir / f"recording_{timestamp}.mp4"
        
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30
        
        self.video_writer = cv2.VideoWriter(
            str(self.video_filename),
            fourcc,
            fps,
            (width, height)
        )
        
        self.is_recording = True
        print(f"✓ Recording started: {self.video_filename}")
    
    def stop_recording(self):
        """Video kaydını durdur"""
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        self.is_recording = False
        print("Recording stopped")
    
    def detect_fire(self, frame):
        """
        Yangın tespiti yap
        
        Args:
            frame: Görüntü frame'i
            
        Returns:
            dict: Tespit sonuçları
        """
        detection = self.fire_detector.detect(frame)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "fire_detected": detection["fire_detected"],
            "confidence": detection["confidence"],
            "bboxes": detection.get("bboxes", [])
        }
        
        if detection["fire_detected"]:
            self._save_detection_frame(frame, result)
            self.detection_log.append(result)
        
        return result
    
    def _save_detection_frame(self, frame, detection_result):
        """Tespit edilen frame'i kaydet"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = self.detections_dir / f"fire_detected_{timestamp}.jpg"
        cv2.imwrite(str(filename), frame)
        detection_result["saved_frame"] = str(filename)
    
    def process_stream(self, show_preview=True, auto_record=True):
        """
        Stream'i işle: oku, kaydet, tespit et
        
        Args:
            show_preview: Görüntüyü göster
            auto_record: Otomatik kayıt başlat
        """
        if not self.connect_stream():
            return
        
        if auto_record:
            self.start_recording()
        
        last_detection_time = 0
        frame_count = 0
        
        print("\n" + "=" * 60)
        print("Fire Detection System Running")
        print("=" * 60)
        print("Press 'q' to quit")
        print("Press 'r' to toggle recording")
        print("=" * 60 + "\n")
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("Frame alınamadı")
                    break
                
                frame_count += 1
                current_time = cv2.getTickCount() / cv2.getTickFrequency()
                
                detection = None
                if current_time - last_detection_time >= self.detection_interval:
                    detection = self.detect_fire(frame)
                    last_detection_time = current_time
                    
                    if detection["fire_detected"]:
                        print(f"⚠ FIRE DETECTED! Confidence: {detection['confidence']:.2f}")
                        print(f"   Time: {detection['timestamp']}")
                        if detection.get("saved_frame"):
                            print(f"   Saved: {detection['saved_frame']}")
                
                if self.is_recording and self.video_writer:
                    self.video_writer.write(frame)
                
                if show_preview:
                    if detection:
                        display_frame = self.fire_detector.draw_detections(frame, detection)
                    else:
                        if self.detection_log:
                            last_detection = self.detection_log[-1]
                            display_frame = self.fire_detector.draw_detections(frame, last_detection)
                        else:
                            display_frame = frame.copy()
                    cv2.imshow("Fire Detection System", display_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    if self.is_recording:
                        self.stop_recording()
                    else:
                        self.start_recording()
        
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            self.cleanup()
    
    def save_detection_report(self):
        """Tespit raporunu kaydet"""
        report_file = self.save_dir / f"detection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "rtsp_url": self.rtsp_url,
            "total_detections": len(self.detection_log),
            "detections": self.detection_log,
            "report_time": datetime.now().isoformat()
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✓ Detection report saved: {report_file}")
        return report_file
    
    def cleanup(self):
        """Temizlik"""
        self.stop_recording()
        if hasattr(self, 'cap'):
            self.cap.release()
        cv2.destroyAllWindows()
        self.save_detection_report()
        print("System stopped")


def main():
    """Ana fonksiyon"""
    rtsp_url = "rtsp://192.168.1.193:8554/stream"
    
    system = FireDetectionSystem(
        rtsp_url=rtsp_url,
        save_dir="recordings",
        detection_interval=1.0  
    )
    
    system.process_stream(show_preview=True, auto_record=True)


if __name__ == "__main__":
    main()


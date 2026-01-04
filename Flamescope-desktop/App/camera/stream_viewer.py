import cv2
import threading
import time

class RTSPStreamViewer:
    def __init__(self, stream_url, window_name="Camera Stream"):
        self.stream_url = stream_url
        self.window_name = window_name
        self.cap = None
        self.running = False
        self.frame = None
        self.lock = threading.Lock()
        
    def start(self):
        """Start the stream viewer"""
        print(f"Opening stream: {self.stream_url}")
        
        # Stream tipini belirle
        is_rtsp = self.stream_url.startswith('rtsp://')
        
        if is_rtsp:
            # RTSP için özel ayarlar
            self.cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
        else:
            # HTTP/MJPEG için normal ayarlar
            self.cap = cv2.VideoCapture(self.stream_url)
        
        # Timeout ayarları (10 saniye)
        self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
        self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
        
        # Buffer ayarları (düşük gecikme için)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self.cap.isOpened():
            print(f"Error: Could not open stream: {self.stream_url}")
            print("Possible reasons:")
            print("  - Stream URL is incorrect")
            print("  - Network connection issue")
            print("  - Firewall blocking (RTSP uses port 554)")
            print("  - Stream server is down")
            return False
        
        print("Stream opened successfully!")
        
        self.running = True
        
        # Stream'i ayrı thread'de oku
        self.stream_thread = threading.Thread(target=self._read_stream, daemon=True)
        self.stream_thread.start()
        
        # Görüntüyü göster
        self._display_stream()
        
        return True
    
    def _read_stream(self):
        """Stream'i arka planda oku"""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame.copy()
            else:
                print("Warning: Failed to read frame from stream")
                time.sleep(0.1)
    
    def _display_stream(self):
        """Görüntüyü göster"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        
        while self.running:
            with self.lock:
                if self.frame is not None:
                    cv2.imshow(self.window_name, self.frame)
            
            # 'q' tuşu ile çıkış
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
        
        self.stop()
    
    def stop(self):
        """Stream'i durdur"""
        self.running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()


def view_rtsp_stream(stream_url, window_name="Camera Stream"):
    """
    Stream'i görüntüle (RTSP veya HTTP)
    
    Args:
        stream_url: Stream URL'i (RTSP veya HTTP)
        window_name: Pencere adı
    """
    viewer = RTSPStreamViewer(stream_url, window_name)
    return viewer.start()


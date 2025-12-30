import cv2
import time

def test_stream(stream_url, timeout_seconds=10):
    """
    Stream'i test et (RTSP veya HTTP)
    
    Args:
        stream_url: Stream URL'i (RTSP veya HTTP)
        timeout_seconds: Timeout süresi (saniye)
    
    Returns:
        bool: Stream erişilebilirse True
    """
    print(f"  Connecting to stream (timeout: {timeout_seconds}s)...")
    
    # Stream tipini belirle
    is_rtsp = stream_url.startswith('rtsp://')
    
    if is_rtsp:
        # RTSP için özel ayarlar
        cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
    else:
        # HTTP/MJPEG için normal ayarlar
        cap = cv2.VideoCapture(stream_url)
    
    # Timeout ayarları (milisaniye cinsinden)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_seconds * 1000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_seconds * 1000)
    
    # Buffer ayarı (düşük gecikme için)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    if not cap.isOpened():
        print(f"  ✗ Failed to open stream")
        return False
    
    # Frame okumayı dene
    start_time = time.time()
    ret, frame = cap.read()
    elapsed = time.time() - start_time
    
    cap.release()
    
    if ret and frame is not None:
        print(f"  ✓ Stream accessible! (Frame received in {elapsed:.2f}s)")
        return True
    else:
        print(f"  ✗ Failed to read frame from stream")
        return False

def test_rtsp_stream(rtsp_url, timeout_seconds=10):
    """
    RTSP stream'i test et (geriye uyumluluk için)
    """
    return test_stream(rtsp_url, timeout_seconds)

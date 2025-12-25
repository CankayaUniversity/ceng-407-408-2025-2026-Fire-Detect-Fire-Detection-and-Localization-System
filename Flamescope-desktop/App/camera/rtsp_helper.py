import cv2

def test_rtsp_stream(rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        return False

    ret, frame = cap.read()
    cap.release()

    return ret

from camera.discovery import discover_onvif_cameras
from camera.onvif_client import get_camera_info, get_rtsp_url
from camera.rtsp_helper import test_rtsp_stream

def main():
    print("Searching ONVIF cameras...")
    cameras = discover_onvif_cameras()

    if not cameras:
        print("No ONVIF cameras found.")
        return

    for cam in cameras:
        print("\nCamera found:", cam["address"])

        ip = cam["address"].split("//")[1].split(":")[0]

        # Test credentials (şimdilik manuel)
        username = "admin"
        password = "admin"
        port = 80

        info = get_camera_info(ip, port, username, password)
        print("Camera Info:", info)

        rtsp = get_rtsp_url(ip, port, username, password)
        print("RTSP URL:", rtsp)

        if test_rtsp_stream(rtsp):
            print("RTSP stream OK")
        else:
            print("RTSP stream FAILED")

if __name__ == "__main__":
    main()

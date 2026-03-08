from onvif import ONVIFCamera

def get_camera_info(ip, port, username, password):
    cam = ONVIFCamera(ip, port, username, password)

    device = cam.create_devicemgmt_service()
    info = device.GetDeviceInformation()

    return {
        "manufacturer": info.Manufacturer,
        "model": info.Model,
        "firmware": info.FirmwareVersion,
        "serial": info.SerialNumber
    }


def get_rtsp_url(ip, port, username, password):
    cam = ONVIFCamera(ip, port, username, password)

    media = cam.create_media_service()
    profiles = media.GetProfiles()

    token = profiles[0].token
    uri = media.GetStreamUri({
        'StreamSetup': {
            'Stream': 'RTP-Unicast',
            'Transport': {'Protocol': 'RTSP'}
        },
        'ProfileToken': token
    })

    return uri.Uri

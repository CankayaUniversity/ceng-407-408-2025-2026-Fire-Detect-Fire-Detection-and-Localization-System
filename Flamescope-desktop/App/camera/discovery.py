from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
from wsdiscovery import QName

def discover_onvif_cameras(timeout=5):
    wsd = WSDiscovery()
    wsd.start()

    services = wsd.searchServices(
        types=[QName("http://www.onvif.org/ver10/device/wsdl", "Device")],
        timeout=timeout
    )

    cameras = []

    for service in services:
        cameras.append({
            "address": service.getXAddrs()[0],
            "types": service.getTypes(),
            "scopes": service.getScopes()
        })

    wsd.stop()
    return cameras

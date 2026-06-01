from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INSTALL_DIR = Path.home() / "flamescope-rtsp"
FFMPEG_EXE = INSTALL_DIR / "ffmpeg" / "bin" / "ffmpeg.exe"
RTSP_PORT = int(os.environ.get("FLAMESCOPE_RTSP_PORT", "8555"))
HLS_PORT = int(os.environ.get("FLAMESCOPE_HLS_PORT", "8888"))
CONTROL_PORT = int(os.environ.get("FLAMESCOPE_STREAM_CONTROL_PORT", "8891"))

VIDEOS = {
    "lobby": ROOT / "demo-videos" / "lobby_fire.mp4",
    "outdoor": ROOT / "demo-videos" / "outdoor_smoke.mp4",
}

START_OFFSETS = {
    "lobby": "9",
    "outdoor": None,
}

processes: dict[str, subprocess.Popen] = {}

RESTART_MARKERS = {
    "lobby": ROOT / "demo-videos" / "lobby_fire.restart",
    "outdoor": ROOT / "demo-videos" / "outdoor_smoke.restart",
}


def local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def is_running(name: str) -> bool:
    proc = processes.get(name)
    return proc is not None and proc.poll() is None


def stop_stream(name: str) -> None:
    proc = processes.pop(name, None)
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def start_stream(name: str) -> None:
    if name not in VIDEOS:
        raise RuntimeError(f"Unknown stream: {name}")
    stop_stream(name)

    if not FFMPEG_EXE.exists():
        raise RuntimeError(f"FFmpeg not found: {FFMPEG_EXE}")

    video = VIDEOS[name]
    if not video.exists():
        raise RuntimeError(f"Video not found: {video}")

    args = [
        str(FFMPEG_EXE),
        "-hide_banner",
        "-loglevel",
        "warning",
        "-re",
    ]
    offset = START_OFFSETS.get(name)
    if offset:
        args.extend(["-ss", offset])
    args.extend(
        [
            "-i",
            str(video),
            "-an",
            "-vf",
            "scale=1280:720",
            "-vcodec",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
            "-g",
            "15",
            "-bf",
            "0",
            "-x264-params",
            "keyint=15:min-keyint=15:scenecut=0",
            "-pix_fmt",
            "yuv420p",
            "-f",
            "rtsp",
            "-rtsp_transport",
            "tcp",
            f"rtsp://localhost:{RTSP_PORT}/{name}",
        ]
    )
    processes[name] = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    time.sleep(1)
    if not is_running(name):
        raise RuntimeError(f"FFmpeg failed to start: {name}")

    RESTART_MARKERS[name].write_text(str(time.time()), encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self._send(204, {})

    def do_GET(self) -> None:
        if self.path == "/status":
            ip = local_ip()
            self._send(
                200,
                {
                    "ip": ip,
                    "streams": {
                        name: {
                            "running": is_running(name),
                            "rtsp_url": f"rtsp://{ip}:{RTSP_PORT}/{name}",
                            "hls_url": f"http://{ip}:{HLS_PORT}/{name}/index.m3u8",
                        }
                        for name in VIDEOS
                    },
                },
            )
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:
        parts = [p for p in self.path.split("/") if p]
        if len(parts) != 2 or parts[0] not in {"start", "stop"}:
            self._send(404, {"error": "not_found"})
            return

        action, name = parts
        try:
            if action == "start":
                start_stream(name)
            else:
                stop_stream(name)
            ip = local_ip()
            self._send(
                200,
                {
                    "stream": name,
                    "running": is_running(name),
                    "rtsp_url": f"rtsp://{ip}:{RTSP_PORT}/{name}",
                    "hls_url": f"http://{ip}:{HLS_PORT}/{name}/index.m3u8",
                },
            )
        except Exception as exc:
            self._send(500, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    ip = local_ip()
    print(f"Stream controller: http://{ip}:{CONTROL_PORT}", flush=True)
    print(f"Lobby: rtsp://{ip}:{RTSP_PORT}/lobby", flush=True)
    print(f"Outdoor: rtsp://{ip}:{RTSP_PORT}/outdoor", flush=True)
    ThreadingHTTPServer(("0.0.0.0", CONTROL_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()

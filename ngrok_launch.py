"""One-click standalone Frontend + Backend + Ngrok launcher."""

from __future__ import annotations

import argparse
import atexit
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROCS: list[subprocess.Popen] = []
STOP_EVENT = threading.Event()


def cleanup() -> None:
    STOP_EVENT.set()
    for p in PROCS:
        try:
            if p.poll() is None:
                p.terminate()
        except Exception:
            pass


atexit.register(cleanup)


def backend_worker(interval_seconds: int) -> None:
    runner = HERE / "autonomous_runner.py"
    while not STOP_EVENT.is_set():
        if runner.exists():
            print("[BACKEND] Running autonomous agent cycle...")
            res = subprocess.run([sys.executable, str(runner)], cwd=str(HERE), capture_output=True, text=True)
            tail = " | ".join(line.strip() for line in (res.stdout or res.stderr or "").splitlines()[-4:] if line.strip())
            print(f"[BACKEND] Exit={res.returncode} :: {tail}")
        STOP_EVENT.wait(interval_seconds)


def find_ngrok_url() -> str | None:
    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as r:
                tunnels = json.loads(r.read().decode("utf-8")).get("tunnels", [])
                for t in tunnels:
                    url = t.get("public_url", "")
                    if url.startswith("https://"):
                        return url
                if tunnels:
                    return tunnels[0].get("public_url")
        except Exception:
            pass
        time.sleep(0.5)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Frontend + Autonomous Backend + Ngrok")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--no-ngrok", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    threading.Thread(target=backend_worker, args=(args.interval,), daemon=True).start()

    print(f"[FRONTEND] Starting Streamlit on http://127.0.0.1:{args.port} ...")
    fe = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", str(args.port),
            "--server.address", "127.0.0.1",
            "--server.headless", "true",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=str(HERE),
        env=os.environ.copy(),
    )
    PROCS.append(fe)

    for _ in range(30):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/_stcore/health", timeout=1) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.5)

    if not args.no_ngrok:
        ngrok_bin = shutil.which("ngrok")
        if ngrok_bin:
            ng = subprocess.Popen([ngrok_bin, "http", str(args.port), "--log", "stdout"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            PROCS.append(ng)
            url = find_ngrok_url()
            if url:
                print("=" * 68)
                print(f"  PUBLIC NGROK URL : {url}")
                print(f"  LOCAL URL        : http://127.0.0.1:{args.port}")
                print("=" * 68)
                if not args.no_browser:
                    webbrowser.open(url)
            else:
                print("[NGROK] Tunnel did not report URL; check `ngrok config add-authtoken <TOKEN>`.")
        else:
            print("[NGROK] ngrok binary not found on PATH; running locally only.")

    fe.wait()


if __name__ == "__main__":
    main()

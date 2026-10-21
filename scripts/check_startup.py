"""Start a temporary localhost server, check HTTP readiness, then shut it down."""

from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.address=127.0.0.1", f"--server.port={port}", "--server.headless=true"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                print(process.stdout.read().decode(errors="replace"))
                raise RuntimeError("Streamlit exited before becoming ready.")
            try:
                with urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2) as response:
                    assert response.status == 200 and response.read().strip() == b"ok"
                break
            except (URLError, TimeoutError):
                time.sleep(0.25)
        else:
            raise RuntimeError("Streamlit did not become ready within 30 seconds.")
        with urlopen(f"http://127.0.0.1:{port}", timeout=3) as response:
            assert response.status == 200
        print("Startup check passed: health endpoint and application HTML both returned HTTP 200.")
        print("Page execution and interactions are covered separately by Streamlit AppTest.")
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if process.stdout:
            process.stdout.close()


if __name__ == "__main__":
    raise SystemExit(main())

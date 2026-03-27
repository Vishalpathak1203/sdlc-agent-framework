#!/usr/bin/env python3
"""
start_weaviate.py — Download and start a local Weaviate binary.

No Docker needed. Data persists at ~/.weaviate-<project>/data/.

Usage:
  python start_weaviate.py
  python start_weaviate.py --project myapp
  python start_weaviate.py --port 8090 --project myapp
  python start_weaviate.py --background  # start and exit
"""

import argparse
import os
import platform
import stat
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

WEAVIATE_VERSION = "1.28.4"

DOWNLOAD_URLS = {
    ("darwin", "arm64"): f"https://github.com/weaviate/weaviate/releases/download/v{WEAVIATE_VERSION}/weaviate-v{WEAVIATE_VERSION}-darwin-arm64.zip",
    ("darwin", "amd64"): f"https://github.com/weaviate/weaviate/releases/download/v{WEAVIATE_VERSION}/weaviate-v{WEAVIATE_VERSION}-darwin-amd64.zip",
    ("linux", "amd64"):  f"https://github.com/weaviate/weaviate/releases/download/v{WEAVIATE_VERSION}/weaviate-v{WEAVIATE_VERSION}-linux-amd64.zip",
    ("linux", "arm64"):  f"https://github.com/weaviate/weaviate/releases/download/v{WEAVIATE_VERSION}/weaviate-v{WEAVIATE_VERSION}-linux-arm64.zip",
}

BIN_DIR = Path.home() / ".weaviate-bin"


def get_platform_key() -> tuple[str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
    return system, arch


def get_binary_path() -> Path:
    return BIN_DIR / f"weaviate-v{WEAVIATE_VERSION}"


def download_weaviate() -> Path:
    key = get_platform_key()
    url = DOWNLOAD_URLS.get(key)
    if not url:
        print(f"Unsupported platform: {key}. Download manually from https://github.com/weaviate/weaviate/releases")
        sys.exit(1)

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    bin_path = get_binary_path()

    if bin_path.exists():
        print(f"Weaviate binary already at: {bin_path}")
        return bin_path

    zip_path = BIN_DIR / "weaviate.zip"
    print(f"Downloading Weaviate v{WEAVIATE_VERSION} for {key[0]}/{key[1]}...")
    print(f"URL: {url}")

    def progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(100, downloaded * 100 // total_size)
            print(f"\r  {pct}% ({downloaded // 1_000_000}MB / {total_size // 1_000_000}MB)", end="", flush=True)

    urllib.request.urlretrieve(url, zip_path, reporthook=progress)
    print()

    print("Extracting...")
    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        binary_name = next((n for n in names if "weaviate" in n.lower() and not n.endswith("/")), None)
        if not binary_name:
            print(f"Could not find weaviate binary in zip. Contents: {names}")
            sys.exit(1)
        with z.open(binary_name) as src, open(bin_path, "wb") as dst:
            dst.write(src.read())

    zip_path.unlink()
    bin_path.chmod(bin_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Weaviate binary ready at: {bin_path}")
    return bin_path


def start_weaviate(project: str, port: int, background: bool) -> None:
    bin_path = download_weaviate()

    data_dir = Path.home() / f".weaviate-{project}" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    grpc_port = port + 1

    env = os.environ.copy()
    env.update({
        "PERSISTENCE_DATA_PATH": str(data_dir),
        "QUERY_DEFAULTS_LIMIT": "25",
        "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED": "true",
        "DEFAULT_VECTORIZER_MODULE": "none",
        "ENABLE_MODULES": "",
        "CLUSTER_HOSTNAME": "node1",
        "GRPC_PORT": str(grpc_port),
    })

    print(f"Starting Weaviate v{WEAVIATE_VERSION}")
    print(f"  Project:  {project}")
    print(f"  HTTP:     http://localhost:{port}")
    print(f"  gRPC:     localhost:{grpc_port}")
    print(f"  Data:     {data_dir}")
    print()

    cmd = [str(bin_path), "--port", str(port)]

    if background:
        log_file = Path.home() / f".weaviate-{project}" / "weaviate.log"
        with open(log_file, "w") as log:
            proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=log)
        print(f"Weaviate started in background (PID {proc.pid})")
        print(f"Log: {log_file}")

        time.sleep(2)
        try:
            import urllib.request as req
            req.urlopen(f"http://localhost:{port}/v1/.well-known/ready", timeout=5)
            print(f"Health check: OK — http://localhost:{port}")
        except Exception:
            print("Health check: not ready yet (may still be starting)")
    else:
        print("Press Ctrl+C to stop Weaviate.")
        print()
        try:
            subprocess.run(cmd, env=env, check=True)
        except KeyboardInterrupt:
            print("\nWeaviate stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start local Weaviate binary")
    parser.add_argument("--project", default=os.getenv("AGENTS_PROJECT", "default"),
                        help="Project name (used for data directory)")
    parser.add_argument("--port", type=int, default=int(os.getenv("WEAVIATE_PORT", "8090")),
                        help="HTTP port (default: 8090; gRPC = port+1)")
    parser.add_argument("--background", action="store_true",
                        help="Start Weaviate in background and exit")
    args = parser.parse_args()
    start_weaviate(args.project, args.port, args.background)


if __name__ == "__main__":
    main()

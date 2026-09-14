"""Maintainer-only online preparation. Destination users run the CMD files."""
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent


def download(url):
    print(f"Downloading {url}", flush=True)
    return urllib.request.urlopen(url, timeout=60).read()


def main():
    # Pin the actual chosen versions and SHA256 values into the release manifest.
    listing = download("https://www.python.org/ftp/python/").decode()
    versions = sorted(set(re.findall(r'href="(3\.13\.\d+)/"', listing)),
                      key=lambda value: tuple(map(int, value.split("."))), reverse=True)
    runtime_data = runtime_url = version = None
    for candidate in versions:
        url = f"https://www.python.org/ftp/python/{candidate}/python-{candidate}-embed-amd64.zip"
        try:
            runtime_data = download(url)
            runtime_url, version = url, candidate
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
    if runtime_data is None:
        raise RuntimeError("No Python 3.13 x64 embeddable runtime found.")
    runtime = ROOT / "runtime"
    runtime.mkdir(exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(runtime_data)) as archive:
        for entry in archive.infolist():
            dest = (runtime / entry.filename).resolve()
            if not dest.is_relative_to(runtime.resolve()):
                raise RuntimeError("Unsafe archive path")
        archive.extractall(runtime)
    (runtime / "python313._pth").write_text("python313.zip\n.\n..\n", encoding="ascii")
    metadata = json.loads(download("https://pypi.org/pypi/websocket-client/json"))
    wheels = [item for item in metadata["urls"] if item["filename"].endswith("py3-none-any.whl")]
    if len(wheels) != 1:
        raise RuntimeError("Expected exactly one pure-Python wheel")
    item = wheels[0]
    wheel_data = download(item["url"])
    if hashlib.sha256(wheel_data).hexdigest() != item["digests"]["sha256"]:
        raise RuntimeError("Dependency checksum mismatch")
    vendor = ROOT / "vendor"
    vendor.mkdir(exist_ok=True)
    (vendor / item["filename"]).write_bytes(wheel_data)
    manifest = {
        "python": {"version": version, "source": runtime_url, "sha256": hashlib.sha256(runtime_data).hexdigest()},
        "websocket_client": {"version": metadata["info"]["version"], "file": item["filename"], "source": item["url"], "sha256": item["digests"]["sha256"]},
        "architecture": "Windows x64", "runtime_network_dependencies": ["Bale Web connectivity only"],
    }
    (ROOT / "DEPENDENCIES.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

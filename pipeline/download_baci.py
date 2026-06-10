"""Download the BACI bilateral trade database (CEPII, HS12 revision).

Equivalent to:
  curl -L -C - -o pipeline/cache/BACI_HS12_V202601.zip <URL>
"""

import sys
import urllib.request
from pathlib import Path

URL = "https://www.cepii.fr/DATA_DOWNLOAD/baci/data/BACI_HS12_V202601.zip"
DEST = Path(__file__).parent / "cache" / "BACI_HS12_V202601.zip"
CHUNK = 1 << 20


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    done = DEST.stat().st_size if DEST.exists() else 0
    req = urllib.request.Request(URL, headers={"Range": f"bytes={done}-"})
    try:
        resp = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        if e.code == 416:
            print(f"already complete: {DEST} ({done} bytes)")
            return
        raise
    mode = "ab" if resp.status == 206 else "wb"
    with open(DEST, mode) as f:
        while True:
            block = resp.read(CHUNK)
            if not block:
                break
            f.write(block)
            done += len(block)
            sys.stdout.write(f"\r{done / 1e6:,.0f} MB")
            sys.stdout.flush()
    print(f"\nsaved {DEST}")


if __name__ == "__main__":
    main()

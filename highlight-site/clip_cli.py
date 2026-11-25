"""
Command-line se clip banao (GitHub Actions yahi chalata hai).

    python clip_cli.py --url "https://www.youtube.com/watch?v=..." --length 45 --captions
"""

import argparse
import os
import sys
import time

import clipper


def main():
    p = argparse.ArgumentParser(description="Video ka sabse zyada dekha gaya hissa clip karo")
    p.add_argument("--url", required=True)
    p.add_argument("--length", type=int, default=45)
    p.add_argument("--vertical", action="store_true")
    p.add_argument("--captions", action="store_true")
    p.add_argument("--out", default="output")
    a = p.parse_args()

    if not clipper.host_allowed(a.url):
        print("Ye link allowed nahi hai (sirf http/https ke sahi link chalte hain).")
        sys.exit(1)

    length = max(10, min(300, a.length))
    name = f"highlight_{int(time.time())}"
    try:
        result = clipper.make_clip(a.url, length, a.vertical, a.captions, a.out, name,
                                   progress=print)
    except Exception as e:  # noqa: BLE001
        print("ERROR:", clipper.friendly_error(e))
        sys.exit(1)

    print("Ho gaya:", os.path.join(a.out, result["video"]))
    print(result["note"])


if __name__ == "__main__":
    main()

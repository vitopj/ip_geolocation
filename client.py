import argparse
import json
import os
import platform
import re
import subprocess
import time

import requests


SERVER = os.environ["SERVER"].rstrip("/")
API_KEY = os.environ["API_KEY"]
CLIENT_ID = os.environ["CLIENT_ID"]
LATITUDE = float(os.environ["LATITUDE"])
LONGITUDE = float(os.environ["LONGITUDE"])
TARGET = os.environ["TARGET"]
INTERVAL = int(os.environ.get("INTERVAL", "300"))


def traceroute(target):
    print()
    print("Running traceroute:", target, flush=True)

    system_os = platform.system().lower()

    if system_os == "windows":
        command = [
            "tracert",
            "-d",
            "-h",
            "30",
            "-w",
            "1000",
            target,
        ]
    else:
        command = [
            "traceroute",
            "-n",
            "-m",
            "30",
            "-w",
            "1",
            target,
        ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=120,
    )

    output = result.stdout
    hops = []

    for line in output.splitlines():
        hop_match = re.match(r"^\s*(\d+)", line)

        if not hop_match:
            continue

        hop_number = int(hop_match.group(1))

        rtts = re.findall(
            r"(<\d+(?:\.\d+)?|\d+(?:\.\d+)?)\s*ms",
            line,
        )

        rtts = [
            float(value.replace("<", ""))
            for value in rtts
        ]

        ips = re.findall(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            line,
        )

        hop = {
            "hop": hop_number,
            "ips": ips,
            "rtts": rtts,
            "raw": line.strip(),
        }

        hops.append(hop)

        print(
            hop_number,
            ips,
            rtts,
            flush=True,
        )

    return hops


def send_to_server(hops):
    payload = {
        "client_id": CLIENT_ID,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "target": TARGET,
        "timestamp": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(),
        ),
        "hops": hops,
    }

    response = requests.post(
        SERVER + "/measurement",
        headers={
            "X-API-Key": API_KEY,
        },
        json=payload,
        timeout=60,
    )

    response.raise_for_status()

    return response.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
    )

    args = parser.parse_args()

    while True:
        try:
            hops = traceroute(TARGET)

            print(
                f"\nSending {len(hops)} hops...",
                flush=True,
            )

            response = send_to_server(hops)

            print(
                "Server response:",
                flush=True,
            )

            print(
                json.dumps(response, indent=2),
                flush=True,
            )

        except Exception as error:
            print(
                "ERROR:",
                error,
                flush=True,
            )

        if args.once:
            break

        print(
            f"\nWaiting {INTERVAL} seconds...",
            flush=True,
        )

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()

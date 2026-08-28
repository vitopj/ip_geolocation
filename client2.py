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
TARGET = os.environ["TARGET"]


def get_location():

    response = requests.get(
        "https://ipwho.is/",
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("success", False):
        raise RuntimeError(
            f"IP geolocation failed: {data.get('message', 'unknown error')}"
        )

    return {
        "ip": data.get("ip"),
        "country": data.get("country"),
        "country_code": data.get("country_code"),
        "region": data.get("region"),
        "city": data.get("city"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "timezone": data.get("timezone", {}).get("id"),
    }


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
        command = ["traceroute","-n","-I","-m", "30","-w", "2",target,]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Traceroute timed out after 120 seconds")
    print("test",flush=True)
    print(result.stdout, flush=True)
    print("Traceroute exit code:", result.returncode, flush=True)
    
    if result.stderr:
        print(
            "Traceroute stderr:",
            result.stderr,
            flush=True,
        )

    output = result.stdout

    hops = []

    for line in output.splitlines():
        hop_match = re.match(r"^\s*(\d+)\s+(.*)$", line)
    
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

def send_to_server(hops, location):
    payload = {
        "client_id": CLIENT_ID,

        "client_ip": location["ip"],

        "latitude": location["latitude"],
        "longitude": location["longitude"],

        "country": location["country"],
        "country_code": location["country_code"],
        "region": location["region"],
        "city": location["city"],
        "timezone": location["timezone"],

        "target": TARGET,

        "timestamp": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(),
        ),

        "hops": hops,
    }

    print()
    print("Sending measurement...", flush=True)

    response = requests.post(
        SERVER + "/measurement",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )

    print(
        "Server HTTP status:",
        response.status_code,
        flush=True,
    )

    response.raise_for_status()

    return response.json()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one measurement and exit",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Traceroute measurement client")
    print("=" * 60)

    

    print()
    print("Detecting runner location...", flush=True)

    location = get_location()

    print()
    print("Runner information:")
    print("  Public IP :", location["ip"])
    print("  Country   :", location["country"])
    print("  Region    :", location["region"])
    print("  City      :", location["city"])
    print("  Latitude  :", location["latitude"])
    print("  Longitude :", location["longitude"])
    print("  Timezone  :", location["timezone"])

   

    hops = traceroute(TARGET)

    print()
    print(
        f"Traceroute finished. Hops found: {len(hops)}",
        flush=True,
    )

    response = send_to_server(
        hops,
        location,
    )

    print()
    print("Server response:")

    print(
        json.dumps(
            response,
            indent=2,
            ensure_ascii=False,
        )
    )

    print()
    print("Measurement completed successfully.")


if __name__ == "__main__":
    print("test")
    main()

"""Explicit local connectivity diagnostic; prints no report data."""
import argparse
import json
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:1234")
args = parser.parse_args()
url = args.url.rstrip("/") + "/v1/models"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with opener.open(url, timeout=10) as response:
        data = json.load(response)
    print(json.dumps({"reachable": True, "models": [m["id"] for m in data.get("data", [])]}, indent=2))
except (urllib.error.URLError, TimeoutError, OSError) as exc:
    print(json.dumps({"reachable": False, "error": str(exc), "checks": [
        "Enable LM Studio local-network serving", "Confirm the Mac IP and port from this server",
        "Allow this workstation through the Mac firewall", "Confirm both machines share a routable local network"]}, indent=2))
    raise SystemExit(1)


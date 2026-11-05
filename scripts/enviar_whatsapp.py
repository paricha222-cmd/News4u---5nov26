#!/usr/bin/env python3
"""Send News4U via approved Meta WhatsApp Cloud API template.

Required GitHub Actions secrets:
WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_RECIPIENT
Optional variables: WHATSAPP_TEMPLATE_NAME (default news4u_diario),
WHATSAPP_TEMPLATE_LANGUAGE (default pt_BR), NEWS4U_PUBLIC_URL.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

def main():
    required = ("WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_RECIPIENT")
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print("WhatsApp not configured. Missing secrets: " + ", ".join(missing))
        return 0  # Keep website publishing functional until credentials are supplied.
    url = os.environ.get("NEWS4U_PUBLIC_URL", "https://news4u-5nov26.onrender.com").rstrip("/")
    date = dt.datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")
    # Wait for Render to serve the current edition, not yesterday's edition.
    ready = False
    for attempt in range(18):
        try:
            req = urllib.request.Request(url + "/?check=" + str(int(time.time())), headers={"User-Agent":"News4U/1.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                page = response.read().decode("utf-8", errors="replace")
            if "News4U" in page and date in page:
                ready = True
                break
        except Exception as exc:
            print("Waiting for publication:", str(exc))
        time.sleep(20)
    if not ready:
        print("Render has not published today's edition. WhatsApp not sent.")
        return 1
    payload = {
        "messaging_product": "whatsapp",
        "to": os.environ["WHATSAPP_RECIPIENT"],
        "type": "template",
        "template": {
            "name": os.environ.get("WHATSAPP_TEMPLATE_NAME", "news4u_diario"),
            "language": {"code": os.environ.get("WHATSAPP_TEMPLATE_LANGUAGE", "pt_BR")},
            "components": [{"type":"body","parameters":[
                {"type":"text","text":date},
                {"type":"text","text":url}
            ]}]
        }
    }
    api_version = os.environ.get("WHATSAPP_GRAPH_VERSION", "v23.0")
    endpoint = f"https://graph.facebook.com/{api_version}/{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/messages"
    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers={
        "Authorization": "Bearer " + os.environ["WHATSAPP_TOKEN"],
        "Content-Type": "application/json"
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.load(response)
        print("WhatsApp accepted message request; message id:", result.get("messages", [{}])[0].get("id", "unknown"))
        return 0
    except urllib.error.HTTPError as exc:
        print("WhatsApp API rejected request:", exc.code, exc.read().decode("utf-8", errors="replace")[:1200])
        return 1

if __name__ == "__main__":
    sys.exit(main())

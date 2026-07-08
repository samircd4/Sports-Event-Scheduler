"""
http_client.py — Shared requests Session for all API calls.

Cloudflare blocks datacenter IPs (VPS / Docker) at the TLS layer.
Setting PROXY_URL in .env routes all traffic through a proxy
(e.g. an SSH SOCKS5 tunnel from the VPS back to your local machine).

How to set up an SSH SOCKS5 tunnel on your VPS:
  ssh -D 1080 -N -f user@your-local-or-residential-ip

Then in .env on the VPS:
  PROXY_URL=socks5h://127.0.0.1:1080

If PROXY_URL is not set, requests go out directly (works on local machines).
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

_PROXY_URL = os.getenv("PROXY_URL", "").strip()

# Shared session — reused across all API calls for connection pooling
session = requests.Session()

if _PROXY_URL:
    session.proxies = {
        "http":  _PROXY_URL,
        "https": _PROXY_URL,
    }

# Common browser-like headers — set once on the session
session.headers.update({
    "accept":            "application/json, text/plain, */*",
    "accept-language":   "en-US,en;q=0.9,bn;q=0.8",
    "authorization":     os.getenv("AUTHORIZATION_KEY", ""),
    "origin":            "https://app.pikkit.com",
    "priority":          "u=1, i",
    "referer":           "https://app.pikkit.com/",
    "sec-ch-ua":         '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile":  "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest":    "empty",
    "sec-fetch-mode":    "cors",
    "sec-fetch-site":    "cross-site",
    "user-agent":        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
})

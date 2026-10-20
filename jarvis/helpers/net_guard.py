"""
JARVIS SSRF-Guarded Outbound Fetcher & Media/Page Proxy Gateway

Protects against Server-Side Request Forgery (SSRF) and DNS Rebinding:
- Refuses internal, loopback, private, link-local, carrier-grade NAT, and cloud metadata IPs
- Resolves DNS ahead of time, refusing the name if ANY answer resolves to a forbidden range
- Connects directly to the pre-vetted IP with SNI + Host headers to eliminate DNS rebinding windows
- Follows redirects manually (up to MAX_REDIRECTS) re-vetting every hop
- Streams bytes with running byte caps to avoid memory exhaustion
"""
import re
import socket
import asyncio
import ipaddress
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple, AsyncIterator
import httpx

MAX_REDIRECTS = 4
PROXY_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

MAX_IMG_BYTES = 15 * 1024 * 1024       # 15 MB
MAX_MEDIA_BYTES = 200 * 1024 * 1024   # 200 MB
MAX_PAGE_BYTES = 8 * 1024 * 1024       # 8 MB

IMG_TIMEOUT_S = 10.0
MEDIA_TIMEOUT_S = 30.0
PAGE_TIMEOUT_S = 15.0

# Hostnames refused before DNS lookup
BLOCKED_HOSTNAME = re.compile(r"(^|\.)(localhost|local|internal|intranet|home\.arpa)$", re.IGNORECASE)

class ProxyError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message

def is_blocked_ip(ip_str: str) -> bool:
    """
    Evaluates whether an IP address is private, loopback, link-local, CGNAT,
    cloud metadata, multicast, or unspecified.
    Unwraps IPv4-mapped IPv6 literals (e.g. ::ffff:127.0.0.1, ::ffff:7f00:1).
    """
    clean = str(ip_str or "").strip("[]").split("%")[0].lower()
    if clean.startswith("::ffff:"):
        mapped = clean[7:]
        if "." in mapped:
            clean = mapped
        else:
            hex_parts = mapped.split(":")
            if len(hex_parts) == 2:
                try:
                    h, l = int(hex_parts[0], 16), int(hex_parts[1], 16)
                    clean = f"{h >> 8}.{h & 0xff}.{l >> 8}.{l & 0xff}"
                except ValueError:
                    return True

    try:
        ip = ipaddress.ip_address(clean)
    except ValueError:
        return True

    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True

    if isinstance(ip, ipaddress.IPv4Address):
        # 100.64.0.0/10 Carrier-Grade NAT (and Tailscale)
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return True
        # 192.0.0.0/24 Protocol Assignments
        if ip in ipaddress.ip_network("192.0.0.0/24"):
            return True
        # 198.18.0.0/15 Benchmarking
        if ip in ipaddress.ip_network("198.18.0.0/15"):
            return True

    return False

def vet_target_url(raw_url: str) -> urllib.parse.ParseResult:
    """
    Validates URL scheme, hostname, and blocks dangerous targets.
    """
    try:
        parsed = urllib.parse.urlparse(str(raw_url or "").strip())
    except Exception:
        raise ProxyError(400, "Invalid URL format")

    if parsed.scheme.lower() not in ("http", "https"):
        raise ProxyError(400, "Absolute http(s) URL required")

    hostname = parsed.hostname
    if not hostname:
        raise ProxyError(400, "Missing hostname in target URL")

    if BLOCKED_HOSTNAME.search(hostname):
        raise ProxyError(403, f"Blocked host: {hostname}")

    # Check if literal IP
    clean_host = hostname.strip("[]")
    try:
        ipaddress.ip_address(clean_host)
        if is_blocked_ip(clean_host):
            raise ProxyError(403, f"Blocked IP target: {clean_host}")
    except ValueError:
        pass  # Hostname is a domain name

    return parsed

async def guarded_resolve_dns(hostname: str, port: int) -> str:
    """
    Resolves hostname via socket.getaddrinfo. Refuses connection if ANY
    resolved IP is in a forbidden range, preventing DNS rebinding.
    Returns the first verified IP.
    """
    loop = asyncio.get_running_loop()
    try:
        addr_info = await loop.run_in_executor(None, lambda: socket.getaddrinfo(hostname, port))
    except Exception as e:
        raise ProxyError(502, f"DNS resolution failed for {hostname}: {e}")

    if not addr_info:
        raise ProxyError(502, f"No DNS addresses found for {hostname}")

    first_ip = None
    for entry in addr_info:
        sockaddr = entry[4]
        ip = sockaddr[0]
        if is_blocked_ip(ip):
            raise ProxyError(403, f"Refusing {hostname}: resolves to forbidden address {ip}")
        if first_ip is None:
            first_ip = ip

    if not first_ip:
        raise ProxyError(502, f"Could not determine safe IP for {hostname}")

    return first_ip

async def open_remote_stream(
    target_url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout_s: float = 15.0,
    max_redirects: int = MAX_REDIRECTS
) -> Tuple[httpx.Response, httpx.AsyncClient]:
    """
    Executes an outbound HTTP request through the SSRF gate with DNS pinning
    and manual redirect loop.
    Returns (response, client). The caller MUST close the client or response.
    """
    current_url = target_url
    req_headers = dict(headers or {})
    if "user-agent" not in {k.lower() for k in req_headers}:
        req_headers["User-Agent"] = PROXY_UA

    client = httpx.AsyncClient(timeout=timeout_s, follow_redirects=False)

    for hop in range(max_redirects + 1):
        parsed = vet_target_url(current_url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        hostname = parsed.hostname or ""

        # Pre-resolve and vet DNS
        resolved_ip = await guarded_resolve_dns(hostname, port)

        # Build direct IP URL to avoid rebinding
        ip_formatted = f"[{resolved_ip}]" if ":" in resolved_ip else resolved_ip
        path_query = parsed.path or "/"
        if parsed.query:
            path_query += f"?{parsed.query}"

        connect_url = f"{parsed.scheme}://{ip_formatted}:{port}{path_query}"

        hop_headers = dict(req_headers)
        hop_headers["Host"] = hostname if (port in (80, 443)) else f"{hostname}:{port}"

        extensions = {}
        if parsed.scheme == "https":
            extensions["sni_hostname"] = hostname

        try:
            req = client.build_request("GET", connect_url, headers=hop_headers, extensions=extensions)
            resp = await client.send(req, stream=True)
        except Exception as e:
            await client.aclose()
            raise ProxyError(502, f"Upstream connection failed: {e}")

        # Check for redirects
        if 300 <= resp.status_code < 400 and "location" in resp.headers:
            await resp.aclose()
            if hop >= max_redirects:
                await client.aclose()
                raise ProxyError(502, "Too many redirects")

            loc = resp.headers["location"]
            current_url = urllib.parse.urljoin(current_url, loc)
            continue

        return resp, client

    await client.aclose()
    raise ProxyError(502, "Redirect limit exceeded")

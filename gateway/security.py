import ipaddress
import os
import socket
from urllib.parse import urlparse


def validate_upstream_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Server URL must be an HTTP(S) URL with a hostname")

    hostname = parsed.hostname.lower()
    allowed = {
        item.strip().lower()
        for item in os.getenv("MCP_ALLOWED_HOSTS", "").split(",")
        if item.strip()
    }
    if hostname in allowed:
        return url.strip()

    addresses = socket.getaddrinfo(hostname, parsed.port, type=socket.SOCK_STREAM)
    block_private = os.getenv("MCP_ALLOW_PRIVATE_RANGES", "false").lower() != "true"
    for address in {item[4][0] for item in addresses}:
        ip = ipaddress.ip_address(address)
        if ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Server URL resolves to a blocked address")
        if block_private and ip.is_private:
            raise ValueError("Private upstream ranges are disabled")
        if str(ip) == "169.254.169.254":
            raise ValueError("Cloud metadata address is blocked")
    return url.strip()

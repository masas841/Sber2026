import socket


def get_lan_ip() -> str:
    """Локальный IP для QR: предпочитаем 192.168.x / 10.x, не VPN."""
    candidates: list[str] = []

    try:
        import psutil

        for _iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family != socket.AF_INET:
                    continue
                ip = addr.address
                if ip.startswith("127.") or ip.startswith("169.254."):
                    continue
                candidates.append(ip)
    except ImportError:
        pass

  # fallback через UDP
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            candidates.append(sock.getsockname()[0])
    except OSError:
        pass

    for ip in candidates:
        if ip.startswith("192.168.") or ip.startswith("10."):
            return ip

    for ip in candidates:
        if not ip.startswith("198.18.") and not ip.startswith("172.16."):
            return ip

    return candidates[0] if candidates else "127.0.0.1"

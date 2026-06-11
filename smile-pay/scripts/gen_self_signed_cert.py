"""Генерация самоподписанного TLS-сертификата для Smile Pay.

Запуск:
    python -m scripts.gen_self_signed_cert 192.168.1.243 slash.omelchak.com

Файлы: certs/cert.pem, certs/key.pem.
"""

from __future__ import annotations

import datetime
import ipaddress
import socket
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parent.parent
CERT_DIR = ROOT / "certs"


def _lan_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def build_san(extra: list[str]) -> tuple[list[x509.GeneralName], list[str]]:
    dns_names = ["localhost"]
    ip_addrs = ["127.0.0.1"]

    hostname = socket.gethostname()
    if hostname and hostname not in dns_names:
        dns_names.append(hostname)

    lan_ip = _lan_ip()
    if lan_ip and lan_ip not in ip_addrs:
        ip_addrs.append(lan_ip)

    for item in extra:
        try:
            ipaddress.ip_address(item)
        except ValueError:
            if item not in dns_names:
                dns_names.append(item)
        else:
            if item not in ip_addrs:
                ip_addrs.append(item)

    san: list[x509.GeneralName] = [x509.DNSName(name) for name in dns_names]
    san.extend(x509.IPAddress(ipaddress.ip_address(addr)) for addr in ip_addrs)
    return san, [*dns_names, *ip_addrs]


def main(argv: list[str]) -> int:
    san, summary = build_san(argv)
    common_name = next((item for item in argv if not _is_ip(item)), "slash.omelchak.com")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Smile Pay Kiosk"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    CERT_DIR.mkdir(parents=True, exist_ok=True)
    cert_path = CERT_DIR / "cert.pem"
    key_path = CERT_DIR / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    print(f"cert: {cert_path}")
    print(f"key:  {key_path}")
    print("SAN: " + ", ".join(summary))
    return 0


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

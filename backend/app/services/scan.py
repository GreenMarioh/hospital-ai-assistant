"""Virus-scan hook. Register scanners returning a threat name (or None if clean)."""

from collections.abc import Callable

EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

Scanner = Callable[[bytes], str | None]


def eicar_scanner(data: bytes) -> str | None:
    return "EICAR-Test-File" if EICAR in data else None


SCANNERS: list[Scanner] = [eicar_scanner]  # append a ClamAV client here in production


def scan(data: bytes) -> str | None:
    for scanner in SCANNERS:
        threat = scanner(data)
        if threat:
            return threat
    return None

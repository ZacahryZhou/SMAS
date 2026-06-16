from __future__ import annotations

import ssl
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import certifi
import requests

from config import settings


class DownloadError(RuntimeError):
    pass


def _verify_setting() -> bool | str:
    if settings.ssl_cert_file:
        return settings.ssl_cert_file
    return settings.ssl_verify


def download_file(url: str, output_path: Path, *, timeout: int = 120) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    verify = _verify_setting()

    try:
        response = requests.get(url, timeout=timeout, verify=verify)
        response.raise_for_status()
        output_path.write_bytes(response.content)
        return
    except requests.exceptions.SSLError as exc:
        last_error: Exception = exc
    except requests.RequestException as exc:
        last_error = exc

    # Fallback for environments where requests/certifi fails but system store works.
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        if verify is False:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        elif isinstance(verify, str):
            context = ssl.create_default_context(cafile=verify)

        request = Request(url, headers={"User-Agent": "SMAS/1.0"})
        with urlopen(request, timeout=timeout, context=context) as response:
            output_path.write_bytes(response.read())
        return
    except URLError as exc:
        raise DownloadError(
            "Failed to download generated image due to SSL/network error. "
            "On macOS, try running: /Applications/Python 3.*/Install Certificates.command. "
            "If you are on a school/corporate network, set SMAS_SSL_VERIFY=false in .env "
            "or point SSL_CERT_FILE to your network CA bundle. "
            f"Original error: {last_error}"
        ) from exc

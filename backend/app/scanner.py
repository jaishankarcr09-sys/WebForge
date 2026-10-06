from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup

@dataclass
class ScanResult:
    url: str
    status_code: int
    html_size: int
    soup: BeautifulSoup

def scan_url(url: str) -> ScanResult:
    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": "WebForgeBot/0.1"},
    )
    response.raise_for_status()
    return ScanResult(
        url=url,
        status_code=response.status_code,
        html_size=len(response.content),
        soup=BeautifulSoup(response.text, "html.parser"),
    )

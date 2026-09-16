"""Configuration settings for SIH Problem Statement Scraper."""

DEFAULT_SIH_URL = "https://sih.gov.in/sih2026PS"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://sih.gov.in/",
    "Connection": "keep-alive",
}

DEFAULT_TIMEOUT = 25  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 3  # seconds

# Mojibake correction map for common character encoding anomalies in SIH text
MOJIBAKE_FIX = {
    "\u00e2\u20ac\u201c": "-",  # en dash
    "\u00e2\u20ac\u201d": "-",  # em dash
    "\u00e2\u20ac\u2122": "'",  # right single quote
    "\u00e2\u20ac\u02dc": "'",  # left single quote
    "\u00e2\u20ac\u0153": '"',  # left double quote
    "\u00e2\u20ac\u0152": '"',  # right double quote
    "\u00e2\u20ac\u00a6": "...",  # ellipsis
    "\u00c2\u00b0": "°",  # degree sign
    "\u00c2\u00b5": "µ",  # micro sign
    "\u00c2\u00b7": "·",  # middle dot
    "\ufffd": "-",  # replacement character
}

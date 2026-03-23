from __future__ import annotations

from pathlib import Path

import httpx
from http.cookiejar import MozillaCookieJar
from rich import print
from rich.panel import Panel

url = "https://www.vwbedrijfswagens.nl/app/authproxy/login"

params = {
    "fag": "vwn-nl,vwag-weconnect",
    "scope-vwn-nl": "profile,carConfigurations,dealers,cars,vin",
    "scope-vwag-weconnect": "openid,mbb",
    "prompt-vwag-weconnect": "none",
    "redirectUrl": "https://www.vwbedrijfswagens.nl/nl/digitale-diensten-en-apps/myvolkswagen.html?---=%7B%22myvw%3Agarage%3Awe-connect-page%22%3A%22%2Fremote-trip-statistics%22%2C%22digitale-diensten-en-apps_myvolkswagen_featureAppSection%22%3A%22%2Fweconnect%2FWVWZZZ3CZLE019622%22%7D",
    "sessionTimeout": "43200",
}

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,nl;q=0.7",
    "priority": "u=0, i",
    "referer": "https://www.vwbedrijfswagens.nl/nl/digitale-diensten-en-apps/myvolkswagen.html?---=%7B%22myvw%3Agarage%3Awe-connect-page%22%3A%22%2Fremote-trip-statistics%22%2C%22digitale-diensten-en-apps_myvolkswagen_featureAppSection%22%3A%22%2Fweconnect%2FWVWZZZ3CZLE019622%22%7D",
    "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
}

COOKIE_FILE = Path("cookies.txt")


def main() -> None:
    jar = MozillaCookieJar(COOKIE_FILE.as_posix())

    if COOKIE_FILE.exists():
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except Exception:
            pass

    with httpx.Client(
        follow_redirects=True,
        cookies=jar,
        timeout=30.0,
    ) as client:
        response = client.get(url, headers=headers, params=params)
        jar.save(ignore_discard=True, ignore_expires=True)

    print("Status:", response.status_code)
    print("Final URL:", str(response.url))
    print("Redirect count:", len(response.history))

    if response.history:
        print("Redirect chain:")
        for previous in response.history:
            location = previous.headers.get("location", "")
            print(
                f"- {previous.status_code} [cyan]{previous.url}[/] -> [green]{location}[/]"
            )

    print("Saved cookies to:", COOKIE_FILE.resolve())
    print(Panel(response.text))


if __name__ == "__main__":
    main()

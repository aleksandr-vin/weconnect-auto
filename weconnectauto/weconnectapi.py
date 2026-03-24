from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import urljoin
from pathlib import Path
from typing import Any
import json
from uuid import uuid4

from bs4 import BeautifulSoup
import httpx
from http.cookiejar import MozillaCookieJar
from rich import print
import typer

from .models import (
    User,
    Relations,
    VehicleData,
    VehicleDetails,
    Packages,
    UserCaps,
    WarningLights,
    LastTripdata,
)


@dataclass
class FormField:
    tag: str
    name: str
    value: str = ""
    field_type: str = ""
    options: list[str] = field(default_factory=list)


@dataclass
class HtmlForm:
    action: str = ""
    method: str = "get"
    fields: list[FormField] = field(default_factory=list)


params = {
    "fag": "vwn-nl,vwag-weconnect",
    "scope-vwn-nl": "profile,carConfigurations,dealers,cars,vin",
    "scope-vwag-weconnect": "openid,mbb",
    "prompt-vwag-weconnect": "none",
    "redirectUrl": "https://www.vwbedrijfswagens.nl/nl/digitale-diensten-en-apps/myvolkswagen.html",
    "sessionTimeout": "43200",
}

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,nl;q=0.7",
    "priority": "u=0, i",
    "referer": "https://www.vwbedrijfswagens.nl/nl/digitale-diensten-en-apps/myvolkswagen.html",
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


def parse_first_form(html: str) -> HtmlForm | None:
    soup = BeautifulSoup(html, "html.parser")
    form_tag = soup.find("form")
    if form_tag is None:
        return None

    form = HtmlForm(
        action=form_tag.get("action", ""),
        method=(form_tag.get("method") or "get").lower(),
    )

    for input_tag in form_tag.find_all("input"):
        name = input_tag.get("name", "")
        if not name:
            continue
        form.fields.append(
            FormField(
                tag="input",
                name=name,
                value=input_tag.get("value", ""),
                field_type=(input_tag.get("type") or "text").lower(),
            )
        )

    return form


def summarize_form(form: HtmlForm) -> None:
    print("Form method:", form.method.upper())
    print("Form action:", form.action or "<current url>")
    print("Form fields:")
    for f in form.fields:
        suffix = f" options={f.options}" if f.options else ""
        field_type = f.field_type or f.tag
        print(f"- {f.name} ({field_type}) = {f.value!r}{suffix}")


def build_form_payload(form: HtmlForm) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    username = os.environ["VW_USERNAME"]
    password = os.environ["VW_PASSWORD"]

    username_assigned = False
    password_assigned = False

    for f in form.fields:
        if f.tag not in {"input", "textarea", "select"}:
            continue

        if f.field_type in {"submit", "button", "image", "file", "reset"}:
            continue

        lower_name = f.name.lower()
        value = f.value

        if not username_assigned and any(
            token in lower_name for token in ("email", "user", "login", "identifier")
        ):
            value = username
            username_assigned = True
        elif not password_assigned and "pass" in lower_name:
            value = password
            password_assigned = True
        elif f.field_type in {"checkbox", "radio"} and not value:
            value = "on"

        payload[f.name] = value

    if not username_assigned:
        raise RuntimeError("Could not find a username/email field in the HTML form")
    if not password_assigned:
        raise RuntimeError("Could not find a password field in the HTML form")

    return payload


def format_bytes(n: int) -> str:
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PiB"


class WeConnectAPI:
    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = "https://www.vwbedrijfswagens.nl/",
        cookie_file: str = "cookies.txt",
        state_file: str = "state.json",
        last_response_file: str | None = None,
        verbose: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.jar = MozillaCookieJar(Path(cookie_file).as_posix())
        self.state_file = state_file
        self.last_response_file = last_response_file
        self._state = {}
        self.verbose = verbose

        if Path(cookie_file).exists():
            try:
                self.jar.load(ignore_discard=True, ignore_expires=True)
            except Exception:
                pass

        self._client = httpx.AsyncClient(
            follow_redirects=True,
            cookies=self.jar,
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "WeConnectAPI":
        await self.load_state()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def load_state(self):
        if Path(self.state_file).exists():
            with Path(self.state_file).open(mode="rt") as f:
                self._state = json.load(f)
                if self.verbose:
                    print("State loaded")

    async def save_state(self):
        with Path(self.state_file).open(mode="wt") as f:
            json.dump(self._state, f)
            if self.verbose:
                print("State saved")

    async def login(self):
        response = await self._client.get(
            "/app/authproxy/login",
            headers=headers,
            params=params,
        )
        if self.verbose:
            await self.dump_response_info(response)
        self.jar.save(ignore_discard=True, ignore_expires=True)

        if response.url.path.endswith("/login"):
            if self.verbose:
                print("[bold]Parsing the login form[/]")

            form = parse_first_form(response.text)
            if form is None:
                raise RuntimeError("No HTML form found in response.text")

            if self.verbose:
                summarize_form(form)

            form_url = urljoin(str(response.url), form.action or str(response.url))
            payload = build_form_payload(form)

            if self.verbose:
                print("POST URL:", form_url)
                print("POST payload:")
                for key, value in payload.items():
                    masked = "********" if "pass" in key.lower() else value
                    print(f"- {key} = {masked!r}")

            post_headers = dict(headers)
            post_headers["referer"] = str(response.url)

            if self.verbose:
                print("[bold]Sending login form[/]")

            method = form.method.lower() or "post"
            if method == "post":
                response = await self._client.post(
                    form_url, headers=post_headers, data=payload
                )
            else:
                response = await self._client.get(
                    form_url, headers=post_headers, params=payload
                )

            if self.verbose:
                await self.dump_response_info(response)

            self.jar.save(ignore_discard=True, ignore_expires=True)

        if self.last_response_file:
            with Path(self.last_response_file).open(mode="wt") as f:
                f.write(response.text)

        self._state["referer"] = str(response.url)

        await self.save_state()

    async def make_headers(self):
        post_headers = dict(headers)
        post_headers["referer"] = self._state["referer"]

        # Extract CSRF token from cookies
        csrf_token = None
        csrf_cookie_names = {
            "csrf_token",
            "csrf-token",
            "xsrf-token",
            "x-csrf-token",
            "csrftoken",
            "_csrf",
        }

        for c in self.jar:
            if c.name.lower() in csrf_cookie_names:
                csrf_token = c.value
                break

        # Add header if found
        if csrf_token:
            post_headers["X-CSRF-TOKEN"] = csrf_token
            if self.verbose:
                print(f"Using CSRF token: {csrf_token[:12]}...")
        else:
            raise RuntimeError("No CSRF token found in cookies")

        return post_headers

    async def dump_response_info(self, response):
        print(
            f"[{len(response.history)} redirects] {response.status_code} for final URL:",
            str(response.url),
        )

        if response.history:
            print("Redirect chain:")
            for previous in response.history:
                location = previous.headers.get("location", "")
                print(
                    f"- {previous.status_code} [cyan]{previous.url}[/] -> [green]{location}[/]"
                )

    async def get_user(self):
        if self.verbose:
            print("[bold]Getting user info[/]")
        headers = await self.make_headers()
        response = await self._client.get(
            "/app/authproxy/vwn-nl/user",
            headers=headers,
        )
        if self.verbose:
            await self.dump_response_info(response)
        response.raise_for_status()
        o = User.model_validate_json(response.text)
        return o

    async def get_users_me_relations(self):
        if self.verbose:
            print("[bold]Getting users me relations[/]")
        headers = await self.make_headers()
        response = await self._client.get(
            "/app/authproxy/vwn-nl/proxy/v2/users/me/relations",
            headers={
                **headers,
                "traceId": str(uuid4()),
            },
            params={"resourceHost": "myvw-vum-prod"},
        )
        if self.verbose:
            await self.dump_response_info(response)
        response.raise_for_status()
        o = Relations.model_validate_json(response.text)
        return o

    async def get_vehicle_data(self, vin: str):
        if self.verbose:
            print(f"[bold]Getting vehicle {vin} details[/]")
        headers = await self.make_headers()
        response = await self._client.get(
            f"/app/authproxy/vwn-nl/proxy/vehicles/{vin}/data/en-EN",
            headers=headers,
            params={"resourceHost": "cwat-group-vehicle-file-service-prod"},
        )
        if self.verbose:
            await self.dump_response_info(response)
        response.raise_for_status()
        o = VehicleData.model_validate_json(response.text)
        return o

    async def get_vehicle_details(self, vin: str):
        if self.verbose:
            print(f"[bold]Getting vehicle {vin} details[/]")
        headers = await self.make_headers()
        response = await self._client.get(
            f"/app/authproxy/vwn-nl/proxy/vehicles/{vin}/details/en-EN",
            headers=headers,
            params={"resourceHost": "cwat-group-vehicle-file-service-prod"},
        )
        if self.verbose:
            await self.dump_response_info(response)
        response.raise_for_status()
        o = VehicleDetails.model_validate_json(response.text)
        return o

    async def get_packages(self, vin: str):
        if self.verbose:
            print(f"[bold]Getting vehicle {vin} packages[/]")
        headers = await self.make_headers()
        response = await self._client.get(
            f"https://www.vwbedrijfswagens.nl/app/authproxy/vwn-nl/proxy/packages/{vin}",
            headers=headers,
            params={"resourceHost": "cwat-vw-navigation-map-update-service-prod"},
        )
        if self.verbose:
            await self.dump_response_info(response)
        response.raise_for_status()
        o = Packages.model_validate_json(response.text)
        return o

    async def download_file(self, link: str):
        if self.verbose:
            print(f"[bold]Downloading package from {link}[/]")
        headers = await self.make_headers()
        filename = Path(link).name
        with open(filename, "wb") as f:
            async with self._client.stream("GET", link, headers=headers) as response:
                response.raise_for_status()
                if self.verbose:
                    await self.dump_response_info(response)
                content_length = int(response.headers["content-length"])
                with typer.progressbar(
                    length=content_length, label="Downloading"
                ) as progress:
                    downloaded = 0
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress.update(len(chunk))
                            progress.label = f"{format_bytes(downloaded)} / {format_bytes(content_length)}"

        if self.verbose:
            print(f"[bold]Downloaded package to {filename}[/]")

    async def get_user_caps(self, vin: str):
        if self.verbose:
            print(f"[bold]Getting vehicle {vin} user capabilities[/]")
        headers = await self.make_headers()
        response = await self._client.get(
            f"/app/authproxy/vwag-weconnect/proxy/vehicles/{vin}/usercapabilities",
            # f"/app/authproxy/vwn-nl/proxy/vehicles/{vin}/usercapabilities",
            headers={
                **headers,
                "User-Id": "__userId__",
                "data": "{}",
            },
            params={
                "gdc": "myvw-mbb-prod",
                "resourceHost": "myvw-vcf-prod",
            },
        )
        if self.verbose:
            await self.dump_response_info(response)
        response.raise_for_status()
        o = UserCaps.model_validate_json(response.text)
        return o

    async def get_last_warning_lights(self, vin: str):
        # TODO: Not working -- 400
        if self.verbose:
            print(f"[bold]Getting vehicle {vin} last warning lights[/]")
        headers = await self.make_headers()
        response = await self._client.get(
            f"/app/authproxy/vwag-weconnect/proxy/vehicles/{vin}/warninglights/last",
            # f"/app/authproxy/vwn-nl/proxy/vehicles/{vin}/warninglights/last",
            headers={
                **headers,
                "User-Id": "__userId__",
                "Accept-Language": "nl-NL",
            },
            params={
                "gdc": "myvw-mbb-prod",
                "resourceHost": "myvw-vcf-prod",
            },
        )
        if self.verbose:
            await self.dump_response_info(response)

        print(response.text)
        response.raise_for_status()
        o = WarningLights.model_validate_json(response.text)
        return o

    async def get_last_cyclic_tripdata(self, vin: str):
        if self.verbose:
            print(f"[bold]Getting vehicle {vin} last warning lights[/]")
        headers = await self.make_headers()
        response = await self._client.get(
            f"/app/authproxy/vwn-nl/proxy/vehicles/{vin}/tripdata/cyclic/last",
            headers={
                **headers,
                "User-Id": "__userId__",
            },
            params={
                "gdc": "myvw-mbb-prod",
                "resourceHost": "myvw-vcf-prod",
            },
        )
        if self.verbose:
            await self.dump_response_info(response)
        response.raise_for_status()
        o = LastTripdata.model_validate_json(response.text)
        return o

    async def get_last_longterm_tripdata(self, vin: str):
        if self.verbose:
            print(f"[bold]Getting vehicle {vin} last warning lights[/]")
        headers = await self.make_headers()
        response = await self._client.get(
            f"/app/authproxy/vwn-nl/proxy/vehicles/{vin}/tripdata/longterm/last",
            headers={
                **headers,
                "User-Id": "__userId__",
            },
            params={
                "gdc": "myvw-mbb-prod",
                "resourceHost": "myvw-vcf-prod",
            },
        )
        if self.verbose:
            await self.dump_response_info(response)
        response.raise_for_status()
        o = LastTripdata.model_validate_json(response.text)
        return o

    async def get_last_shortterm_tripdata(self, vin: str):
        if self.verbose:
            print(f"[bold]Getting vehicle {vin} last warning lights[/]")
        headers = await self.make_headers()
        response = await self._client.get(
            f"/app/authproxy/vwn-nl/proxy/vehicles/{vin}/tripdata/shortterm/last",
            headers={
                **headers,
                "User-Id": "__userId__",
            },
            params={
                "gdc": "myvw-mbb-prod",
                "resourceHost": "myvw-vcf-prod",
            },
        )
        if self.verbose:
            await self.dump_response_info(response)
        response.raise_for_status()
        o = LastTripdata.model_validate_json(response.text)
        return o

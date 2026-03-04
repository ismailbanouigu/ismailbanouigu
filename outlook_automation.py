#!/usr/bin/env python3
"""CLI helper to prepare a unique Outlook username and strong password.

Flow:
1) Try <first><last>@outlook.com
2) If already used, fetch fallback names from Fantasy Name Generators by country
3) Keep checking availability until a free username is found
4) Generate a secure password (8-12 chars)
"""

from __future__ import annotations

import argparse
import json
import random
import re
import secrets
import string
from http.cookiejar import CookieJar
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import List

LOOKUP_URL = "https://account.live.com/GetCredentialType.srf"
FANTASY_BASE = "https://www.fantasynamegenerators.com/{slug}-names.php"
DEFAULT_SIGNUP_URL = (
    "https://signup.live.com/signup?mkt=FR-FR&uiflavor=web&fl=dob%2cflname%2cwld"
)


class _FantasyResultParser(HTMLParser):
    """Extract names from the #result section in fantasynamegenerators pages."""

    def __init__(self) -> None:
        super().__init__()
        self.in_result = False
        self.buffer: List[str] = []
        self.names: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_dict = dict(attrs)
        if tag == "div" and attrs_dict.get("id") == "result":
            self.in_result = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self.in_result:
            self.in_result = False
        if tag == "a" and self.in_result and self.buffer:
            text = "".join(self.buffer).strip()
            self.buffer.clear()
            if text and text.lower() != "more names":
                self.names.append(text)

    def handle_data(self, data: str) -> None:
        if self.in_result:
            self.buffer.append(data)


def slugify_country(country: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", country.strip().lower()).strip("-")


def normalize_for_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def check_outlook_exists(email: str, timeout: int = 20) -> bool:
    """Return True if account appears to exist, False if not found/available."""
    payload = {
        "username": email,
        "uaid": "",  # optional for this endpoint
        "isOtherIdpSupported": True,
        "checkPhones": False,
        "isRemoteNGCSupported": True,
        "isCookieBannerShown": False,
        "isFidoSupported": True,
        "forceotclogin": False,
        "isExternalFederationDisallowed": False,
        "isRemoteConnectSupported": False,
        "federationFlags": 0,
        "isSignup": False,
        "flowToken": "",
    }
    request = urllib.request.Request(
        LOOKUP_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not contact Microsoft lookup endpoint: {exc}") from exc

    data = json.loads(body)
    # IfExistsResult values commonly seen:
    # 0 = account does not exist (available), 1/5/6 = exists or managed
    return int(data.get("IfExistsResult", 1)) != 0


def _extract_query_param(url: str, key: str, fallback: str = "") -> str:
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    return params.get(key, [fallback])[0]


def check_outlook_exists_via_signup(email: str, signup_url: str, timeout: int = 20) -> bool:
    """Check username existence by first opening signup.live.com then calling GetCredentialType.

    This mirrors the account-creation flow more closely than a standalone lookup call.
    """
    uaid = _extract_query_param(signup_url, "uaid", "")

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    opener.addheaders = [("User-Agent", "Mozilla/5.0")]

    try:
        opener.open(signup_url, timeout=timeout).read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not open signup page: {exc}") from exc

    payload = {
        "username": email,
        "uaid": uaid,
        "isOtherIdpSupported": True,
        "checkPhones": False,
        "isRemoteNGCSupported": True,
        "isCookieBannerShown": False,
        "isFidoSupported": True,
        "forceotclogin": False,
        "isExternalFederationDisallowed": False,
        "isRemoteConnectSupported": False,
        "federationFlags": 0,
        "isSignup": True,
        "flowToken": "",
    }
    request = urllib.request.Request(
        LOOKUP_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Referer": signup_url},
        method="POST",
    )

    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not contact Microsoft signup lookup endpoint: {exc}") from exc

    data = json.loads(body)
    return int(data.get("IfExistsResult", 1)) != 0


def fetch_fantasy_names(country: str, limit: int = 20, timeout: int = 20) -> List[str]:
    slug = slugify_country(country)
    if not slug:
        return []

    url = FANTASY_BASE.format(slug=urllib.parse.quote(slug))
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except urllib.error.URLError:
        return []

    parser = _FantasyResultParser()
    parser.feed(html)

    deduped = []
    seen = set()
    for raw in parser.names:
        base = normalize_for_alias(raw)
        if base and base not in seen:
            seen.add(base)
            deduped.append(base)
        if len(deduped) >= limit:
            break
    return deduped


def generate_password(min_len: int = 8, max_len: int = 12) -> str:
    if min_len < 8 or max_len > 64 or min_len > max_len:
        raise ValueError("Invalid password length bounds")

    length = random.randint(min_len, max_len)
    pools = {
        "lower": string.ascii_lowercase,
        "upper": string.ascii_uppercase,
        "digit": string.digits,
        "symbol": "!@#$%^&*",
    }

    password_chars = [
        secrets.choice(pools["lower"]),
        secrets.choice(pools["upper"]),
        secrets.choice(pools["digit"]),
        secrets.choice(pools["symbol"]),
    ]
    all_chars = "".join(pools.values())
    password_chars.extend(secrets.choice(all_chars) for _ in range(length - len(password_chars)))
    random.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def pick_unique_alias(
    first: str,
    last: str,
    country: str,
    skip_check: bool = False,
    checker=None,
    signup_url: str = DEFAULT_SIGNUP_URL,
) -> tuple[str, List[str]]:
    attempts = []
    if checker is None:
        checker = check_outlook_exists

    primary = normalize_for_alias(first + last)
    if not primary:
        raise ValueError("First and last name did not contain usable letters/numbers")

    candidates = [primary]
    candidates.extend(fetch_fantasy_names(country))

    for candidate in candidates:
        email = f"{candidate}@outlook.com"
        if skip_check:
            attempts.append(f"{email} => SKIPPED (offline mode)")
            return candidate, attempts

        if checker is check_outlook_exists_via_signup:
            exists = checker(email, signup_url)
        else:
            exists = checker(email)
        attempts.append(f"{email} => {'TAKEN' if exists else 'AVAILABLE'}")
        if not exists:
            return candidate, attempts

    raise RuntimeError(
        "Could not find an available username from provided names. "
        "Try a different country or add manual suffixes."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate unique Outlook alias + password")
    parser.add_argument("first_name")
    parser.add_argument("last_name")
    parser.add_argument("country", help="Used for fantasy fallback names, e.g. 'japan'")
    parser.add_argument("--skip-availability-check", action="store_true",
                        help="Offline fallback: skip Microsoft uniqueness check")
    parser.add_argument(
        "--signup-url",
        default=DEFAULT_SIGNUP_URL,
        help="Signup URL to initialize Microsoft account-creation session",
    )
    parser.add_argument(
        "--use-signup-flow",
        action="store_true",
        help="Check availability using signup.live.com flow before credential lookup",
    )
    args = parser.parse_args()

    checker = check_outlook_exists_via_signup if args.use_signup_flow else check_outlook_exists

    alias, attempts = pick_unique_alias(
        args.first_name,
        args.last_name,
        args.country,
        skip_check=args.skip_availability_check,
        checker=checker,
        signup_url=args.signup_url,
    )
    password = generate_password(8, 12)

    print("Check log:")
    for line in attempts:
        print(f" - {line}")

    print("\nResult:")
    print(f"Username: {alias}@outlook.com")
    print(f"Password: {password}")


if __name__ == "__main__":
    main()

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
# ]
# ///
"""
Resolve a Blender version input to a download URL and a cache key.

Daily builds come from the builder's JSON API, which is not behind Cloudflare.
Releases come from download.blender.org, which is, and which sometimes refuses
GitHub's runners (403). Releases are then listed from official mirrors, and if
nothing answers, the newest cached build of the requested series is restored.
"""

import json
import os
import platform
import re
import sys

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RELEASE_HOSTS = [
    "https://download.blender.org/release/",
    "https://mirrors.ocf.berkeley.edu/blender/release/",
    "https://ftp.halifax.rwth-aachen.de/blender/release/",
]
DAILY_API = "https://builder.blender.org/download/daily/?format=json&v=1"
USER_AGENT = "setup-blender (+https://github.com/BradyAJohnston/setup-blender)"

# what Cloudflare serves instead of the page when it challenges a client
CLOUDFLARE_CHALLENGE = ("Just a moment", "cf_chl_opt", "challenge-platform")

# archives the install steps know how to unpack, by builder platform
DAILY_EXTENSIONS = {"linux": "xz", "darwin": "dmg", "windows": "zip"}
# builder (platform, architecture) -> suffix of the BLEND_URL_* variables
DAILY_TARGETS = {
    ("windows", "amd64"): "WINDOWS_X64",
    ("windows", "arm64"): "WINDOWS_ARM64",
    ("darwin", "x86_64"): "MACOS_X64",
    ("darwin", "arm64"): "MACOS_ARM64",
    ("linux", "x86_64"): "LINUX_X64",
}


class Unavailable(Exception):
    """A server could not be reached or refused us, after retries."""


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    retry = Retry(
        total=3,
        backoff_factor=2,  # 2, 4, 8 s
        # 403 included: Cloudflare's refusals of runners are often short-lived
        status_forcelist=(403, 429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


SESSION = make_session()


def fetch(url: str) -> str | None:
    """The page at url, None if it doesn't exist, raising Unavailable otherwise."""
    try:
        response = SESSION.get(url, timeout=30)
    except requests.RequestException as e:
        raise Unavailable(f"{url}: {e}") from e
    if response.status_code == 404:
        return None
    if any(marker in response.text for marker in CLOUDFLARE_CHALLENGE):
        raise Unavailable(f"{url}: Cloudflare challenge ({response.status_code})")
    if not response.ok:
        raise Unavailable(f"{url}: {response.status_code} {response.reason}")
    return response.text


def write_github_env(env_vars: dict) -> None:
    """Write environment variables to GITHUB_ENV or print them locally."""
    try:
        with open(os.environ["GITHUB_ENV"], "a") as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
                print(f"Set {key}={value}")
    except KeyError:
        print("Local environment detected, values:")
        for key, value in env_vars.items():
            print(f"{key}={value}")


def version_key(version: str) -> tuple:
    return tuple(int(n) for n in version.split("."))


def matches(version: str, requested: str) -> bool:
    """Whether a full version like 4.2.6 is in a requested 4.2, or is 4.2.6."""
    return version == requested or version.startswith(requested + ".")


# releases ---------------------------------------------------------------------


def fetch_release_page(path: str) -> tuple[str, str | None]:
    """
    The release listing at path from the first host that answers, and that host.

    The page is None if the host answered that it doesn't exist. Unavailable is
    raised only when no host answers at all.
    """
    errors = []
    for host in RELEASE_HOSTS:
        try:
            return host, fetch(host + path)
        except Unavailable as e:
            print(f"::warning::{e}")
            errors.append(str(e))
    raise Unavailable("no release host answered: " + "; ".join(errors))


def get_latest_release_base_version() -> str:
    """The highest released series, like '4.2'."""
    print("Fetching available Blender release versions...")
    host, page = fetch_release_page("")
    versions = sorted(
        set(re.findall(r'href="Blender(\d+\.\d+)/"', page or "")), key=version_key
    )
    if not versions:
        raise ValueError(f"No release versions found at {host}")
    print(f"Found {len(versions)} release versions: {', '.join(versions)}")
    return versions[-1]


def get_release_versions(base_version: str) -> tuple[str, list[str]]:
    """The host listing a series' releases, and the releases, oldest first."""
    print(f"Checking releases of {base_version}...")
    host, page = fetch_release_page(f"Blender{base_version}/")
    pattern = rf'href="blender-({re.escape(base_version)}\.\d+)-'
    versions = sorted(set(re.findall(pattern, page or "")), key=version_key)
    print(
        f"Found {len(versions)} releases of {base_version} at {host}: {', '.join(versions)}"
    )
    return host, versions


# daily builds -----------------------------------------------------------------


def get_daily_builds() -> list[dict]:
    """The daily builds the install steps can unpack, from the builder's JSON API."""
    print("Fetching daily builds...")
    page = fetch(DAILY_API)
    if page is None:
        raise Unavailable(f"{DAILY_API}: 404")
    builds = [
        build
        for build in json.loads(page)
        if (build["platform"], build["architecture"]) in DAILY_TARGETS
        and build["file_extension"] == DAILY_EXTENSIONS[build["platform"]]
    ]
    versions = sorted({build["version"] for build in builds}, key=version_key)
    print(f"Found {len(builds)} daily builds of {', '.join(versions)}")
    return builds


def get_runner_target() -> str:
    """The BLEND_URL_* suffix for the runner we're executing on."""
    arch = "ARM64" if platform.machine().lower() in ("arm64", "aarch64") else "X64"
    system = platform.system()
    if system == "Windows":
        return f"WINDOWS_{arch}"
    if system == "Darwin":
        return f"MACOS_{arch}"
    return "LINUX_X64"


def daily_env(builds: list[dict], full_version: str) -> dict:
    """
    The BLEND_URL_* of the newest build of full_version for each platform, and the
    cache key of the runner's.

    Every daily of a series reports the same version, so the cache is keyed on the
    build's commit hash as well, or it would keep restoring the first daily ever
    cached. Platforms aren't always built from the same commit, so each is keyed
    on the hash of its own build.
    """
    newest = {}
    for build in builds:
        if build["version"] != full_version:
            continue
        target = DAILY_TARGETS[(build["platform"], build["architecture"])]
        if target not in newest or build["file_mtime"] > newest[target]["file_mtime"]:
            newest[target] = build

    env_vars = {f"BLEND_URL_{target}": build["url"] for target, build in newest.items()}
    runner = newest.get(get_runner_target())
    if runner is None:
        print(
            f"No daily build of {full_version} for {get_runner_target()}, caching disabled"
        )
        env_vars["CACHE_VERSION"] = ""
    else:
        env_vars["CACHE_VERSION"] = f"{full_version}-{runner['hash']}"
    return env_vars


# resolving --------------------------------------------------------------------


def release_result(host: str, base_version: str, full_version: str) -> dict:
    return {
        "BLENDER_BASE_VERSION": base_version,
        "FULL_VERSION": full_version,
        "IS_DAILY": "false",
        "BLENDER_RELEASE_URL": host,
        # a release version identifies its download exactly
        "CACHE_VERSION": full_version,
    }


def daily_result(builds: list[dict], full_version: str) -> dict:
    return {
        "BLENDER_BASE_VERSION": ".".join(full_version.split(".")[:2]),
        "FULL_VERSION": full_version,
        "IS_DAILY": "true",
        **daily_env(builds, full_version),
    }


def newest_version(builds: list[dict]) -> str:
    return max((build["version"] for build in builds), key=version_key)


def resolve(version: str) -> dict:
    requested = version.strip()
    lower = requested.lower()

    if lower == "daily":
        builds = get_daily_builds()
        if not builds:
            raise ValueError(f"No daily builds found at {DAILY_API}")
        full_version = newest_version(builds)
        print(f"Using latest daily build: {full_version}")
        return daily_result(builds, full_version)

    if lower == "latest":
        base_version = get_latest_release_base_version()
        host, versions = get_release_versions(base_version)
        print(f"Using latest release: {versions[-1]}")
        return release_result(host, base_version, versions[-1])

    if not re.fullmatch(r"\d+\.\d+(\.\d+)?", requested):
        raise ValueError(
            f"Unrecognised version {version!r}, expected e.g. 4.2, 4.2.1, daily or latest"
        )
    base_version = ".".join(requested.split(".")[:2])

    # The builder is asked first: it is reliable, and a series it only has alpha
    # or beta builds of isn't released, which saves asking download.blender.org
    try:
        daily = [b for b in get_daily_builds() if matches(b["version"], requested)]
        daily_error = None
    except Unavailable as e:
        print(f"::warning::{e}")
        daily, daily_error = [], e
    if daily and all(b["release_cycle"] in ("alpha", "beta") for b in daily):
        full_version = newest_version(daily)
        print(f"{requested} has no release yet, using daily build: {full_version}")
        return daily_result(daily, full_version)

    host, versions = get_release_versions(base_version)
    released = [v for v in versions if matches(v, requested)]
    if released:
        print(f"Using release: {released[-1]}")
        return release_result(host, base_version, released[-1])
    if daily:
        full_version = newest_version(daily)
        print(f"{requested} is not released, using daily build: {full_version}")
        return daily_result(daily, full_version)
    if daily_error is not None:
        # it may well be a daily build, we just couldn't ask
        raise Unavailable(f"{requested} is not released, and {daily_error}")

    raise ValueError(
        f"Version {version} is neither a release at {host}Blender{base_version}/ "
        f"(found: {', '.join(versions) or 'none'}) nor a daily build at {DAILY_API}"
    )


def cache_fallback(version: str) -> str | None:
    """
    The cache key prefix to restore when the version can't be resolved: any
    cached build of the requested series, or of the exact version. None for daily
    and latest, which can't be told apart from other cached builds.
    """
    requested = version.strip()
    if re.fullmatch(r"\d+\.\d+", requested):
        return requested + "."
    if re.fullmatch(r"\d+\.\d+\.\d+", requested):
        return requested
    return None


def set_versions(version: str) -> dict:
    try:
        env_vars = resolve(version)
    except Unavailable as e:
        prefix = cache_fallback(version)
        if prefix is None:
            raise
        print(
            f"::warning::Could not resolve Blender {version}, restoring the newest "
            f"cached build of {prefix}* instead, if there is one. {e}"
        )
        env_vars = {
            "BLENDER_BASE_VERSION": ".".join(version.strip().split(".")[:2]),
            "FULL_VERSION": "",
            "IS_DAILY": "",
            "CACHE_VERSION": "",
            "CACHE_FALLBACK": prefix,
        }
    write_github_env(env_vars)
    return env_vars


def main():
    if len(sys.argv) != 2:
        print("Usage: python set_versions.py <version>")
        sys.exit(1)

    set_versions(sys.argv[1])


if __name__ == "__main__":
    main()

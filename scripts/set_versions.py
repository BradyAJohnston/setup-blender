# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "bs4",
#     "requests",
# ]
# ///
import os
import re
import sys
import requests
from bs4 import BeautifulSoup
from typing import Tuple, List


def fetch_url(url: str) -> BeautifulSoup:
    response = requests.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


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


def get_release_versions() -> List[str]:
    print("Fetching available Blender release versions...")
    soup = fetch_url("https://download.blender.org/release/")

    versions = {
        match.group(1)
        for link in soup.find_all("a", href=True)
        if (match := re.search(r"Blender(\d+\.\d+)", link["href"]))
    }

    sorted_versions = sorted(versions, key=lambda x: [int(n) for n in x.split(".")])
    print(
        f"Found {len(sorted_versions)} release versions: {', '.join(sorted_versions)}"
    )
    return sorted_versions


def get_latest_patch_version(base_version: str) -> str:
    print(f"Checking patch versions for {base_version}...")
    soup = fetch_url(f"https://download.blender.org/release/Blender{base_version}/")

    versions = {
        int(match.group(1))
        for link in soup.find_all("a", href=True)
        if (match := re.search(rf"blender-{base_version}\.(\d+)-", link["href"]))
    }

    latest_patch = max(versions) if versions else 0
    full_version = f"{base_version}.{latest_patch}"
    print(f"Found latest patch version: {full_version}")
    return full_version


def get_latest_builds(target_version: str = None) -> dict:
    print("Fetching latest daily builds...")
    soup = fetch_url("https://builder.blender.org/download/daily/")

    platform_links = {
        "windows": {"x64": [], "arm64": []},
        "macos": {"x64": [], "arm64": []},
        "linux": {"x64": []},
    }

    build_container = soup.find(id="builds-container")
    if not build_container:
        raise ValueError("Could not find builds container")

    for link in build_container.find_all("a", href=True):
        href = link["href"]
        if not href.endswith((".zip", ".dmg", ".tar.xz")):
            continue

        if target_version and not re.search(f"blender-{target_version}", href):
            continue

        if "windows" in href:
            target = "arm64" if "arm64" in href else "x64"
            platform_links["windows"][target].append(href)
        elif "darwin" in href:
            target = "arm64" if "arm64" in href else "x64"
            platform_links["macos"][target].append(href)
        elif "linux" in href:
            platform_links["linux"]["x64"].append(href)

    env_vars = {}
    for platform, archs in platform_links.items():
        for arch, links in archs.items():
            if links:
                latest = max(
                    links,
                    key=lambda x: re.search(r"blender-(\d+\.\d+\.\d+)", x).group(1),
                )
                env_name = f"BLEND_URL_{platform.upper()}_{arch.upper()}"
                env_vars[env_name] = latest

    return env_vars


def get_daily_versions() -> List[str]:
    print("Fetching available daily builds...")
    soup = fetch_url("https://builder.blender.org/download/")

    build_container = soup.find(id="builds-container")
    if not build_container:
        raise ValueError("Could not find builds container")

    versions = {
        match.group(1)
        for link in build_container.find_all("a", href=True)
        if (match := re.search(r"blender-(\d+\.\d+\.\d+)", link["href"]))
    }

    sorted_versions = sorted(versions, key=lambda x: [int(n) for n in x.split(".")])
    print(f"Found {len(sorted_versions)} daily versions: {', '.join(sorted_versions)}")
    return sorted_versions


def set_versions(version: str) -> Tuple[str, str, bool]:
    env_vars = {}
    checked_locations = []

    if version.lower() == "daily":
        available_versions = get_daily_versions()
        if not available_versions:
            raise ValueError(
                "No daily versions found at https://builder.blender.org/download/"
            )
        full_version = available_versions[-1]
        base_version = ".".join(full_version.split(".")[:2])
        print(f"Using latest daily build: {full_version}")
        is_daily = True
        target_version = full_version
    else:
        base_version = ".".join(version.split(".")[:2])
        available_versions = get_release_versions()
        checked_locations.append(
            f"Release versions at https://download.blender.org/release/"
        )

        if base_version in available_versions:
            full_version = (
                get_latest_patch_version(base_version)
                if re.match(r"^\d+\.\d+$", version)
                else version
            )
            is_daily = False
            target_version = None
        else:
            print(
                f"Version {base_version} not found in releases, checking daily builds..."
            )
            daily_versions = get_daily_versions()
            checked_locations.append(
                f"Daily builds at https://builder.blender.org/download/"
            )
            matching_versions = [v for v in daily_versions if v.startswith(version)]

            if not matching_versions:
                error_msg = (
                    f"Version {version} not found in any of the following locations:\n"
                )
                for loc in checked_locations:
                    error_msg += f"- {loc}\n"
                error_msg += "\nAvailable versions:\n"
                error_msg += f"- Release versions: {', '.join(available_versions)}\n"
                error_msg += f"- Daily versions: {', '.join(daily_versions)}"
                raise ValueError(error_msg)

            full_version = matching_versions[-1]
            print(f"Found version in daily builds: {full_version}")
            is_daily = True
            target_version = full_version

    env_vars.update(
        {
            "BLENDER_BASE_VERSION": base_version,
            "FULL_VERSION": full_version,
            "IS_DAILY": "true" if is_daily else "false",
        }
    )

    if is_daily:
        env_vars.update(get_latest_builds(target_version))

    write_github_env(env_vars)
    return base_version, full_version, is_daily


def main():
    if len(sys.argv) != 2:
        print("Usage: python set_versions.py <version>")
        sys.exit(1)

    version = sys.argv[1]
    set_versions(version)


if __name__ == "__main__":
    main()

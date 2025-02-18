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


def get_release_versions() -> List[str]:
    print("Fetching available Blender release versions...")
    soup = fetch_url("https://download.blender.org/release/")

    versions = {
        match.group(1)
        for link in soup.find_all("a", href=True)
        if (match := re.search(r"Blender(\d+\.\d+)", link["href"]))
    }

    sorted_versions = sorted(versions, key=lambda x: [int(n) for n in x.split(".")])
    print(f"Found {len(sorted_versions)} release versions")
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


def get_latest_builds() -> None:
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

        if "windows" in href:
            target = "arm64" if "arm64" in href else "x64"
            platform_links["windows"][target].append(href)
        elif "darwin" in href:
            target = "arm64" if "arm64" in href else "x64"
            platform_links["macos"][target].append(href)
        elif "linux" in href:
            platform_links["linux"]["x64"].append(href)

    try:
        with open(os.environ["GITHUB_ENV"], "a") as f:
            for platform, archs in platform_links.items():
                for arch, links in archs.items():
                    if links:
                        latest = max(
                            links,
                            key=lambda x: re.search(
                                r"blender-(\d+\.\d+\.\d+)", x
                            ).group(1),
                        )
                        env_name = f"BLEND_URL_{platform.upper()}_{arch.upper()}"
                        f.write(f"{env_name}={latest}\n")
                        print(f"Set {env_name}={latest}")
    except KeyError:
        print("Local environment detected, URLs:")
        for platform, archs in platform_links.items():
            for arch, links in archs.items():
                if links:
                    latest = max(
                        links,
                        key=lambda x: re.search(r"blender-(\d+\.\d+\.\d+)", x).group(1),
                    )
                    env_name = f"BLEND_URL_{platform.upper()}_{arch.upper()}"
                    print(f"{env_name}={latest}")


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

    sorted_versions = sorted(versions)
    print(f"Found {len(sorted_versions)} daily versions")
    return sorted_versions


def set_versions(version: str) -> Tuple[str, str, bool]:
    if version.lower() == "daily":
        available_versions = get_daily_versions()
        if not available_versions:
            raise ValueError("No daily versions found")
        full_version = available_versions[-1]
        base_version = ".".join(full_version.split(".")[:2])
        print(f"Using latest daily build: {full_version}")
        return base_version, full_version, True

    base_version = ".".join(version.split(".")[:2])
    available_versions = get_release_versions()

    if base_version in available_versions:
        full_version = (
            get_latest_patch_version(base_version)
            if re.match(r"^\d+\.\d+$", version)
            else version
        )
        is_daily = False
    else:
        print(f"Version {base_version} not found in releases, checking daily builds...")
        daily_versions = get_daily_versions()
        matching_versions = [v for v in daily_versions if v.startswith(base_version)]

        if not matching_versions:
            raise ValueError(
                f"Version {base_version} not found in releases or daily builds"
            )

        full_version = matching_versions[-1]
        print(f"Found version in daily builds: {full_version}")
        is_daily = True

    try:
        with open(os.environ["GITHUB_ENV"], "a") as f:
            f.write(f"BLENDER_BASE_VERSION={base_version}\n")
            f.write(f"FULL_VERSION={full_version}\n")
            f.write(f"IS_DAILY={'true' if is_daily else 'false'}\n")
        print("Environment variables set successfully")
    except KeyError:
        print("Local environment detected, values:")
        print(f"BLENDER_BASE_VERSION={base_version}")
        print(f"FULL_VERSION={full_version}")
        print(f"IS_DAILY={'true' if is_daily else 'false'}")

    if is_daily:
        get_latest_builds()

    return base_version, full_version, is_daily


def main():
    if len(sys.argv) != 2:
        print("Usage: python set_versions.py <version>")
        sys.exit(1)

    version = sys.argv[1]
    set_versions(version)
    if version.lower() == "daily":
        get_latest_builds()


if __name__ == "__main__":
    main()

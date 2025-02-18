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


def get_release_versions():
    print("Fetching available Blender release versions...")
    url = "https://download.blender.org/release/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    versions = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        match = re.search(r"Blender(\d+\.\d+)", href)
        if match:
            versions.add(match.group(1))

    sorted_versions = sorted(versions, key=lambda x: [int(n) for n in x.split(".")])
    print(f"Found {len(sorted_versions)} release versions")
    return sorted_versions


def get_latest_patch_version(base_version):
    print(f"Checking patch versions for {base_version}...")
    url = f"https://download.blender.org/release/Blender{base_version}/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    versions = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        match = re.search(f"blender-{base_version}\.(\d+)-", href)
        if match:
            versions.add(int(match.group(1)))

    latest_patch = max(versions) if versions else 0
    full_version = f"{base_version}.{latest_patch}"
    print(f"Found latest patch version: {full_version}")
    return full_version


def get_latest_builds():
    print("Fetching latest daily builds...")
    url = "https://builder.blender.org/download/daily/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    builds = {
        "windows": {"x64": None, "arm64": None},
        "macos": {"x64": None, "arm64": None},
        "linux": {"x64": None},
    }

    def get_version(href):
        match = re.search(r"blender-(\d+\.\d+\.\d+)", href)
        return match.group(1) if match else "0.0.0"

    platform_links = {
        "windows": {"x64": [], "arm64": []},
        "macos": {"x64": [], "arm64": []},
        "linux": {"x64": []},
    }

    build_container = soup.find(id="builds-container")
    for link in build_container.find_all("a", href=True):
        href = link["href"]
        if not href.endswith((".zip", ".dmg", ".tar.xz")):
            continue

        if "windows" in href:
            if "arm64" in href:
                platform_links["windows"]["arm64"].append(href)
            else:
                platform_links["windows"]["x64"].append(href)
        elif "darwin" in href:
            if "arm64" in href:
                platform_links["macos"]["arm64"].append(href)
            else:
                platform_links["macos"]["x64"].append(href)
        elif "linux" in href:
            platform_links["linux"]["x64"].append(href)

    try:
        with open(os.environ["GITHUB_ENV"], "a") as f:
            for platform in builds:
                for arch in builds[platform]:
                    if platform_links[platform][arch]:
                        latest = max(platform_links[platform][arch], key=get_version)
                        env_name = f"BLEND_URL_{platform.upper()}_{arch.upper()}"
                        f.write(f"{env_name}={latest}\n")
                        print(f"Set {env_name}")
    except KeyError:
        print("Running in local environment, displaying URLs:")
        for platform in builds:
            for arch in builds[platform]:
                if platform_links[platform][arch]:
                    latest = max(platform_links[platform][arch], key=get_version)
                    env_name = f"BLEND_URL_{platform.upper()}_{arch.upper()}"
                    print(f"{env_name}={latest}")

    return builds


def set_versions(version):
    if version.lower() == "daily":
        available_versions = get_daily_versions()
        full_version = available_versions[-1] if available_versions else "0.0.0"
        base_version = ".".join(full_version.split(".")[:2])
        print(f"Using latest daily build: {full_version}")
        return base_version, full_version, True

    base_version = ".".join(version.split(".")[:2])

    # First try release versions
    available_versions = get_release_versions()
    if base_version in available_versions:
        if re.match(r"^\d+\.\d+$", version):
            full_version = get_latest_patch_version(base_version)
        else:
            full_version = version
        is_daily = False
    else:
        # If not in releases, check daily builds
        print(f"Version {base_version} not found in releases, checking daily builds...")
        daily_versions = get_daily_versions()
        matching_versions = [v for v in daily_versions if v.startswith(base_version)]

        if matching_versions:
            full_version = matching_versions[-1]
            print(f"Found version in daily builds: {full_version}")
            is_daily = True
        else:
            print(f"Version {base_version} not found in releases or daily builds")
            sys.exit(1)

    try:
        with open(os.environ["GITHUB_ENV"], "a") as f:
            f.write(f"BLENDER_BASE_VERSION={base_version}\n")
            f.write(f"FULL_VERSION={full_version}\n")
            f.write(f"IS_DAILY={str(is_daily).lower()}\n")
        print("Environment variables set successfully")
    except KeyError:
        print("GITHUB_ENV not available, printing values instead:")
        print(f"BLENDER_BASE_VERSION={base_version}")
        print(f"FULL_VERSION={full_version}")
        print(f"IS_DAILY={str(is_daily).lower()}")

    if is_daily:
        get_latest_builds()

    return base_version, full_version, is_daily


def get_daily_versions():
    print("Fetching available daily builds...")
    url = "https://builder.blender.org/download/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    versions = set()
    build_container = soup.find(id="builds-container")
    for link in build_container.find_all("a", href=True):
        href = link["href"]
        match = re.search(r"blender-(\d+\.\d+\.\d+)", href)
        if match:
            versions.add(match.group(1))

    sorted_versions = sorted(versions)
    print(f"Found {len(sorted_versions)} daily versions")
    return sorted_versions


def main():
    if len(sys.argv) == 2:
        version = sys.argv[1]
        set_versions(version)
        if version.lower() == "daily":
            get_latest_builds()
    else:
        print("Usage: python set_versions.py <version>")
        sys.exit(1)


if __name__ == "__main__":
    main()

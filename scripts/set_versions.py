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


def get_available_versions():
    print("Fetching available Blender versions...")
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
    print(f"Found {len(sorted_versions)} versions")
    return sorted_versions


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

    print("Processing build URLs...")
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

    print("Writing build URLs to environment file...")
    with open(os.environ["GITHUB_ENV"], "a") as f:
        for platform in builds:
            for arch in builds[platform]:
                if platform_links[platform][arch]:
                    latest = max(platform_links[platform][arch], key=get_version)
                    env_name = f"BLEND_URL_{platform.upper()}_{arch.upper()}"
                    f.write(f"{env_name}={latest}\n")
                    print(f"Set {env_name}")
    return builds


def set_versions(version):
    base_version = ".".join(version.split(".")[:2])
    print(f"Processing version: {version}")
    print(f"Base version: {base_version}")

    if re.match(r"^\d+\.\d+$", version):
        available_versions = get_available_versions()
        matching_versions = [
            v for v in available_versions if v.startswith(base_version)
        ]
        full_version = matching_versions[-1] if matching_versions else f"{version}.0"
        print(f"Found latest patch version: {full_version}")
    else:
        full_version = version
        print(f"Using provided full version: {full_version}")

    # Try to write to GITHUB_ENV if available, otherwise just print
    try:
        with open(os.environ["GITHUB_ENV"], "a") as f:
            f.write(f"BLENDER_BASE_VERSION={base_version}\n")
            f.write(f"FULL_VERSION={full_version}\n")
        print("Environment variables set successfully")
    except (KeyError, IOError):
        print("GITHUB_ENV not available, printing values instead:")
        print(f"BLENDER_BASE_VERSION={base_version}")
        print(f"FULL_VERSION={full_version}")

    return base_version, full_version


def main():
    if len(sys.argv) == 2:
        version = sys.argv[1]
        set_versions(version)
        get_latest_builds()
    else:
        print("Usage: python combined_blender_setup.py <version>")
        sys.exit(1)


if __name__ == "__main__":
    main()

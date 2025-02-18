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


def set_versions(version):
    if version.lower() == "daily":
        available_versions = get_daily_versions()
        full_version = available_versions[-1] if available_versions else "0.0.0"
        base_version = ".".join(full_version.split(".")[:2])
    else:
        base_version = ".".join(version.split(".")[:2])
        if re.match(r"^\d+\.\d+$", version):
            full_version = get_latest_patch_version(base_version)
        else:
            full_version = version

    try:
        with open(os.environ["GITHUB_ENV"], "a") as f:
            f.write(f"BLENDER_BASE_VERSION={base_version}\n")
            f.write(f"FULL_VERSION={full_version}\n")
            f.write(f"IS_DAILY={'true' if version.lower() == 'daily' else 'false'}\n")
        print("Environment variables set successfully")
    except KeyError:
        print("GITHUB_ENV not available, printing values instead:")
        print(f"BLENDER_BASE_VERSION={base_version}")
        print(f"FULL_VERSION={full_version}")
        print(f"IS_DAILY={'true' if version.lower() == 'daily' else 'false'}")

    return base_version, full_version


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

import requests
from bs4 import BeautifulSoup
import json
import sys
import os
import re


def get_latest_builds():
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

    # Get latest version for each platform/arch and store in env
    with open(os.environ["GITHUB_ENV"], "a") as f:
        for platform in builds:
            for arch in builds[platform]:
                if platform_links[platform][arch]:
                    latest = max(platform_links[platform][arch], key=get_version)
                    env_name = f"BLEND_URL_{platform.upper()}_{arch.upper()}"
                    f.write(f"{env_name}={latest}\n")


if __name__ == "__main__":
    builds = get_latest_builds()
    print(json.dumps(builds))

from .Utilities import download_file, ua_header
from typing import TypedDict
import os
import requests

class ModrinthFile(TypedDict):
    url: str
    primary: bool

class ModrinthVersion(TypedDict):
    id: str
    game_versions: list[str]
    files: list[ModrinthFile]

def download_mod(destination_folder: str, platform: str, game_version: str, project: str, filename: str) -> ModrinthVersion:
    print(f"Downloading mod {project} for {platform} {game_version}")

    versions = requests.get(
        f"https://api.modrinth.com/v2/project/{project}/version?loaders={platform}",
        headers=ua_header,
    ).json()
    
    version = next((ver for ver in versions if game_version in ver["game_versions"]), None)
    if not version:
        raise Exception(f"No version found for {platform} {game_version}")

    url = version["files"][0]["url"]
    jar_path = os.path.join(destination_folder, filename)
    download_file(jar_path, url, version=version["id"])

    return version

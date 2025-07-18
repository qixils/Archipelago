import argparse
import json
import os
import sys
import re
import atexit
import shutil
from subprocess import Popen
from shutil import copyfile
from time import strftime
import logging
from typing import Optional, TypedDict, Literal

import requests

import Utils
from worlds.minecraft.downloader.Utilities import download_file
from worlds.minecraft.downloader.Java import download_jre
from worlds.minecraft.downloader.NeoForge import download_neoforge
from settings import get_settings

atexit.register(input, "Press enter to exit.")

# 1 or more digits followed by m or g, then optional b
max_heap_re = re.compile(r"^(\d+[mg])[b]?$", re.I)


class ModVersion(TypedDict):
    version: str
    channel: Literal["release", "beta"]
    data: int
    java: int
    minecraft: str
    url: str


def replace_apmc_files(forge_dir: str, apmc_file: str):
    """Create APData folder if needed; clean .apmc files from APData; copy given .apmc into directory."""
    if apmc_file is None:
        return
    apdata_dir = os.path.join(forge_dir, 'APData')
    copy_apmc = True
    if not os.path.isdir(apdata_dir):
        os.mkdir(apdata_dir)
        logging.info(f"Created APData folder in {forge_dir}")
    for entry in os.scandir(apdata_dir):
        if entry.name.endswith(".apmc") and entry.is_file():
            if not os.path.samefile(apmc_file, entry.path):
                os.remove(entry.path)
                logging.info(f"Removed {entry.name} in {apdata_dir}")
            else: # apmc already in apdata
                copy_apmc = False
    if copy_apmc:
        copyfile(apmc_file, os.path.join(apdata_dir, os.path.basename(apmc_file)))
        logging.info(f"Copied {os.path.basename(apmc_file)} to {apdata_dir}")


def read_apmc_file(apmc_file):
    from base64 import b64decode

    with open(apmc_file, 'r') as f:
        return json.loads(b64decode(f.read()))


def run_forge_server(forge_dir: str, run_args: list[str]) -> Popen:
    """Run the Forge server."""

    args = run_args + ["-nogui"]
    logging.info(f"Running Forge server: {args}")
    os.chdir(forge_dir)
    return Popen(args)


def get_minecraft_versions(version: Optional[int], release_channel: Optional[str]) -> ModVersion:
    version_file_endpoint = "https://raw.githubusercontent.com/qixils/NeoForgeAP/main/versions/minecraft_versions.json"
    resp = requests.get(version_file_endpoint)
    local = False
    if resp.status_code == 200:  # OK
        try:
            data: list[ModVersion] = resp.json()
        except requests.exceptions.JSONDecodeError:
            logging.warning(f"Unable to fetch version update file, using local version. (status code {resp.status_code}).")
            local = True
    else:
        logging.warning(f"Unable to fetch version update file, using local version. (status code {resp.status_code}).")
        local = True

    if local:
        with open(Utils.user_path("minecraft_versions.json"), 'r') as f:
            data = json.load(f)
    else:
        with open(Utils.user_path("minecraft_versions.json"), 'w') as f:
            json.dump(data, f)

    try:
        # Filter to compatible versions and release channels
        # If no release channel is specified we sort for the stable-est release channel available
        items = sorted(
            (item for item in data if (item["version"] == version or version is None) and
             (item["channel"] == release_channel or release_channel is None)),
            key=lambda x: (x["channel"] != "release", x["version"]),
            reverse=True
        )
        return next(items)
    except (StopIteration, KeyError):
        logging.error(f"No compatible mod version found for client version {version} on \"{release_channel}\" channel.")
        if release_channel != "release":
            logging.error("Consider switching \"release_channel\" to \"release\" in your Host.yaml file")
        else:
            logging.error("No suitable mod found on the \"release\" channel. Please Contact us on discord to report this error.")
        sys.exit(0)


if __name__ == '__main__':
    Utils.init_logging("MinecraftClient")
    parser = argparse.ArgumentParser()
    parser.add_argument("apmc_file", default=None, nargs='?', help="Path to an Archipelago Minecraft data file (.apmc)")
    parser.add_argument('--install', '-i', dest='install', default=False, action='store_true',
                        help="Download and install Java and the Forge server. Does not launch the client afterwards.")
    parser.add_argument('--release_channel', '-r', dest="channel", type=str, action='store',
                        help="Specify release channel to use.")
    parser.add_argument('--version', '-v', metavar='9', dest='data_version', type=int, action='store',
                        help="specify Mod data version to download.")

    args = parser.parse_args()
    apmc_file = os.path.abspath(args.apmc_file) if args.apmc_file else None

    # Change to executable's working directory
    os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))

    options = get_settings().minecraft_options
    channel = args.channel or options.release_channel
    apmc_data = None
    data_version = args.data_version or None

    if apmc_file is None and not args.install:
        apmc_file = Utils.open_filename('Select APMC file', (('APMC File', ('.apmc',)),))

    if apmc_file is not None and data_version is None:
        apmc_data = read_apmc_file(apmc_file)
        data_version = apmc_data.get('client_version', '')

    forge_dir = options.forge_directory
    max_heap = options.max_heap_size or "2G"

    max_heap_match = max_heap_re.match(max_heap)
    if not max_heap_re.match(max_heap):
        raise Exception(f"Max heap size {max_heap} in incorrect format. Use a number followed by M or G, e.g. 2G.")

    max_heap = max_heap_match.group(1)

    versions = get_minecraft_versions(data_version, channel)

    java_version = versions["java"]
    minecraft_version = versions["minecraft"]
    mod_url = versions["url"]
    mod_version = versions["version"]

    # Download JRE
    java_exe = download_jre(forge_dir, java_version)

    # Download NeoForge
    paths = download_neoforge(forge_dir, minecraft_version, max_heap)

    # Download mod
    mod_path = os.path.join(paths.mods_dir, "archipelago.jar")
    download_file(mod_path, mod_url, version=mod_version)

    if args.install:
        print(f"Installed server to {forge_dir}")
        sys.exit(0)

    if apmc_data is None:
        raise FileNotFoundError(f"APMC file does not exist or is inaccessible at the given location ({apmc_file})")

    replace_apmc_files(paths.root_dir, apmc_file)
    server_process = run_forge_server(paths.root_dir, paths.run_args)
    server_process.wait()

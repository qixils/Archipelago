from .Utilities import download_file, jre_paths, ua_header, write_eula
from .Modrinth import download_mod
from .Java import get_java_path
from . import ServerInstallData
from typing import TypedDict
import Utils
import os
import requests
import subprocess

class NeoVersions(TypedDict):
    isSnapshot: bool
    versions: list[str]

def download_neoforge(to: str, force_version: str | None = None, heap: str = "2048M") -> ServerInstallData:
    if force_version:
        force_version = force_version.split(".", 1)[1] + "."  # 1.21.5 -> 21.5.

    neo_versions: NeoVersions = requests.get(
        "https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge",
        headers=ua_header
    ).json()

    neo_latest = next(
        (ver for ver in reversed(neo_versions["versions"]) if force_version is None or ver.startswith(force_version)),
        None
    )
    
    if not neo_latest:
        raise Exception("No suitable NeoForge version found")

    minecraft = f"1.{'.'.join(neo_latest.split('.', 2)[:2])}"

    root = os.path.join(to, f"NeoForge {minecraft}")
    os.makedirs(root, exist_ok=True)

    java_path = get_java_path(to, 21)
    java_path_relative = os.path.relpath(java_path, root)
    print(f"Using Java at {java_path_relative}")

    all_run = [java_path_relative, f"-Xmx{heap}", f"-Xms{heap}", "@user_jvm_args.txt"]
    windows_run = all_run + [f"@libraries/net/neoforged/neoforge/{neo_latest}/win_args.txt"]
    unix_run = all_run + [f"@libraries/net/neoforged/neoforge/{neo_latest}/unix_args.txt"]
    system_run = windows_run if Utils.is_windows else (unix_run if Utils.is_linux else None)

    mods = os.path.join(root, "mods")
    os.makedirs(mods, exist_ok=True)

    version_path = os.path.join(root, "neo_version")

    if os.path.exists(version_path):
        with open(version_path, 'r') as f:
            if f.read().strip() == neo_latest:
                print(f"NeoForge {neo_latest} is already installed, skipping download")
                return ServerInstallData(root_dir=root, mods_dir=mods, run_args=system_run)

    # todo: y/n prompt?
    write_eula(root)

    print(f"Downloading NeoForge {neo_latest} installer")
    installer_jar = os.path.join(to, f"neoforge-{neo_latest}.jar")
    installer_url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{neo_latest}/neoforge-{neo_latest}-installer.jar"
    download_file(installer_jar, installer_url)

    print(f"Running NeoForge {neo_latest} installer")
    java_path = get_java_path(to, 21)
    subprocess.run([java_path, "-jar", installer_jar, "--installServer"], cwd=root, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    os.unlink(installer_jar)

    bat_file = os.path.join(root, "run.bat")
    with open(bat_file, 'w') as f:
        f.write(f"@echo off\nstart {' '.join(windows_run)} %* > log.txt 2> errorlog.txt")
    
    sh_file = os.path.join(root, "run.sh")
    with open(sh_file, 'w') as f:
        f.write(f"#!/bin/bash\nexec {' '.join(unix_run)} \"$@\" > log.txt 2> errorlog.txt")

    with open(version_path, 'w') as f:
        f.write(neo_latest)

    return ServerInstallData(root_dir=root, mods_dir=mods, run_args=system_run)
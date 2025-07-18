import os
import sys
import requests
from typing import Optional

ua = "qixils/minecraft-crowdcontrol/1.0.0"
ua_header = {"User-Agent": ua}

jre_paths: dict[int, str] = {
    8: "jdk-8",
    21: "jdk-21",
}

def mkdir(dir: str, empty: bool = False) -> str:
    os.makedirs(dir, exist_ok=True)

    if empty:
        # Delete all files and subdirectories in the directory
        for filename in os.listdir(dir):
            file_path = os.path.join(dir, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)

    return dir

def is_semver_ge(new_semver: str, old_semver: str) -> bool:
    new_parts = new_semver.split(".")
    old_parts = old_semver.split(".")
    parts = max(len(new_parts), len(old_parts))
    
    for i in range(parts):
        new_part = int(new_parts[i]) if i < len(new_parts) else 0
        old_part = int(old_parts[i]) if i < len(old_parts) else 0
        
        if new_part > old_part:
            return True
        elif new_part < old_part:
            return False
            
    return True

def semver_sort(a: str, b: str) -> int:
    if a == b:
        return 0
    if is_semver_ge(a, b):
        return -1
    if is_semver_ge(b, a):
        return 1
    return 0  # fallback

def download_file(path: str, url: str, version: Optional[str] = None) -> None:
    # Optionally check if a file with a matching version is already downloaded
    version_path = path + ".version"
    if version is not None:
        if os.path.exists(version_path):
            with open(version_path, 'r') as f:
                if f.read().strip() == version:
                    return

    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise Exception(f"Failure while retrieving remote data (source: {url})")

    with open(path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)
    
    if version is not None:
        with open(version_path, 'w') as f:
            f.write(version)

def write_eula(folder: str) -> None:
    file = os.path.join(folder, "eula.txt")
    if os.path.exists(file):
        with open(file, 'r') as f:
            if 'eula=true' in f.read():
                return

    print("")
    print("Please note that by running a Minecraft server, you are indicating your agreement to Minecraft's EULA (https://aka.ms/MinecraftEULA).")
    confirmation = input("Continue? (Y/n): ")
    if len(confirmation) > 0 and not confirmation.lower().startswith('y'):
        sys.exit(0)

    contents = "eula=true"
    with open(file, 'w') as f:
        f.write(contents)

def write_run(jar: str, java: int) -> None:
    jre = jre_paths[java]
    jar_name = os.path.basename(jar)
    bat_file = os.path.join(os.path.dirname(jar), "run.bat")
    
    with open(bat_file, 'w') as f:
        f.write(f"@echo off\n"
                f"start ..\\java\\{jre}\\bin\\java.exe -Xmx2048M -Xms2048M -jar {jar_name} nogui > log.txt 2> errorlog.txt")

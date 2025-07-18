from .Utilities import DownloadStep, FetchStep, SubprocessStep, download_file, jre_paths, ua_header, write_eula
from .Modrinth import download_mod
from .Java import get_java_path
from . import ServerInstallData, StepsStep, SyncStep
from typing import TypedDict
import Utils
import os
import requests
import subprocess

class NeoVersions(TypedDict):
    isSnapshot: bool
    versions: list[str]

class DownloadNeoForge(StepsStep):
    def __init__(self, to: str, force_version: str | None = None, heap: str = "2048M"):
        self.name = f"Downloading {force_version if force_version else 'latest'} NeoForge..."

        self.to = to
        self.force_version = (force_version.split(".", 1)[1] + ".") if force_version else None
        self.heap = heap
        self.installer_jar = os.path.join(to, f"neoforge-installer.jar")

        super().__init__(
            SyncStep(lambda: print(f"Downloading NeoForge index")),
            FetchStep("https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge"),
            SyncStep(self._process_versions),
            DownloadStep(filepath=self.installer_jar),
            SyncStep(self._process_server),
            SubprocessStep(),
            SyncStep(self._process_cleanup),
        )
    
    def _process_versions(self, neo_versions: NeoVersions) -> str:
        self.neo_latest = next(
            (ver for ver in reversed(neo_versions["versions"]) if self.force_version is None or ver.startswith(self.force_version)),
            None
        )
        
        if not self.neo_latest:
            raise Exception("No suitable NeoForge version found")

        self.minecraft = f"1.{'.'.join(self.neo_latest.split('.', 2)[:2])}"

        self.root = os.path.join(self.to, f"NeoForge {self.minecraft}")
        os.makedirs(self.root, exist_ok=True)

        self.java_path = get_java_path(self.to, 21)
        self.java_path_relative = os.path.relpath(self.java_path, self.root)
        print(f"Using Java at {self.java_path_relative}")

        self.all_run = [self.java_path_relative, f"-Xmx{self.heap}", f"-Xms{self.heap}", "@user_jvm_args.txt"]
        self.windows_run = self.all_run + [f"@libraries/net/neoforged/neoforge/{self.neo_latest}/win_args.txt"]
        self.unix_run = self.all_run + [f"@libraries/net/neoforged/neoforge/{self.neo_latest}/unix_args.txt"]
        self.system_run = self.windows_run if Utils.is_windows else (self.unix_run if Utils.is_linux else None)

        self.mods = os.path.join(self.root, "mods")
        os.makedirs(self.mods, exist_ok=True)

        self.version_path = os.path.join(self.root, "neo_version")

        if os.path.exists(self.version_path):
            with open(self.version_path, 'r') as f:
                if f.read().strip() == self.neo_latest:
                    print(f"NeoForge {self.neo_latest} is already installed, skipping download")
                    return

        # todo: y/n visual prompt
        write_eula(self.root)

        print(f"Downloading NeoForge {self.neo_latest} installer")
        return f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{self.neo_latest}/neoforge-{self.neo_latest}-installer.jar"

    def _process_server(self, req):
        if req is False:
            # install is skipped
            return
        
        print(f"Running NeoForge {self.neo_latest} installer")
        java_path = get_java_path(self.to, 21)
        return [java_path, "-jar", self.installer_jar, "--installServer"], {"cwd": self.root, "stderr": subprocess.DEVNULL, "stdout": subprocess.DEVNULL}

    def _process_cleanup(self, req):
        if req is False:
            # install is skipped
            return ServerInstallData(root_dir=self.root, mods_dir=self.mods, run_args=self.system_run)
        
        os.unlink(self.installer_jar)

        bat_file = os.path.join(self.root, "run.bat")
        with open(bat_file, 'w') as f:
            f.write(f"@echo off\nstart {' '.join(self.windows_run)} %* > log.txt 2> errorlog.txt")
        
        sh_file = os.path.join(self.root, "run.sh")
        with open(sh_file, 'w') as f:
            f.write(f"#!/bin/bash\nexec {' '.join(self.unix_run)} \"$@\" > log.txt 2> errorlog.txt")

        with open(self.version_path, 'w') as f:
            f.write(self.neo_latest)

        return ServerInstallData(root_dir=self.root, mods_dir=self.mods, run_args=self.system_run)

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
from .Utilities import download_file, jre_paths, ua_header, write_eula
from Utils import is_windows, is_linux
import os
import requests
import zipfile
import platform
from typing import TypedDict

class Download(TypedDict):
    checksum: str
    checksum_link: str
    download_count: int
    link: str
    metadata_link: str
    name: str
    signature_link: str
    size: int

class Binary(TypedDict):
    architecture: str
    download_count: int
    heap_size: str
    image_type: str
    installer: Download
    jvm_impl: str
    os: str
    package: Download
    project: str
    scm_ref: str
    updated_at: str

class Version(TypedDict):
    build: int
    major: int
    minor: int
    openjdk_version: str
    optional: str
    security: int
    semver: str

class Asset(TypedDict):
    binary: Binary
    release_link: str
    release_name: str
    vendor: str
    version: Version

def download_jre(to: str, version: int) -> str:
    print(f"Fetching Java {version} versions")

    system = "windows" if is_windows else "linux" if is_linux else None
    if not system:
        raise Exception("Unsupported operating system for Java download")
    
    arch = "aarch64" if platform.machine() in ["aarch64", "arm64"] else "x64"

    api_url = f"https://api.adoptium.net/v3/assets/latest/{version}/hotspot?architecture={arch}&image_type=jre&os={system}&vendor=eclipse"
    data: Asset = requests.get(api_url, headers=ua_header).json()[0]

    outpath = os.path.join(to, "java", jre_paths[version])
    os.makedirs(outpath, exist_ok=True)
    release_path = os.path.join(outpath, "release")
    semver = None

    if os.path.exists(release_path):
        with open(release_path, 'r') as file:
            info = file.read()
            semver = info.split('SEMANTIC_VERSION="')[1].split('"')[0]

    if data["version"]["semver"] == semver:
        print("Already up-to-date, skipping download")
        return

    print(f"Downloading Java {data['version']['semver']}")
    url = data["binary"]["package"]["link"]
    zip_path = os.path.join(outpath, "jre.zip")
    download_file(zip_path, url)

    print(f"Extracting Java {version}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        subfolder = zip_ref.namelist()[0]
        for entry in zip_ref.infolist()[1:-1]:
            if entry.is_dir():
                continue
            relative = entry.filename[len(subfolder):]
            filepath = os.path.join(outpath, *relative.split("/"))
            dirpath = os.path.dirname(filepath)
            os.makedirs(dirpath, exist_ok=True)
            with open(filepath, 'wb') as file:
                file.write(zip_ref.read(entry.filename))

    os.remove(zip_path)

    return get_java_path(to, version)

def get_java_path(to: str, version: int) -> str:
    jre = jre_paths[version]

    bin = "java.exe" if is_windows else "java" if is_linux else None
    if not bin:
        raise Exception("Unsupported operating system for Java path retrieval")

    java_path = os.path.join(to, "java", jre, "bin", bin)

    if not os.path.exists(java_path):
        raise Exception(f"Java {version} not found at {java_path}")
    
    return java_path

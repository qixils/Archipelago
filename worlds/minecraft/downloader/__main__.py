from .Java import download_jre
from .NeoForge import download_neoforge
from .Utilities import download_file
import os

root = os.path.join(os.getcwd(), "Minecraft Forge Server")
download_jre(root, 21)
mods_dir = download_neoforge(root, force_version="1.21.6").mods_dir
download_file(os.path.join(mods_dir, "archipelago.jar"), "https://github.com/qixils/NeoForgeAP/releases/download/v1.1.0/aprandomizer-0.3.0-SNAPSHOT+1.21.6.jar")

from typing import NamedTuple

class ServerInstallData(NamedTuple):
    root_dir: str
    mods_dir: str
    run_args: list[str]

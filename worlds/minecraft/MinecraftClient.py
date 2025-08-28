import argparse
import io
import json
import logging
import os
import pkgutil
import platform
import re
import shutil
import subprocess
import sys
import threading
import time

from enum import Enum
from math import floor, log
from queue import Queue
from typing import List, Optional
from urllib.parse import urlparse

from kivy import Config
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.network.urlrequest import UrlRequest, UrlRequestUrllib
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, ListProperty
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import NoTransition
from kivy.uix.textinput import TextInput
from kivy.utils import escape_markup

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.progressindicator import MDLinearProgressIndicator
from kivymd.uix.recycleview import MDRecycleView
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.stacklayout import MDStackLayout
from kivymd.uix.widget import MDWidget

import Utils
from worlds.minecraft.downloader import ServerInstallData, StepsStep, SyncStep
from worlds.minecraft.downloader.Java import DownloadJava
from worlds.minecraft.downloader.NeoForge import DownloadNeoForge
from worlds.minecraft.downloader.Utilities import DownloadStep, FetchStep

version_file_endpoint = "https://raw.githubusercontent.com/qixils/NeoForgeAP/main/versions/minecraft_versions.json"

# TODO: Import/fix options.py and/or whatever is being generated in host.yaml
options = Utils.get_settings()["minecraft_options"]

os.environ["KIVY_NO_CONSOLELOG"] = "1"
os.environ["KIVY_NO_FILELOG"] = "1"
os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_LOG_ENABLE"] = "0"

Config.set("input", "mouse", "mouse,disable_multitouch")
Config.set("kivy", "exit_on_escape", "0")
Config.set("graphics", "multisamples", "0")

parser = argparse.ArgumentParser()
parser.add_argument("apmc_file", default=None, nargs='?', help="Path to an Archipelago Minecraft data file (.apmc)")

args, rest = parser.parse_known_args()

Utils.init_logging('MinecraftClient')
logger = logging.getLogger("MinecraftClient")


def load_text(*path: str):
    return pkgutil.get_data(__name__, "/".join(path)).decode()


def load_image(*path: str):
    data = io.BytesIO(pkgutil.get_data(__name__, "/".join(path)))
    texture = CoreImage(data, ext="png")
    return texture


def format_bytes(size):
    power = 0 if size <= 0 else floor(log(size, 1024))
    return f"{round(size / 1024 ** power, 2)} {['B', 'KB', 'MB', 'GB', 'TB'][int(power)]}"


class ServerStatus(Enum):
    STOPPED = 0
    STARTING = 1
    RUNNING = 2

    def __lt__(self, other):
        return self.value < other.value

    def __gt__(self, other):
        return self.value > other.value

    def __eq__(self, other):
        return self.value == other.value


def get_recent_items() -> List:
    if not os.path.isdir(options.server_directory):
        os.makedirs(options.server_directory)
    saves = []
    for directory in os.listdir(options.server_directory):
        if directory.startswith("Archipelago-"):
            save = os.path.join(options.server_directory, directory, "save.apmc")
            description = "None"
            with open(save, "r") as jsonfile:
                save = json.load(jsonfile)
                description = save["description"]
            saves.append((description, directory))
    return saves


class MinecraftClient(MDApp):
    stop = threading.Event()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.index = 0
        self.welcome_window: Optional[WelcomeWindow] = None
        self.window_manager: Optional[WindowManager] = None
        self.server_window: Optional[ServerWindow] = None
        self.minecraft_versions: dict[str, list] = {}
        self.apmc = None
        self.version = {}
        self.server = None
        self.java_url = None
        self.status: ServerStatus = ServerStatus.STOPPED
        self.apmc_path = None
        self.mod_info = {}
        self.release_chanel = None
        logger.info(f"Client Initialized")
        self._init_mod_info()

    # Handles (re)loading mod info, whether from a successful HTTP request or not
    def _handle_mod_info(self, resp):
        if resp:
            self.mod_info = resp
            os.makedirs(options.server_directory, exist_ok=True)
            with open(fp, 'w') as f:
                self.mod_info = json.dump(resp, f)
            return

        fp = os.path.join(options.server_directory, 'ap-version.json')
        if not os.path.exists(fp):
            return

        try:
            with open(fp, 'r') as f:
                self.mod_info = json.load(f)
        except Exception as e:
            logger.error("Failed to parse ap-version JSON", e)

    # Handles initializing the mod info fetching process
    def _init_mod_info(self):
        StepsStep(
            SyncStep(self._handle_mod_info), # Load the cached JSON file
            FetchStep(url=version_file_endpoint), # Download the latest version
            SyncStep(self._handle_mod_info), # Save the latest version (if available)
            # TODO: self.auto_start_server() ?
        ).run(error_ok=True)

    def build(self):
        logger.info(f"building client")
        # TODO: Rewrite MinecraftClient.kv to work with KivyMD. Look under the data file.
        Builder.load_string(load_text("data", "MinecraftClient.kv"))
        self.window_manager = WindowManager(transition=NoTransition())
        self.welcome_window = WelcomeWindow(self)
        self.server_window = ServerWindow(self)
        self.window_manager.add_widget(self.welcome_window)
        self.window_manager.add_widget(self.server_window)
        logger.info(f"client built")

        # send our request out to fetch the versions file
        logger.info(f"fetching versions file")
        self._init_mod_info()

        logger.info(f"binding on close request")
        Window.bind(on_request_close=self.on_request_close)

        logger.info(f"returning window manager")
        return self.window_manager

    def on_request_close(self, *arg):
        if self.status == ServerStatus.RUNNING:
            self.send_command("stop")
            Clock.schedule_interval(self.close, 1 / 60)
            return True
        sys.exit()

    def close(self, dt):
        if self.stop.is_set():
            sys.exit()

    def get_application_icon(self):
        return load_image("assets", "icon.png")

    def init(self, dt=None):
        layout: MDWidget = self.welcome_window.ids.saves
        layout.clear_widgets()
        saves = get_recent_items()
        if len(saves) == 0:
            layout.add_widget(MDLabel(text="No saves"))
        else:
            for name, path in saves:
                layout.add_widget(RecentItem(name=name, path=path, client=self))

        ids: MDStackLayout = self.welcome_window.ids
        ids.path.value = options.server_directory
        ids.max_memory.value = options.max_heap_size
        ids.min_memory.value = options.min_heap_size
        ids.release_option.value = options.release_channel
        ids.release_option.options = self.minecraft_versions.keys()

    def auto_start_server(self):
        Clock.schedule_once(self.init, 1)
        self.apmc_path = os.path.abspath(args.apmc_file) if args.apmc_file else None
        if self.apmc_path:
            self.open_apmc(path=self.apmc_path)

    def open_apmc(self, path=None):
        self.apmc_path = path
        if self.apmc_path is None:
            # TODO: Replace filedialog from KTinker with MDDialog?
            self.apmc_path = filedialog.askopenfilename(title="Choose AP Minecraft file",
                                                        filetypes=(("Archipelago Minecraft", "*.apmc"),))
        if self.apmc_path is None or self.apmc_path == "" or os.path.isfile(self.apmc_path) is False:
            return
        with open(self.apmc_path, "r") as f:
            data = f.read()

            if data.startswith("e"):
                from base64 import b64decode
                apmc = json.loads(b64decode(data))
            elif data.startswith("{"):
                apmc = json.loads(data)

        if apmc is not None:
            try:
                self.apmc = apmc

                self.version = next(filter(lambda entry: entry['version'] == self.apmc["client_version"],
                                           self.minecraft_versions[options.release_channel]))
                self.server_window.status.text = f"Initializing {self.version['minecraft']}"

                self.window_manager.current = "Server"
                self.start_server()
            except KeyError:
                logger.error(f"unable to find version {self.apmc['client_version']} on {options.release_channel}")
                self.log_error(f"unable to find version {self.apmc['client_version']} on {options.release_channel}")
                self.apmc_path = None

    def set_description(self, text):
        self.apmc["description"] = text
        self.start_server()

    def eula_yes(self):
        eula_path = os.path.join(options.server_directory, "eula.txt")
        with open(eula_path, 'r+') as f:
            text = f.read()
            if 'false' in text:
                f.seek(0)
                f.write(text.replace('false', 'true'))
                f.truncate()
        self.start_server()

    def eula_no(self):
        self.window_manager.current = "Welcome"

    def download_file(self, url, folder, on_success=None, on_error=None, file_name=None, extract=False,
                      message="Downloading Files"):
        self.server_window.show_progress_bar_dialog("Downloading", message, 100)

        self.download = Downloader(url=url,
                                   folder=folder,
                                   download_popup=self.server_window.progress_popup,
                                   on_success=on_success, on_error=on_error,
                                   on_finish=lambda: self.server_window.close_progress_bar_dialog(),
                                   file_name=file_name,
                                   extract=extract)

    @mainthread
    def start_server(self) -> None:
        # TODO: define better insight/typing into what self.version is
        StepsStep(
            DownloadJava(options.server_directory, 21),
            DownloadNeoForge(options.server_directory, self.version["minecraft"]), # TODO: is there a standalone JAR like fabric now? check history
            SyncStep(lambda data: (None, os.path.join(data.mods_dir, "Archipelago.jar"))),
            DownloadStep(self.version["url"])
        )

        # TODO: migrate into above (for check_eula, integrate it as a KivyMD-based prompt into the EULA writer in NeoForge.py)
        # if self.apmc.get("description") is None:
        #     edit_prompt(title="Set Description", content="Set a description for this world", default="",
        #                 confirm=lambda text: self.set_description(text))
        #     return

        # if not self.check_eula():
        #     confirm_prompt(title="EULA Agreement",
        #                    content="By running this server you agree to the Minecraft EULA"
        #                            "\nhttps://aka.ms/MinecraftEULA\nDo you agree to the Minecraft Eula?",
        #                    confirm=lambda _: self.eula_yes(), cancel=lambda _: self.eula_no())
        #     return

        # threading.Thread(target=self.server_thread).start()

    def server_thread(self):

        self.status = ServerStatus.STOPPED
        self.server_window.background_color = (.5, .1, .1, 1)
        world_name = f"Archipelago-{self.apmc['seed_name']}-P{self.apmc['player_id']}"
        world_dir = os.path.join(options.server_directory, world_name)
        if not os.path.isdir(world_dir):
            os.makedirs(world_dir)
        save_path = os.path.join(world_dir, "save.apmc")
        if not os.path.isfile(save_path):
            with open(save_path, "w") as file:
                json.dump(self.apmc, file)

        os.environ["JAVA_OPTS"] = ""
        self.server = subprocess.Popen((self.get_jdk(),
                                        "-jar",
                                        self.get_server_jar(),
                                        "--nogui",
                                        "--world",
                                        world_name,
                                        ),
                                       stderr=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stdin=subprocess.PIPE,
                                       encoding="utf-8",
                                       text=True,
                                       cwd=options.server_directory
                                       )

        server_queue = Queue()
        stream_server_output(self.server.stdout, server_queue, self.server)
        stream_server_output(self.server.stderr, server_queue, self.server)

        while not self.stop.is_set():
            if self.server.poll() is not None:
                self.log_raw("[color=FFFF00]Minecraft server has exited.[/color]")
                self.stop.set()
                self.server_window.status.text = "Server Stopped"
                self.server_window.background_color = (.5, .1, .1, 1)

            while not server_queue.empty():
                raw_message: str = server_queue.get()

                match = re.match(r"^\[[0-9:]+] \[.+/(WARN|INFO|ERROR)] \[.+]: (.*)", raw_message)
                if match:
                    level = match.group(1)
                    msg = escape_markup(match.group(2))

                    if level == "WARN":
                        self.log_warn(msg)
                    elif level == "ERROR":
                        self.log_error(msg)
                    elif level == "INFO":
                        self.log_info(msg)
                else:
                    self.log_info(raw_message)

                if self.status < ServerStatus.RUNNING:

                    server_starting_match = re.match(r"^\[[0-9:]+] \[main/INFO]: Loading Minecraft ([0-9.]+)",
                                                     raw_message)
                    if server_starting_match:
                        self.log_info(f"Starting Minecraft {server_starting_match.group(1)}")
                        self.server_window.status.text = f"Starting Server for {server_starting_match.group(1)}"
                        self.server_window.background_color = (.5, .5, .0, 1)
                        self.version["minecraft"] = server_starting_match.group(1)
                        self.status = ServerStatus.STARTING

                    server_started_match = re.match(
                        r"^\[[0-9:]+] \[Server thread/INFO]: Done \([0-9.]+s\)! For help, type \"help\"", raw_message)
                    if server_started_match:
                        self.server_window.status.text = f"Server Running. Connect to `127.0.0.1` in Minecraft {self.version['minecraft']}"
                        self.server_window.background_color = (.1, .5, .1, 1)
                        self.status = ServerStatus.RUNNING

                server_queue.task_done()
            time.sleep(0.01)

    def send_command(self, cmd):
        try:
            self.server.stdin.write(f'{cmd}\n')
            self.server.stdin.flush()
        except Exception:
            pass

    @mainthread
    def log_info(self, msg):
        self.server_window.log.on_message_markup(f"[b][INFO][/b] {escape_markup(msg)}")

    @mainthread
    def log_warn(self, msg):
        self.server_window.log.on_message_markup(f"[color=FFFF00][b][WARN][/b][/color] {escape_markup(msg)}")

    @mainthread
    def log_error(self, msg):
        self.server_window.log.on_message_markup(f"[color=FFFF00][b][ERROR][/b][/color] {escape_markup(msg)}")

    @mainthread
    def log_raw(self, msg):
        self.server_window.log.on_message_markup(msg)


def stream_server_output(pipe, queue, process):
    def queuer():
        while process.poll() is None:
            text = pipe.readline().rstrip().expandtabs()
            if text:
                queue.put_nowait(text)

    thread = threading.Thread(target=queuer, name="Minecraft Output Queue", daemon=True)
    thread.start()
    return thread


class TextOption(MDGridLayout):
    value = StringProperty()
    label = StringProperty()
    button_label = StringProperty()


class DropdownOption(MDGridLayout):
    value = StringProperty()
    label = StringProperty()
    options = ListProperty()


class FolderOption(TextOption):

    def button_press(self):
        # TODO: Replace filedialog from KTinker with MDDialog?
        new_dir = filedialog.askdirectory(title="Choose Server Directory", initialdir=options.server_directory)
        if new_dir:
            self.value = new_dir


class RecentItem(MDBoxLayout):
    name = StringProperty()
    path = StringProperty()
    client: MinecraftClient = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        icon_delete = load_image("assets", "delete.png")
        icon_edit = load_image("assets", "edit.png")
        self.ids.delete_icon.texture = icon_delete.texture
        self.ids.rename_icon.texture = icon_edit.texture

    def load(self):
        save_path = os.path.join(options.server_directory, self.path, "save.apmc")
        if os.path.isfile(save_path):
            self.client.open_apmc(save_path)
        else:
            info_dialog(title="Error", content=f"Unable to find save file for world {self.path}")

    def delete(self):
        self.client.welcome_window.confirm_delete(target=self.path, title="Confirm Delete",
                                                  content=f"Delete {self.name}?\nThis Action is permanent.")

    def rename(self):
        edit_prompt(title="Confirm Edit", content=f"Rename {self.name}", default=self.name,
                    confirm=lambda text: self.set_name(text))

    def set_name(self, name):
        self.name = name
        try:
            with open(os.path.join(options.server_directory, self.path, "save.apmc"), "r+") as file:
                data = json.load(file)
                data["description"] = name
                file.seek(0)
                file.truncate()
                json.dump(data, file)
        except Exception as e:
            info_dialog(title="Error", content=f"Error renaming world: {e}")


class ConfirmDialog(Popup):
    text = StringProperty()
    confirm_text = StringProperty()
    cancel_text = StringProperty()


class InfoDialog(Popup):
    text = StringProperty()
    button_text = StringProperty()


class ProgressBarDialog(Popup):
    text = StringProperty("")
    progress_text = StringProperty("")
    progress = NumericProperty(0)
    max = NumericProperty(100)

    def __init__(self, max, **kwargs):
        super().__init__(**kwargs)
        self.max = max


# TODO: migrate to Steps
def confirm_prompt(confirm=None, title="Prompt", content="Are you sure?", cancel=None, confirm_text="Yes",
                   cancel_text="No"):
    popup = ConfirmDialog(title=title, text=content, confirm_text=confirm_text, cancel_text=cancel_text)
    popup.open()

    if cancel is not None:
        popup.ids.cancel.bind(on_press=cancel)

    if confirm is not None:
        popup.ids.confirm.bind(on_press=confirm)


def info_dialog(title="Prompt", content="Are you sure?", cancel=None):
    popup = InfoDialog(title=title, text=content, button_text="OK")
    popup.open()


def edit_prompt(confirm, title="Prompt", content="Are you sure?", cancel=None, default=""):
    popup = ConfirmDialog(title=title, text=content, confirm_text="Confirm", cancel_text="Cancel")
    popup.open()

    content: MDWidget = popup.ids.content

    textinput = TextInput(text=default,
                          size_hint=(1, None),
                          height=30,
                          multiline=False,
                          )
    content.add_widget(textinput)
    textinput.bind(on_text_validate=lambda _: confirm(textinput.text))
    textinput.bind(on_text_validate=popup.dismiss)

    if cancel is not None:
        popup.ids.cancel.bind(on_press=cancel)

    popup.ids.confirm.bind(on_press=lambda _: confirm(textinput.text))


class WindowManager(MDScreenManager):
    pass


class LogEntry(MDLabel):
    pass


class ServerWindow(MDScreen):

    def __init__(self, client, **kw):
        super().__init__(**kw)
        self.client = client
        self.log: ServerLog = self.ids.log
        self.status: MDLabel = self.ids.status
        self.cmd: TextInput = self.ids.cmd
        self.progress_popup: Optional[ProgressBarDialog] = None
        self.background_color = (.5, .1, .1, 1)

    def send_command(self, value):
        self.client.send_command(value)
        self.cmd.text = ""
        Clock.schedule_once(self.focus_cmd, 0)

    def focus_cmd(self, dv):
        self.cmd.focus = True

    def show_progress_bar_dialog(self, title, content, max):
        self.progress_popup = ProgressBarDialog(title=title, text=content, max=max)
        self.progress_popup.open()

    def close_progress_bar_dialog(self):
        if self.progress_popup is not None:
            self.progress_popup.dismiss()
        self.progress_popup = None


class ServerLog(MDRecycleView):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []

    def on_log(self, record: str):
        self.data.append({"text": escape_markup(record)})
        self.clean_old()

    def on_message_markup(self, text):
        self.data.append({"text": text})
        self.clean_old()

    def clean_old(self):
        if len(self.data) > self.messages:
            self.data.pop(0)


class WelcomeWindow(MDScreen):
    version = StringProperty()

    def __init__(self, client: MinecraftClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.apmc = None
        Window.minimum_width, Window.minimum_height = (400, 300)

    def do_delete(self, target):
        world_path = os.path.join(options.server_directory, target)
        if options.server_directory in world_path and os.path.isdir(world_path):
            shutil.rmtree(world_path)
            self.client.init()

    def confirm_delete(self, target, title="Confirm Delete", content="This Action is permanent."):
        confirm_prompt(title=title, content=content, confirm=lambda _: self.do_delete(target))

    def save_options(self):
        options.server_directory = self.ids.path.value
        options.max_heap_size = self.ids.max_memory.value
        options.min_heap_size = self.ids.min_memory.value
        options.release_channel = self.ids.release_option.value
        Utils.get_settings().save()
        self.client.init()


def launch():
    MinecraftClient().run()


MinecraftClient().run()

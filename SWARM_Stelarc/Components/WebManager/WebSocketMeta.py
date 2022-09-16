import datetime
import socketio
import time
import asyncio
import threading
from collections import deque
from ..Utils.FPSCounter import FPSCounter
import io
import datetime
import base64
import cv2
import asyncio
from concurrent.futures import ThreadPoolExecutor


class SwarmData:
    def __init__(self, image_data=None, cameras_data=None):
        self.image_data = image_data
        self.cameras_data = cameras_data
        self.time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    def get_cameras_json(self):
        if self.cameras_data is not None:
            return self.cameras_data

    def get_image_string(self):
        if self.image_data is not None:
            retval, buffer = cv2.imencode('.jpg', self.image_data)
            img_str = base64.b64encode(buffer).decode()
            # img_str = base64.b64encode(self.image_data.getvalue()).decode()
            return "data:image/jpeg;base64," + img_str
        return ''

    def get_json(self):
        data = {}
        data['cameras_data'] = self.get_cameras_json()
        data['frame_data'] = self.get_image_string()
        data['datetime'] = self.time
        return data


class Status:
    def __init__(self, _id, name, description):
        self.id = _id
        self.name = name
        self.description = description
        self.extra = ''

    def get_dbg_text(self, ws):
        synced = "(SYNCD) " if ws.sync_with_server else ""
        return f"{synced}{self.name}: {self.description}"


class Statuses:
    NOT_INITIALIZED = Status(-1, "NOT INITIALIZED", "Socket.io created but not initialized")
    INITIALIZED = Status(0, "INITIALIZED", "Socket.io setup but not connected")
    CONNECTING = Status(1, "CONNECTING", "Socket.io is trying to connect")
    CONNECTED = Status(2, "CONNECTED", "Socket.io connected")
    WAITING = Status(3, "WAITING", "Socket.io connected")
    DISCONNECTED = Status(4, "DISCONNECTED", "Socket.io lost connection")


class WebSocketMeta:
    def __init__(self, tasks_manager, url, namespace, frame_w, frame_h):
        self.sio = socketio.AsyncClient(logger=False, engineio_logger=False)
        self.enabled = True
        self.sync_with_server = False
        self.max_wait_timeout = 10
        self.wait_time = 0
        self.status = Statuses.NOT_INITIALIZED

        self.url = "url"
        self.namespace = namespace
        self.uri = self.url + self.namespace
        self.tag = "WS_" + self.namespace[1:min(4, len(self.namespace))] # First 3 characters of the namespace, excluding the "/"

        self.multi_threaded = True
        self.tasks_manager = tasks_manager
        self.task_running = False
        self.async_loop = asyncio.new_event_loop()
        self.executor = ThreadPoolExecutor(2)   #Create a ProcessPool with 2 processes

        self.fps_counter = FPSCounter()
        self.out_buffer_size = 2
        self.out_buffer = deque([])
        self.out_fps_counter = FPSCounter()

        self.in_buffer_size = 60
        self.in_buffer = deque([])
        self.in_fps_counter = FPSCounter()

        self.last_emit = datetime.datetime.now()

    def attach_callbacks(self):
        print(f"Attach callbacks not implemented!")
        return False

    def main_loop_starter(self):
        self.async_loop.run_until_complete(self.main_loop())

    async def main_loop(self):
        print(f"{self.namespace} Task started!")
        try:
            while self.task_running:
                if not self.sio.connected:
                    await self.attempt_connect()
                    await asyncio.sleep(3)
                else:
                    await self.background_task()
                    await asyncio.sleep(0)
        except Exception as e:
            print(f"Exception in {self.namespace} loop: {e}")

    async def background_task(self):
        print(f"WebSocket loop not implemented!")

    def start_async_task(self):
        self.task_running = True
        self.async_loop.run_in_executor(self.executor, self.main_loop_starter)
        # print(f"{self.namespace} Task completed")

    def stop_async_task(self):
        self.task_running = False

    def init(self):
        if self.enabled:
            if not self.multi_threaded:
                print(f"Stopping {self.namespace} background task")
                self.stop_async_task()
            else:
                if not self.task_running:
                    print(f"Starting {self.namespace} background task")
                    self.start_async_task()
        else:
            if self.task_running:
                print(f"Stopping {self.namespace} background task")
                self.stop_async_task()

    def update_config(self, data):
        self.sync_with_server = data.get("sync_with_server", False)
        url = data.get("url", self.url)
        namespace = data.get("namespace", self.namespace)
        if url != self.url or namespace != self.namespace:
            print(f"WebSocket URI changed from {self.url}{self.namespace} to {url}{namespace}, reconnecting")
            self.url = url
            self.namespace = namespace
            self.uri = f"{url}{namespace}"
            self.init()
            # if not self.connect_task.is_running():
            #     self.connect_task.start()

    def set_status(self, new_status, extra="", debug=True):
        if debug:
            print(f"{self.tag} {self.status.name} -> {new_status.name}, {extra}")
        self.status = new_status
        self.status.extra = extra

    def update_status(self, as_loop):
        if self.sio.connected:
            if self.status.id == Statuses.WAITING.id:
                elapsed = time.time() - self.wait_time
                if elapsed > self.max_wait_timeout:
                    self.wait_time = 0
                    self.set_status(Statuses.CONNECTED, self.uri)
                    return True
                return False
            elif self.status.id != Statuses.CONNECTED.id:
                # Maybe something went wrong and we missed the connected message but socketio still connected somehow!
                self.set_status(Statuses.CONNECTED, self.uri)
            return True
        else:
            if self.status.id == Statuses.CONNECTING.id:
                return False
            elif self.status.id == Statuses.CONNECTED.id:
                self.set_status(Statuses.DISCONNECTED, self.uri)
                return False
            elif self.status.id in [Statuses.DISCONNECTED.id, Statuses.NOT_INITIALIZED.id]:
                self.set_status(Statuses.CONNECTING, self.uri)
                try:
                    as_loop.run_until_complete(self.attempt_connect())
                except Exception as e:
                    print(f"Connect loop is already running: {e}")
                # self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=1)
                # time.sleep(1) # Otherwise it might get stuck in a loop as the status will change to connected WHILE it was in the "sio.connected" else
                return False
            else:
                self.set_status(Statuses.DISCONNECTED, self.uri)
            return False

    def is_ready(self):
        return self.status.id == Statuses.CONNECTED.id

    async def attempt_connect(self):
        try:
            await self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=3)
        except Exception as e:
            print(f"Exception trying to connect to {self.url}{self.namespace}: {e}")
            self.set_status(Statuses.DISCONNECTED)
            await asyncio.sleep(3)

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
        synced = "(SYNCD)" if ws.sync_with_server else ""
        return f"{synced} {self.name}: {self.description}"


class Statuses:
    NOT_INITIALIZED = Status(-1, "NOT INITIALIZED", "Socket.io created but not initialized")
    INITIALIZED = Status(0, "INITIALIZED", "Socket.io setup but not connected")
    CONNECTING = Status(1, "CONNECTING", "Socket.io is trying to connect")
    CONNECTED = Status(2, "CONNECTED", "Socket.io connected")
    WAITING = Status(3, "WAITING", "Socket.io connected")
    DISCONNECTED = Status(4, "DISCONNECTED", "Socket.io lost connection")


class WebSocketMeta(socketio.AsyncClientNamespace):
    async def on_connect(self):
        print(f"{self.namespace} Connected, Thread ws: {threading.current_thread().getName() }")
        self.set_status(Statuses.CONNECTED, f"{self.uri}")
        await self.sio.emit(event="test_msg", namespace=self.namespace)
        await self.sio.emit(event="ping", data={}, namespace=self.namespace)

    async def on_disconnect(self):
        print(f"{self.namespace} Disconnected, Thread ws: {threading.current_thread().getName() }")
        self.set_status(Statuses.DISCONNECTED, f"{self.uri}")

    async def on_connect_error(self, data):
        print(f"{self.namespace} CONNECTION ERROR, Thread ws: {threading.current_thread().getName() }")

    async def on_hey(self, *args):
        data = ""
        if len(args) > 0:
            data = args[0]
            print(f"Received msg from {data}, Thread ws: {threading.current_thread().getName() }")
        self.set_status(Statuses.CONNECTED, f"{self.uri} {data}")

    def __init__(self, tasks_manager, url, namespace, frame_w, frame_h, async_loop=None):
        socketio.AsyncClientNamespace.__init__(self, namespace)
        self.sio = socketio.AsyncClient(logger=False, engineio_logger=False)
        self.sio.register_namespace(self)
        self.sync_with_server = False
        self.max_wait_timeout = 10
        self.wait_time = 0
        self.status = Statuses.NOT_INITIALIZED

        self.url = "url"
        self.namespace = namespace
        self.uri = self.url + self.namespace
        self.tag = "WS_" + self.namespace[1:min(4, len(self.namespace))] # First 3 characters of the namespace, excluding the "/"

        self.last_emit = datetime.datetime.now()
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.buffer_size = 2
        self.data_to_send = deque([])
        self.enabled = True

        self.fps_counter = FPSCounter()
        self.read_lock = threading.Lock()
        self.main_loop = asyncio.new_event_loop()

        self.tasks_manager = tasks_manager
        # self.connect_task = self.tasks_manager.add_task(self.tag+"Conn", None, self.connection_loop, None, self.read_lock)
        self.send_task = self.tasks_manager.add_task(self.tag, None, self.loop, None, self.read_lock)
        self.multi_threaded = True

    def set_async_loop(self, loop):
        self.main_loop = loop
    #
    # def connection_loop(self, tasks_manager=None, async_loop=None):
    #     if self.status.id != Statuses.CONNECTED.id:
    #         self.update_status(self.main_loop)
    #     time.sleep(3)
    #     return True

    def loop(self, tasks_manager=None, async_loop=None):
        print(f"WebSocket loop not implemented!")
        return False

    def init(self):
        if self.enabled:
            if not self.multi_threaded:
                if self.send_task.is_running():
                    print(f"Stopping {self.send_task.name} background task")
                    self.send_task.stop()
            else:
                if not self.send_task.is_running():
                    print(f"Starting {self.send_task.name} background task")
                    self.send_task.start()
        else:
            if self.send_task.is_running():
                print(f"Stopping {self.send_task.name} background task")
                self.send_task.stop()

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


from .WebSocketMeta import WebSocketMeta
from .WebSocketStatusManager import Statuses
from .WebSocketHandlers import WebSocketHandlers
import time
from ..Utils.DataQueue import DataQueue

class WebSocketInteraction(WebSocketMeta):

    def attach_callbacks(self):
        self.sio.on("connect", handler=WebSocketInteraction.on_connect, namespace=self.namespace)
        self.sio.on("disconnect", handler=WebSocketInteraction.on_disconnect, namespace=self.namespace)
        self.sio.on("connect_error", handler=WebSocketInteraction.on_connect_error, namespace=self.namespace)
        self.sio.on("hey_yo", handler=WebSocketInteraction.on_hey_yo, namespace=self.namespace)
        self.sio.on("webcam_data_out", handler=WebSocketInteraction.on_webcam_data_out, namespace=self.namespace)
        self.sio.on("remote_command", handler=WebSocketInteraction.on_remote_command, namespace=self.namespace)

    async def on_hey(*args):
        global ws_inter
        await WebSocketHandlers.on_msg(ws_inter, *args)

    async def on_connect():
        global ws_inter
        await WebSocketHandlers.on_connect(ws_inter)

    async def on_disconnect():
        global ws_inter
        await WebSocketHandlers.on_disconnect(ws_inter)

    async def on_connect_error(data):
        global ws_inter
        await WebSocketHandlers.on_connect_error(ws_inter, data)

    async def on_webcam_data_out(data):
        global ws_inter
        await WebSocketHandlers.on_frame_received(ws_inter, data)

    async def on_frame_received(data):
        global ws_inter
        await WebSocketHandlers.on_frame_received(ws_inter, data)

    async def on_frame_received_ACK(*args):
        global ws_inter
        await WebSocketHandlers.on_frame_received_ACK(ws_inter, *args)

    async def on_scale_request(*args):
        global ws_inter
        await WebSocketHandlers.on_scale_request(ws_inter, *args)

    async def on_hey_yo(*args):
        global ws_inter
        await WebSocketHandlers.on_msg(ws_inter, *args)

    async def on_remote_command(self, data):
        print(f"Received remote command {data}")
        return self.in_commands_buffer.insert_data(data)

    def get_latest_received_frame(self):
        return self.in_buffer.pop_data()

    def get_last_remote_command(self):
        return self.in_commands_buffer.pop_data()


    def __init__(self, tasks_manager, url, namespace, frame_w, frame_h, executor=None):
        WebSocketMeta.__init__(self, tasks_manager, url, namespace, frame_w, frame_h, executor)
        print(f"Creating websocket interaction")
        self.frame_w = frame_w

        self.frame_h = frame_h

        self.target_framerate = 30
        self.scaling_factor = 1.0
        self.frame_skipping = False
        self.last_file_size = 1
        self.in_commands_buffer = DataQueue(10)

    def create_ws(tasks_manager, url, namespace, frame_w, frame_h, executor=None):
        global ws_inter
        ws_inter = WebSocketInteraction(tasks_manager, url, namespace, frame_w, frame_h, executor)
        ws_inter.attach_callbacks()
        return ws_inter

ws_inter = None



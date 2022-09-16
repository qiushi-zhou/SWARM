import asyncio
import datetime
import threading
from .WebSocketMeta import Status, Statuses, WebSocketMeta, SwarmData
import cv2
import time
import socketio
from collections import deque
from ..Utils.FPSCounter import FPSCounter
import io


class WebSocketInteraction(WebSocketMeta):

    def attach_callbacks(self):
        self.sio.on("connect", handler=WebSocketInteraction.on_connect, namespace=self.namespace)
        self.sio.on("disconnect", handler=WebSocketInteraction.on_disconnect, namespace=self.namespace)
        self.sio.on("connect_error", handler=WebSocketInteraction.on_connect_error, namespace=self.namespace)
        self.sio.on("hey_yo", handler=WebSocketInteraction.on_hey_yo, namespace=self.namespace)
        self.sio.on("webcam_data_out", handler=WebSocketInteraction.on_webcam_data_out, namespace=self.namespace)

    async def on_connect():
        global ws_inter
        print(f"{ws_inter.namespace} Connected, Thread ws: {threading.current_thread().getName() }")
        ws_inter.set_status(Statuses.CONNECTED, f"{ws_inter.uri}")
        await ws_inter.sio.emit(event="test_msg", namespace=ws_inter.namespace)
        await ws_inter.sio.emit(event="ping", data={}, namespace=ws_inter.namespace)

    async def on_disconnect():
        global ws_inter
        print(f"{ws_inter.namespace} Disconnected, Thread ws: {threading.current_thread().getName() }")
        ws_inter.set_status(Statuses.DISCONNECTED, f"{ws_inter.uri}")

    async def on_connect_error(data):
        global ws_inter
        print("Error connecting to video stream socket")

    async def on_hey_yo(*args):
        global ws_inter
        if len(args) > 0:
            data = args[0]
            print(f"Received hey yo from {data}, Thread ws: {threading.current_thread().getName() }")
        # self.set_status(Statuses.CONNECTED, f"{self.uri} {data}")

    def get_latest_frame(self):
        # print(f"Getting latest stream frame {len(self.in_buffer)}")
        if len(self.in_buffer) > 0:
            self.out_fps_counter.update(1)
            return self.in_buffer.popleft()
        return None


    async def on_webcam_data_out(data):
        global ws_inter
        ws_inter.in_fps_counter.update(1)
        if len(ws_inter.in_buffer) > ws_inter.in_buffer_size:
            print(f"{ws_inter.namespace} received buffer full!")
            return
        else:
            ws_inter.in_buffer.append(data)
        # print(f"{self.namespace} Webcam frame out, Thread ws: {threading.current_thread().getName() }")

    async def background_task(self):
        global ws_inter
        pass

    def __init__(self, tasks_manager, url, namespace, frame_w, frame_h):
        WebSocketMeta.__init__(self, tasks_manager, url, namespace, frame_w, frame_h)
        print(f"Creating websocket interaction")
        self.frame_w = frame_w
        self.frame_h = frame_h

        self.target_framerate = 30
        self.scaling_factor = 1.0
        self.frame_skipping = False
        self.last_file_size = 1

    def create_ws(tasks_manager, url, namespace, frame_w, frame_h, async_loop=None):
        global ws_inter
        ws_inter = WebSocketInteraction(tasks_manager, url, namespace, frame_w, frame_h)
        ws_inter.attach_callbacks()
        return ws_inter

ws_inter = None



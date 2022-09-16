import asyncio
import datetime
import threading
from .WebSocketMeta import Status, Statuses, WebSocketMeta, SwarmData
import cv2
import time
import socketio
import socketio
from collections import deque
from ..Utils.FPSCounter import FPSCounter
import io


class WebSocketVideoStream(WebSocketMeta):
    def attach_callbacks(self):
        self.sio.on("connect", handler=WebSocketVideoStream.on_connect, namespace=self.namespace)
        self.sio.on("disconnect", handler=WebSocketVideoStream.on_disconnect, namespace=self.namespace)
        self.sio.on("connect_error", handler=WebSocketVideoStream.on_connect_error, namespace=self.namespace)
        self.sio.on("hey", handler=WebSocketVideoStream.on_hey, namespace=self.namespace)
        self.sio.on("frame_received", handler=WebSocketVideoStream.on_frame_received, namespace=self.namespace)
        self.sio.on("scale_request", handler=WebSocketVideoStream.on_scale_request, namespace=self.namespace)
        self.sio.on("op_frame_new", handler=WebSocketVideoStream.on_op_frame_new, namespace=self.namespace)

    async def on_hey(*args):
        global ws_vs
        data = ""
        if len(args) > 0:
            data = args[0]
            print(f"Received msg from {data}, Thread ws: {threading.current_thread().getName() }")
        ws_vs.set_status(Statuses.CONNECTED, f"{ws_vs.uri} {data}")
    async def on_connect():
        global ws_vs
        print(f"{ws_vs.namespace} Connected, Thread ws: {threading.current_thread().getName() }")
        ws_vs.set_status(Statuses.CONNECTED, f"{ws_vs.uri}")
        await ws_vs.sio.emit(event="test_msg", namespace=ws_vs.namespace)
        await ws_vs.sio.emit(event="ping", data={}, namespace=ws_vs.namespace)

    async def on_disconnect():
        global ws_vs
        print(f"{ws_vs.namespace} Disconnected, Thread ws: {threading.current_thread().getName() }")
        ws_vs.set_status(Statuses.DISCONNECTED, f"{ws_vs.uri}")

    async def on_connect_error(data):
        global ws_vs
        print("Error connecting to video stream socket")

    async def on_frame_received(*args):
        global ws_vs
        print(f"elapsed: {(ws_vs.last_emit - datetime.datetime.now()).microseconds / 1000}")
        ws_vs.set_status(Statuses.CONNECTED, f"Frame received", debug=False)

    async def on_scale_request(*args):
        global ws_vs
        if len(args) > 0:
            data = args[0]
            ws_vs.set_scaling(float(data.get('scaling_factor', 1.0)))

    async def on_op_frame_new(*args):
        global ws_vs
        data = ""
        if len(args) > 0:
            data = args[0]
        ws_vs.set_status(Statuses.CONNECTED, f"{ws_vs.uri} {data}", debug=False)

    async def send_frame_async(self, swarm_data):
        global ws_vs
        data_json = swarm_data.get_json()
        if ws_vs.is_ready():
            try:
                data_json["frame_time"] = ws_vs.fps_counter.time_since_last_frame()
                data_json["time"] = f"{datetime.datetime.now()}"
                data_json["fps"] = ws_vs.target_framerate
                await ws_vs.send_image_data(data_json)
                ws_vs.fps_counter.update(1)
            except Exception as e:
                print(f"Exception sending data! {ws_vs.namespace} {e}")

    async def background_task(self):
        global ws_vs
        if ws_vs.status.id != Statuses.CONNECTED.id:
            ws_vs.fps_counter.reset()
        if ws_vs.frame_skipping:
            if ws_vs.fps_counter.fps > ws_vs.target_framerate:
                ws_vs.fps_counter.update()
        try:
            if len(ws_vs.out_buffer) > 0:
                swarm_data = ws_vs.out_buffer.popleft()
                if swarm_data is not None:
                    await self.send_frame_async(swarm_data)
            else:
                time.sleep(0.001)
        except Exception as e:
            print(f"Error running send loop {ws_vs.namespace} : {e}")

    async def send_graph_data(self, swarm_data):
        global ws_vs
        data_json = swarm_data.get_json()
        # if ws_vs.status.id != Statuses.CONNECTED.id:
        #     return False
        try:
            await ws_vs.sio.emit(event='graph_data', data=swarm_data, namespace=ws_vs.namespace)
        except Exception as e:
            print(f"Error Sending graph data to WebSocket {ws_vs.namespace}  {e}")
            ws_vs.set_status(Statuses.DISCONNECTED, f"{e}")
        return True

    def send_frame(self, swarm_data):
        global ws_vs
        data_json = swarm_data.get_json()
        ws_vs.main_loop.run_until_complete(ws_vs.send_image_data(data_json))
        ws_vs.fps_counter.update(1)

    async def send_image_data(self, dict_data):
        global ws_vs
        try:
            if ws_vs.sync_with_server:
                ws_vs.set_status(Statuses.WAITING, "Send_data", debug=False)
                ws_vs.last_emit = datetime.datetime.now()
                await ws_vs.sio.emit(event='gallery_stream', data=dict_data, namespace=ws_vs.namespace, callback=frame_received)
            else:
                print(f"Emitting 'gallery_stream_in' on {ws_vs.namespace} from Thread ws: {threading.current_thread().getName() }")
                # print(dict_data)
                await ws_vs.sio.emit(event='gallery_stream_in', data=dict_data, namespace=ws_vs.namespace)
        except Exception as e:
            print(f"Error Sending frame data to WebSocket {ws_vs.namespace}  {e}")
            ws_vs.set_status(Statuses.DISCONNECTED, f"{e}")
        return True

    def set_scaling(self, scaling_factor):
        global ws_vs
        ws_vs.scaling_factor = scaling_factor

    def enqueue_frame(self, cv2_frame, cameras_data, draw=False):
        global ws_vs
        if ws_vs.scaling_factor < 1:
            swarm_data = SwarmData(cv2.resize(cv2_frame, (int(ws_vs.frame_w * ws_vs.scaling_factor), int(ws_vs.frame_h * ws_vs.scaling_factor))), cameras_data)
        else:
            swarm_data = SwarmData(cv2_frame, cameras_data)
        if ws_vs.multi_threaded:
            if len(ws_vs.out_buffer) >= ws_vs.out_buffer_size:
                return
            ws_vs.out_buffer.append(swarm_data)
        else:
            ws_vs.send_frame(swarm_data)

    def __init__(self, tasks_manager, url, namespace, frame_w, frame_h, async_loop=None):
        WebSocketMeta.__init__(self, tasks_manager, url, namespace, frame_w, frame_h)

        self.frame_w = frame_w
        self.frame_h = frame_h

        self.fps_counter = FPSCounter()
        self.target_framerate = 60
        self.scaling_factor = 1.0
        self.frame_skipping = False
        self.last_file_size = 1

    def create_ws(tasks_manager, url, namespace, frame_w, frame_h, async_loop=None):
        global ws_vs
        ws_vs = WebSocketVideoStream(tasks_manager, url, namespace, frame_w, frame_h)
        ws_vs.attach_callbacks()
        return ws_vs

ws_vs = None

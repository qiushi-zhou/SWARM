import socketio
import threading
import datetime
import cv2
import asyncio
from .WebSocketHandlers import WebSocketHandlers
from ..Utils.DataQueue import DataQueue
from .SwarmData import SwarmData
from .WebSocketStatusManager import WebSocketStatusManager
import time


class WebSocketMeta:
    def __init__(self, tasks_manager, url, namespace, frame_w, frame_h, threadpool_executor=None):
        self.sio = socketio.AsyncClient(logger=False, engineio_logger=False)
        self.enabled = True
        self.sync_with_server = False

        self.status_manager = WebSocketStatusManager(self)

        self.url = "url"
        self.namespace = namespace
        self.uri = self.url + self.namespace
        self.tag = "WS_" + self.namespace[1:min(4, len(self.namespace))] # First 3 characters of the namespace, excluding the "/"

        self.emit_event = 'frame_data_in'

        self.multi_threaded = True
        self.tasks_manager = tasks_manager
        self.task_running = False
        self.async_loop = asyncio.new_event_loop()
        self.executor = threadpool_executor
        # if self.executor is None:
        #     self.executor = ThreadPoolExecutor(3)  #Create a ProcessPool with 2 processes

        self.frame_w = frame_w
        self.frame_h = frame_h

        self.target_framerate = 30
        self.scaling_factor = 0.6
        self.last_file_size = 1

        self.out_buffer = DataQueue(2, self.target_framerate)
        self.in_buffer = DataQueue(60)

        self.last_emit = datetime.datetime.now()


    def attach_callbacks(self):
        print(f"Attach callbacks not implemented!")
        return False

    def main_loop_starter(self):
        self.async_loop.run_until_complete(self.main_loop())

    async def main_loop(self):
        try:
            while self.task_running:
                await self.status_manager.update_status()
                if self.status_manager.is_ready():
                    await self.background_task()
                    await asyncio.sleep(0)
        except Exception as e:
            print(f"Exception in {self.namespace} loop: {e}")

    async def background_task(self):
        # print(f"FPS: {self.out_buffer.fps()} > {self.target_framerate}")
        if not self.status_manager.is_ready():
            self.out_buffer.fps_counter.reset()
        if self.out_buffer.fps() > self.target_framerate:
            self.out_buffer.discard_next()
            return
        try:
            await self.send_data()
        except Exception as e:
            print(f"Error running send loop {self.namespace} : {e}")
        await asyncio.sleep(0.00001)
        # print(f"WebSocket loop not implemented!")

    def start_async_task(self):
        if not self.task_running:
            self.in_buffer.clear()
            self.out_buffer.clear()
            print(f"Starting {self.namespace} background task")
            self.task_running = True
            self.async_loop.run_in_executor(self.executor, self.main_loop_starter)

    def stop_async_task(self):
        if self.task_running:
            print(f"Stopping {self.namespace} background task")
            self.task_running = False

    def check_enable(self):
        if self.enabled:
            if self.multi_threaded:
                self.start_async_task()
            else:
                self.stop_async_task()
        else:
            self.stop_async_task()

    def update_config(self, data):
        self.sync_with_server = data.get("sync_with_server", False)
        self.target_framerate = data.get("target_framerate", 30)
        self.enabled = data.get("enabled", self.enabled)
        # self.frame_scaling = data.get("frame_scaling", False)
        # self.adaptive_scaling = data.get("frame_adaptive", False)
        # self.min_frame_scaling = data.get("min_frame_scaling", 1)
        self.scaling_factor = data.get("fixed_frame_scaling", self.scaling_factor)
        # self.max_frame_scaling = self.fixed_frame_scaling
        # self.send_frames = data.get("send_frames", self.send_frames)
        # self.frame_skipping = data.get("frame_skip", False)
        url = data.get("url", self.url)
        namespace = data.get("namespace", self.namespace)
        self.emit_event = data.get('emit_event', self.emit_event)
        if url != self.url or namespace != self.namespace:
            print(f"WebSocket URI changed from {self.url}{self.namespace} to {url}{namespace}, reconnecting")
            self.url = url
            self.namespace = namespace
            self.uri = f"{url}{namespace}"
        self.check_enable()
            # if not self.connect_task.is_running():
            #     self.connect_task.start()

    def set_status(self, new_status, extra="", debug=True):
        self.status_manager.set_status(new_status, extra)

    def is_ready(self):
        return self.status_manager.is_ready()

    async def send_graph_data(self, swarm_data):
        data_json = swarm_data.get_json()
        try:
            await self.sio.emit(event='graph_data', data=swarm_data, namespace=self.namespace)
        except Exception as e:
            print(f"Error Sending graph data to WebSocket {self.namespace}  {e}")
            self.status_manager.set_disconnected(f"{e}")
        return True

    def set_scaling(self, scaling_factor):
        self.scaling_factor = scaling_factor

    def enqueue_frame(self, frame, cameras_data):
        if frame is None:
            return
        if self.scaling_factor < 0.99:
            frame = cv2.resize(frame, (int(self.frame_w * self.scaling_factor), int(self.frame_h * self.scaling_factor)))
        swarm_data = SwarmData(frame, cameras_data)
        self.out_buffer.insert_data(swarm_data)
        if not self.multi_threaded:
            self.send_data()

    async def send_data(self):
        try:
            time_since_last_pop = self.out_buffer.time_since_last_pop()
            swarm_data = self.out_buffer.pop_data()
            if swarm_data is None:
                return
            data_json = swarm_data.get_json()
            data_json["frame_time"] = time_since_last_pop
            data_json["time"] = f"{datetime.datetime.now()}"
            data_json["fps"] = self.out_buffer.fps()
            data_json["target_fps"] = self.target_framerate
            # print(f"Emitting {'SYNCD' if self.sync_with_server else ''} {self.emit_event} on {self.namespace} from Thread ws: {threading.current_thread().getName()}. \tFPS: {self.out_buffer.fps()}")
            # print(data_json)
            if self.sync_with_server:
                self.status_manager.set_waiting("Sending data")
                self.last_emit = datetime.datetime.now()
                await self.sio.emit(event=self.emit_event, data=data_json, namespace=self.namespace, callback=WebSocketHandlers.on_frame_received_ACK)
            else:
                await self.sio.emit(event=self.emit_event, data=data_json, namespace=self.namespace)
        except Exception as e:
            print(f"Error Sending frame data to WebSocket {self.namespace}  {e}")
            self.status_manager.set_disconnected(f"{e}")

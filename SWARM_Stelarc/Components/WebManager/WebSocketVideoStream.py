import asyncio
import datetime
import threading
from .WebSocketMeta import Status, Statuses, WebSocketMeta, SwarmData
import cv2
import time
import socketio


class WebSocketVideoStream(WebSocketMeta):
    async def on_frame_received(self, *args):
        print(f"elapsed: {(self.last_emit - datetime.datetime.now()).microseconds / 1000}")
        self.set_status(Statuses.CONNECTED, f"Frame received", debug=False)

    async def on_scale_request(self, *args):
        if len(args) > 0:
            data = args[0]
            self.set_scaling(float(data.get('scaling_factor', 1.0)))

    async def on_op_frame_new(self, *args):
        data = ""
        if len(args) > 0:
            data = args[0]
        self.set_status(Statuses.CONNECTED, f"{self.uri} {data}", debug=False)

    def loop(self, tasks_manager=None, async_loop=None):
        if self.status.id != Statuses.CONNECTED.id:
            self.update_status(self.main_loop)
            time.sleep(1)
            self.fps_counter.reset()
            return True
        if self.frame_skipping:
            if self.fps_counter.fps > self.target_framerate:
                self.fps_counter.update()
                time.sleep(0.1)
                return True
        try:
            if len(self.data_to_send) > 0:
                swarm_data = self.data_to_send.popleft()
                if swarm_data is not None:
                    self.main_loop.run_until_complete(self.send_frame_async(swarm_data))
            else:
                time.sleep(0.001)
        except Exception as e:
            print(f"Error running send loop {self.namespace} : {e}")
        return True

    async def send_graph_data(self, swarm_data):
        data_json = swarm_data.get_json()
        # if self.status.id != Statuses.CONNECTED.id:
        #     return False
        try:
            await self.sio.emit(event='graph_data', data=swarm_data, namespace=self.namespace)
        except Exception as e:
            print(f"Error Sending graph data to WebSocket {self.namespace}  {e}")
            self.set_status(Statuses.DISCONNECTED, f"{e}")
        return True

    def send_frame(self, swarm_data):
        data_json = swarm_data.get_json()
        self.main_loop.run_until_complete(self.send_image_data(data_json))
        self.fps_counter.update(1)

    async def send_frame_async(self, swarm_data):
        data_json = swarm_data.get_json()
        if self.is_ready():
            try:
                data_json["frame_time"] = self.fps_counter.time_since_last_frame()
                data_json["time"] = f"{datetime.datetime.now()}"
                data_json["fps"] = self.target_framerate
                await self.send_image_data(data_json)
                self.fps_counter.update(1)
            except Exception as e:
                print(f"Exception sending data! {self.namespace} {e}")

    async def send_image_data(self, dict_data):
        try:
            if self.sync_with_server:
                self.set_status(Statuses.WAITING, "Send_data", debug=False)
                self.last_emit = datetime.datetime.now()
                await self.sio.emit(event='gallery_stream', data=dict_data, namespace=self.namespace, callback=frame_received)
            else:
                print(f"Emitting 'gallery_stream_in' on {self.namespace} from Thread ws: {threading.current_thread().getName() }")
                # print(dict_data)
                await self.sio.emit(event='gallery_stream_in', data=dict_data, namespace=self.namespace)
        except Exception as e:
            print(f"Error Sending frame data to WebSocket {self.namespace}  {e}")
            self.set_status(Statuses.DISCONNECTED, f"{e}")
        return True

    def set_scaling(self, scaling_factor):
        self.scaling_factor = scaling_factor

    def enqueue_frame(self, cv2_frame, cameras_data, draw=False):
        if self.scaling_factor < 1:
            swarm_data = SwarmData(cv2.resize(cv2_frame, (int(self.frame_w * self.scaling_factor), int(self.frame_h * self.scaling_factor))), cameras_data)
        else:
            swarm_data = SwarmData(cv2_frame, cameras_data)
        if self.multi_threaded:
            if len(self.data_to_send) >= self.buffer_size:
                return
            self.data_to_send.append(swarm_data)
        else:
            self.send_frame(swarm_data)

            # self.main_loop.run_until_complete(self.send_frame_async(swarm_data))

    #
    # def update_scaling(self):
    #     if self.frame_scaling:
    #         if self.adaptive_scaling:
    #             if self.fps_counter.fps < self.target_framerate:
    #                 self.current_frame_scaling = min(self.min_frame_scaling, self.current_frame_scaling - self.scaling_step)
    #             else:
    #                 self.current_frame_scaling = max(self.max_frame_scaling, self.current_frame_scaling + self.scaling_step)
    #         else:
    #             self.current_frame_scaling = self.fixed_frame_scaling
    #     else:
    #         self.current_frame_scaling = 1.0
    #     return self.current_frame_scaling

    def __init__(self, tasks_manager, url, namespace, frame_w, frame_h, async_loop=None):
        WebSocketMeta.__init__(self, tasks_manager, url, namespace, frame_w, frame_h, async_loop)
        self.target_framerate = 60
        self.scaling_factor = 1.0
        self.frame_skipping = False
        self.last_file_size = 1

from .WebSocketMeta import WebSocketMeta
from .WebSocketHandlers import WebSocketHandlers
from .SwarmData import SwarmData
import datetime
import cv2
from ..Utils.utils import *
from ..Utils.DataQueue import DataQueue


class WebSocketVideoStreamOut(WebSocketMeta):
    def attach_callbacks(self):
        self.sio.on("connect", handler=WebSocketVideoStreamOut.on_connect, namespace=self.namespace)
        self.sio.on("disconnect", handler=WebSocketVideoStreamOut.on_disconnect, namespace=self.namespace)
        self.sio.on("connect_error", handler=WebSocketVideoStreamOut.on_connect_error, namespace=self.namespace)
        self.sio.on("hey", handler=WebSocketVideoStreamOut.on_hey, namespace=self.namespace)
        self.sio.on("frame_received", handler=WebSocketVideoStreamOut.on_frame_received, namespace=self.namespace)
        self.sio.on("scale_request", handler=WebSocketVideoStreamOut.on_scale_request, namespace=self.namespace)
        # self.sio.on("op_frame_new", handler=WebSocketVideoStreamOut.on_op_frame_new, namespace=self.namespace)

    async def on_hey(*args):
        global ws_vs
        await WebSocketHandlers.on_msg(ws_vs, *args)

    async def on_connect():
        global ws_vs
        await WebSocketHandlers.on_connect(ws_vs)

    async def on_disconnect():
        global ws_vs
        ws_vs.config_update_sent = False
        await WebSocketHandlers.on_disconnect(ws_vs)

    async def on_connect_error(data):
        global ws_vs
        ws_vs.config_update_sent = False
        await WebSocketHandlers.on_connect_error(ws_vs, data)

    async def on_frame_received(*args):
        global ws_vs
        await WebSocketHandlers.on_frame_received(ws_vs, *args)

    async def on_frame_received_ACK(*args):
        global ws_vs
        await WebSocketHandlers.on_frame_received_ACK(ws_vs, *args)

    async def on_scale_request(*args):
        global ws_vs
        await WebSocketHandlers.on_scale_request(ws_vs, *args)

    async def send_graph_data(self, swarm_data):
        data_json = swarm_data.get_json()['graph_data']
        try:
            await self.sio.emit(event='graph_data', data=swarm_data, namespace=self.namespace)
        except Exception as e:
            print(f"Error Sending graph data to WebSocket {self.namespace}  {e}")
            self.status_manager.set_disconnected(f"{e}")
        return True

    def set_scaling(self, scaling_factor):
        self.scaling_factor = scaling_factor

    def enqueue_behaviour_data(self, swarm_data):
        data = {}
        data['swarm_data'] = swarm_data
        data['datetime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        self.behaviour_data_out.insert_data(data)

    def enqueue_frame(self, frame, cameras_data, swarm_data):
        if frame is None:
            return
        if self.scaling_factor < 0.99:
            frame = cv2.resize(frame, (int(self.frame_w * self.scaling_factor), int(self.frame_h * self.scaling_factor)))
        data = SwarmData(frame, cameras_data, swarm_data)
        if 'current_behavior' in data.get_json()['swarm_data'].keys():
            self.app_logger.app(f"Keys to send? {'current_behavior' in data.get_json()['swarm_data'].keys()} - {data.get_json()['datetime']}")
        self.out_buffer.insert_data(data)
        if not self.multi_threaded:
            self.send_data()

    async def send_data(self):
        if self.app_config_data is not None and not self.config_update_sent:
            try:
                await self.sio.emit(event='app_config_update', data=self.app_config_data, namespace=self.namespace)
                self.app_logger.critical(f"Sending app_config_data")
                self.config_update_sent = True
            except Exception as e:
                self.app_logger.critical(f"Error sending app_config_data update {e}")
        behaviour_data = self.behaviour_data_out.pop_data()
        if behaviour_data is not None:
            await self.sio.emit(event='behaviour_update', data=behaviour_data, namespace=self.namespace)
        try:
            time_since_last_pop = self.out_buffer.time_since_last_pop()
            swarm_data = self.out_buffer.pop_data()
            if swarm_data is None:
                return

            data_json = swarm_data.get_json()
            # if 'current_behavior' in data_json['swarm_data'].keys():
            #     self.app_logger.app(f"Sending curr update? {'current_behavior' in data_json['swarm_data'].keys()} - {data_json['datetime']}")
            # self.app_logger.app(f"Sending curr update? {'current_behavior' in data_json['swarm_data'].keys()} - {data_json['datetime']}")
            data_json["frame_time"] = time_since_last_pop
            data_json["time"] = f"{datetime.datetime.now()}"
            data_json["fps"] = self.out_buffer.fps()
            data_json["target_fps"] = self.target_framerate
            # print(f"Emitting {'SYNCD' if self.sync_with_server else ''} {self.emit_event} on {self.namespace} from Thread ws: {threading.current_thread().getName()}. \tFPS: {self.out_buffer.fps()}")
            # print(data_json)
            # behaviour_data = data_json['swarm_data'].get('')

            # self.app_logger.critical(f"Sending update {data_json['swarm_data'].keys()}")
            if self.sync_with_server:
                self.status_manager.set_waiting("Sending data")
                self.last_emit = datetime.datetime.now()
                await self.sio.emit(event=self.emit_event, data=data_json, namespace=self.namespace, callback=WebSocketHandlers.on_frame_received_ACK)
            else:
                await self.sio.emit(event=self.emit_event, data=data_json, namespace=self.namespace)
        except Exception as e:
            print(f"Error Sending frame data to WebSocket {self.ws_id} {self.namespace}  {e}")
            self.config_update_sent = False
            self.status_manager.set_disconnected(f"{e}")
        
    def send_config_update(self, data):
        self.config_update_sent = False
        data = serialize_datetime(data)
        self.app_config_data = data

    def __init__(self, app_logger, ws_id, tasks_manager, url, namespace, frame_w, frame_h, executor=None):
        WebSocketMeta.__init__(self, app_logger, ws_id, tasks_manager, url, namespace, frame_w, frame_h, executor)
        self.app_config_data = None
        self.behaviour_data_in = DataQueue(10)
        self.behaviour_data_out = DataQueue(10)

    def create_ws(app_logger, ws_id, tasks_manager, url, namespace, frame_w, frame_h, executor=None):
        global ws_vs
        ws_vs = WebSocketVideoStreamOut(app_logger, ws_id, tasks_manager, url, namespace, frame_w, frame_h, executor)
        ws_vs.attach_callbacks()
        return ws_vs

ws_vs = None

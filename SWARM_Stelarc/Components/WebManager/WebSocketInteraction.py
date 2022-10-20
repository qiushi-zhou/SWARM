
from .WebSocketMeta import WebSocketMeta
from .WebSocketStatusManager import Statuses
from .WebSocketHandlers import WebSocketHandlers
import time
import datetime
from ..Utils.DataQueue import DataQueue

class WebSocketInteraction(WebSocketMeta):

    def attach_callbacks(self):
        self.sio.on("connect", handler=WebSocketInteraction.on_connect, namespace=self.namespace)
        self.sio.on("disconnect", handler=WebSocketInteraction.on_disconnect, namespace=self.namespace)
        self.sio.on("connect_error", handler=WebSocketInteraction.on_connect_error, namespace=self.namespace)
        self.sio.on("hey_yo", handler=WebSocketInteraction.on_hey_yo, namespace=self.namespace)
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

    async def on_hey_yo(*args):
        global ws_inter
        await WebSocketHandlers.on_msg(ws_inter, *args)

    async def on_remote_command(self, data):
        print(f"Received remote command {data}")
        return self.in_buffer.insert_data(data)

    def get_last_remote_command(self):
        remote_command_data = self.in_buffer.peek()
        if remote_command_data is not None:
            return remote_command_data.get("name", None)

    def pop_last_command(self):
        self.out_buffer.insert(self.in_buffer.pop_data())

    async def send_data(self):
        try:
            remote_command_data = self.out_buffer.pop_data()
            if remote_command_data is None:
                return
            data_json = {}
            data_json['remote_command'] = remote_command_data
            data_json["executed_time"] = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            # print(f"Emitting {'SYNCD' if self.sync_with_server else ''} {self.emit_event} on {self.namespace} from Thread ws: {threading.current_thread().getName()}. \tFPS: {self.out_buffer.fps()}")
            # print(data_json)
            await self.sio.emit(event=self.emit_event, data=data_json, namespace=self.namespace)
        except Exception as e:
            print(f"Error Sending remote command data to WebSocket {self.ws_id} {self.namespace}  {e}")
            self.status_manager.set_disconnected(f"{e}")


    def __init__(self, app_logger, ws_id, tasks_manager, url, namespace, frame_w, frame_h, executor=None):
        WebSocketMeta.__init__(self, app_logger, ws_id, tasks_manager, url, namespace, frame_w, frame_h, executor)
        print(f"Creating websocket interaction {ws_id}")

    def create_ws(app_logger, ws_id, tasks_manager, url, namespace, frame_w, frame_h, executor=None):
        global ws_inter
        ws_inter = WebSocketInteraction(app_logger, ws_id, tasks_manager, url, namespace, frame_w, frame_h, executor)
        ws_inter.attach_callbacks()
        return ws_inter

ws_inter = None



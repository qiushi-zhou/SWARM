from .WebSocketMeta import WebSocketMeta
import time
from .WebSocketHandlers import WebSocketHandlers


class WebSocketVideoStream(WebSocketMeta):
    def attach_callbacks(self):
        self.sio.on("connect", handler=WebSocketVideoStream.on_connect, namespace=self.namespace)
        self.sio.on("disconnect", handler=WebSocketVideoStream.on_disconnect, namespace=self.namespace)
        self.sio.on("connect_error", handler=WebSocketVideoStream.on_connect_error, namespace=self.namespace)
        self.sio.on("hey", handler=WebSocketVideoStream.on_hey, namespace=self.namespace)
        self.sio.on("frame_received", handler=WebSocketVideoStream.on_frame_received, namespace=self.namespace)
        self.sio.on("scale_request", handler=WebSocketVideoStream.on_scale_request, namespace=self.namespace)
        # self.sio.on("op_frame_new", handler=WebSocketVideoStream.on_op_frame_new, namespace=self.namespace)

    async def on_hey(*args):
        global ws_vs
        await WebSocketHandlers.on_msg(ws_vs, *args)

    async def on_connect():
        global ws_vs
        await WebSocketHandlers.on_connect(ws_vs)

    async def on_disconnect():
        global ws_vs
        await WebSocketHandlers.on_disconnect(ws_vs)

    async def on_connect_error(data):
        global ws_vs
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

    def __init__(self, tasks_manager, url, namespace, frame_w, frame_h):
        WebSocketMeta.__init__(self, tasks_manager, url, namespace, frame_w, frame_h)

    def create_ws(tasks_manager, url, namespace, frame_w, frame_h):
        global ws_vs
        ws_vs = WebSocketVideoStream(tasks_manager, url, namespace, frame_w, frame_h)
        ws_vs.attach_callbacks()
        return ws_vs

ws_vs = None

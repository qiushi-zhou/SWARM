import socketio
import time
import io
import datetime
import math
import asyncio
import json
import base64
import cv2
import pygame

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
    pass


Statuses.NOT_INITIALIZED = Status(-1, "NOT INITIALIZED", "Socket.io created but not initialized")
Statuses.INITIALIZED = Status(0, "INITIALIZED", "Socket.io setup but not connected")
Statuses.CONNECTING = Status(1, "CONNECTING", "Socket.io is trying to connect")
Statuses.CONNECTED = Status(2, "CONNECTED", "Socket.io connected")
Statuses.WAITING = Status(3, "WAITING", "Socket.io connected")
Statuses.DISCONNECTED = Status(4, "DISCONNECTED", "Socket.io lost connection")

# sio = socketio.AsyncClient(logger=True, engineio_logger=True)
sio = socketio.Client()

# @sio.event(namespace='/visualization')
def connect():
    global ws
    ws.set_status(Statuses.CONNECTED, f"{ws.uri}")


# @sio.event(namespace='/visualization')
def connect_error(data):
    global ws
    print(f"CONNECTION ERROR!")
    ws.set_status(Statuses.DISCONNECTED, f"{ws.uri} {data}")


# @sio.event(namespace='/visualization')
def frame_received(*args):
    global ws
    data = ""
    if len(args) > 0:
        data = args[0]
        # print(f"Received ACK from server{data}")
    ws.set_status(Statuses.CONNECTED, f"Frame received", debug=True)


# @sio.event(namespace='/visualization')
def op_frame_new(*args):
    global ws
    if len(args) > 0:
        data = args[0]
        # print(f"Received op_frame_new from {data}")
    ws.set_status(Statuses.CONNECTED, f"{ws.uri} {data}", debug=False)


# @sio.event(namespace='/visualization')
def disconnect():
    global ws
    ws.set_status(Statuses.DISCONNECTED, f"{ws.uri}")


# @sio.event(namespace='/visualization')
def hey(*args):
    global ws
    if len(args) > 0:
        data = args[0]
        print(f"Received msg from {data}")
    ws.set_status(Statuses.CONNECTED, f"{ws.uri} {data}")


class WebSocket:
    def __init__(self):
        global sio
        self.sync_with_server = False
        self.max_wait_timeout = 10
        self.wait_time = 0
        self.sio = sio
        self.tag = "WebSocket"
        self.status = Statuses.NOT_INITIALIZED
        self.url = ""
        self.namespace = ""
        self.uri = self.url + self.namespace

    def init(self):
        self.set_status(Statuses.DISCONNECTED, {self.uri})
        self.attach_callbacks()
        self.update_status()
        self.send_msg()

    def attach_callbacks(self):
        global sio
        sio.on('connect', handler=connect, namespace=self.namespace)
        sio.on('connect_error', handler=connect_error, namespace=self.namespace)
        sio.on('hey', handler=hey, namespace=self.namespace)
        # sio.on('frame_received', handler=frame_received, namespace=self.namespace)
        sio.on('op_frame_new', handler=op_frame_new, namespace=self.namespace)
        sio.on('disconnect', handler=disconnect, namespace=self.namespace)

    def set_status(self, new_status, extra, debug=True):
        if debug:
            print(f"{self.tag} {self.status.name} -> {new_status.name}, {extra}")
        self.status = new_status
        self.status.extra = extra

    def update_config(self, data):
        self.sync_with_server = data.get("ws_sync_with_server", False)
        url = data.get("ws_url", self.url)
        recreate = url != self.url
        namespace = data.get("ws_namespace", self.namespace)
        recreate = recreate or namespace != self.namespace
        if recreate:
            print(f"WebSocket URI changed from {self.url}{self.namespace} to {url}{namespace}, reconnecting")
            self.url = url
            self.namespace = namespace
            self.uri = url + namespace
            self.init()

    def update_status(self):
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
                self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=1)
                # time.sleep(1) # Otherwise it might get stuck in a loop as the status will change to connected WHILE it was in the "sio.connected" else
                return False
            else:
                self.set_status(Statuses.DISCONNECTED, self.uri)
            return False

    def is_ready(self):
        return self.status.id == Statuses.CONNECTED.id

    def send_msg(self):
        print(f"Sending msg websocket")
        self.sio.emit(event='test_msg', namespace=self.namespace)

    def send_data(self, dict_data):
        if self.status.id != Statuses.CONNECTED.id:
            return False
        try:
            self.set_status(Statuses.WAITING, "Send_data", debug=True)
            self.sio.emit(event='op_frame', data=dict_data, namespace=self.namespace, callback=frame_received)
        except Exception as e:
            print(f"Error Sending frame data to WebSocket {e}")
            self.set_status(Statuses.DISCONNECTED, f"{e}")
        return True

ws = WebSocket()

import socketio
import threading
import time
import io
import datetime
import math
import asyncio
import json
import base64

class WebSocket:
    class WebSocketStatus:
      def __init__(self, _id, name, description):
        self.id = _id
        self.name = name
        self.description = description
        self.extra = ''
        
      def get_dbg_text(self):
        return f"{self.name}: {self.description} - {self.extra}"
      
    statuses = {
      "NOT INITIALIZED":  WebSocketStatus(-1, "NOT INITIALIZED", "Socket.io created but not initialized"),
      "INITIALIZED":      WebSocketStatus(0, "INITIALIZED", "Socket.io setup but not connected"),
      "CONNECTED":        WebSocketStatus(1, "CONNECTED", "Socket.io connected"),
      "CONNECTING":       WebSocketStatus(2, "CONNECTING", "Socket.io is trying to connect"),
      "DISCONNECTED":     WebSocketStatus(3, "DISCONNECTED", "Socket.io lost connection")
    }
      
    def __init__(self):
        self.tag = "WebSocket"
        self.status = self.statuses["NOT INITIALIZED"]
        # self.sio = socketio.Client(logger=True, engineio_logger=True)
        self.sio = socketio.AsyncClient()
        self.async_loop = asyncio.get_event_loop()    
        self.url = ""
        self.namespace = ""
        self.uri = self.url + self.namespace
        self.last_file_size = -1
        self.attach_callbacks()
        # self.do_async(self.attach_callbacks)
        
    def attach_callbacks(self):
      self.sio.on('connect', self.connect, namespace=self.namespace)
      self.sio.on('hey', self.handle_msg, namespace=self.namespace)
      self.sio.on('disconnect', self.disconnect, namespace=self.namespace)      
    
    def set_status(self, new_status_key, extra, debug=True):
      new_status = self.statuses[new_status_key]
      if debug:
        print(f"{self.tag} {self.status.name} -> {new_status.name}, {extra}")
      self.status = new_status
      self.status.extra = extra
        
    def update_config(self, data):
        url = data.get("ws_url", self.url)
        recreate = url != self.url
        namespace = data.get("ws_namespace", self.namespace)
        recreate = recreate or namespace != self.namespace
        if recreate:
          print(f"WebSocket URI changed from {self.url}{self.namespace} to {url}{namespace}, reconnecting")
          self.url = url
          self.namespace = namespace
          self.uri = url + namespace 
    
    def do_async(self, async_function, *args, **kwargs):
      try:
          self.async_loop.run_until_complete(async_function(*args, **kwargs))
      except Exception as e:
          print(f"Error running WebSocket async function: {e}")
      
    def encode_image_data(self, image_data):
        img_str = base64.b64encode(image_data)
        return "data:image/jpeg;base64," + img_str.decode()        
        
    def b64_size(self, b64string):
        return (len(b64string) * 3) / 4 - b64string.count('=', -2)
      
    async def is_ready_to_send(self):
      if self.sio.connected:
        if self.status.id != self.statuses["CONNECTED"].id:
          self.set_status("CONNECTED", self.uri)
        return True
      else:
        if self.status.id == self.statuses["CONNECTING"].id:
          return False
        elif self.status.id == self.statuses["CONNECTED"].id:
          self.set_status("DISCONNECTED", self.uri)
          return False
        elif self.status.id == self.statuses["DISCONNECTED"].id:
          self.set_status("CONNECTING", self.uri)
          await self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=1)     
          return False 
        else:
          self.set_status("DISCONNECTED", self.uri)
        return False
    
    def send_msg(self):
      self.do_async(self.send_msg_async)
          
    async def send_msg_async(self):
      if not (await self.is_ready_to_send()):
        return
      await self.sio.emit(event='test_msg', namespace=self.namespace)
      
    def send_data(self, image_bytes):
      self.do_async(self.send_data_async, image_bytes)      
          
    async def send_data_async(self, image_bytes):
      if not (await self.is_ready_to_send()):
        return
      try:
        self.last_file_size = f"{image_bytes.getbuffer().nbytes/(1024*1024):0.2f}"
        #   print(f"Sending {file_size:0.2f} MB of frame data to WebSocket. FPS: {self.fps}")
        b64_data = self.encode_image_data(image_bytes.getvalue())
        t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        await self.sio.emit(event='op_frame', data={'frame_data': b64_data, 'datetime': t}, namespace=self.namespace)
      except Exception as e:
          print(f"Error Sending frame data to WebSocket {e}")
    
    def connect(self):
      print(f"CONNECTED!")
      self.set_status("CONNECTED", {self.uri})
    
    def handle_msg(self, data):
      print(f"Received msg {data}")
        
    def disconnect(self):
      print(f"DISCONNECTED!")
      self.set_status("DISCONNECTED", {self.uri})
        

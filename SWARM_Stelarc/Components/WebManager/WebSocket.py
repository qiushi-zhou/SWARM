import socketio
import threading
import time
import io
import datetime
import math
import asyncio
import json
import base64
import cv2


# sio = socketio.AsyncClient(logger=True, engineio_logger=True)
sio = socketio.AsyncClient()

# @sio.event(namespace='/visualization')
async def connect():
  global ws
  ws.set_status(WebSocket.Statuses.CONNECTED,  f"{ws.uri}")

# @sio.event(namespace='/visualization')
async def connect_error(data):
  global ws
  print(f"CONNECTION ERROR!")
  ws.set_status(WebSocket.Statuses.DISCONNECTED, f"{ws.uri} {data}")

# @sio.event(namespace='/visualization')
async def frame_received(*args):
  global ws
  if len(args) > 0:
    data = args[0]
    print(f"Received ACK from server{data}")
  ws.set_status(WebSocket.Statuses.CONNECTED,  f"{ws.uri} {data}", debug=False)
  
# @sio.event(namespace='/visualization')
async def op_frame_new(*args):
  global ws
  if len(args) > 0:
    data = args[0]
    # print(f"Received op_frame_new from {data}")
  ws.set_status(WebSocket.Statuses.CONNECTED,  f"{ws.uri} {data}", debug=False)

# @sio.event(namespace='/visualization')
async def disconnect():
  global ws
  ws.set_status(WebSocket.Statuses.DISCONNECTED, f"{ws.uri}")

# @sio.event(namespace='/visualization')
async def hey(*args):
  global ws
  if len(args) > 0:
    data = args[0]
    print(f"Received msg from {data}")
  ws.set_status(WebSocket.Statuses.CONNECTED,  f"{ws.uri} {data}")

  
class WebSocket:
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
      
    def __init__(self):
      global sio
      self.target_framerate = 30
      self.scaling_step = 0.1
      self.min_frame_scaling = 1
      self.fixed_frame_scaling = 1
      self.current_frame_scaling = 1
      self.sync_with_server = False
      self.sio = sio
      self.tag = "WebSocket"
      self.status = WebSocket.Statuses.NOT_INITIALIZED
      # sio = socketio.Client(logger=True, engineio_logger=True)
      self.url = ""
      self.namespace = ""
      self.uri = self.url + self.namespace
      self.last_file_size = -1
      self.async_loop = asyncio.get_event_loop()
      
    def init(self):
      self.set_status(WebSocket.Statuses.DISCONNECTED, {self.uri})
      self.attach_callbacks()
      self.do_async(self.update_status)
      # self.update_status()
      self.send_msg()
          
    def attach_callbacks(self):
      global sio
      sio.on('connect', handler=connect, namespace=self.namespace)
      sio.on('connect_error', handler=connect_error, namespace=self.namespace)
      sio.on('hey', handler=hey, namespace=self.namespace)
      sio.on('frame_received', handler=frame_received, namespace=self.namespace)
      sio.on('op_frame_new', handler=op_frame_new, namespace=self.namespace)
      sio.on('disconnect', handler=disconnect, namespace=self.namespace)      
    
    def set_status(self, new_status, extra, debug=True):
      if debug:
        print(f"{self.tag} {self.status.name} -> {new_status.name}, {extra}")
      self.status = new_status
      self.status.extra = extra
        
    def update_config(self, data):
        self.target_framerate = data.get("ws_target_framerate", 30)
        self.min_frame_scaling = data.get("ws_min_frame_scaling", 1)
        self.fixed_frame_scaling = data.get("ws_fixed_frame_scaling", 1)
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
    
    def do_async(self, async_function, *args, **kwargs):
      try:
          self.async_loop.run_until_complete(async_function(*args, **kwargs))
          # self.sio.start_background_task(async_function, *args, **kwargs)
      except Exception as e:
          print(f"Error running WebSocket async function: {e}")
      
    def encode_image_data(self, image_data):
        img_str = base64.b64encode(image_data)
        return "data:image/jpeg;base64," + img_str.decode()        
        
    def b64_size(self, b64string):
        return (len(b64string) * 3) / 4 - b64string.count('=', -2)
      
    async def update_status(self):
      if self.sio.connected:
        if self.status.id == WebSocket.Statuses.WAITING.id:
          return False
        elif self.status.id != WebSocket.Statuses.CONNECTED.id:
          # Maybe something went wrong and we missed the connected message but socketio still connected somehow!
          self.set_status(WebSocket.Statuses.CONNECTED, self.uri)
        return True
      else:
        if self.status.id == WebSocket.Statuses.CONNECTING.id:
          return False
        elif self.status.id == WebSocket.Statuses.CONNECTED.id:
          self.set_status(WebSocket.Statuses.DISCONNECTED, self.uri)
          return False
        elif self.status.id in [WebSocket.Statuses.DISCONNECTED.id, WebSocket.Statuses.NOT_INITIALIZED.id]:
          self.set_status(WebSocket.Statuses.CONNECTING, self.uri)
          await self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=1)
          # time.sleep(1) # Otherwise it might get stuck in a loop as the status will change to connected WHILE it was in the "sio.connected" else
          return False 
        else:
          self.set_status(WebSocket.Statuses.DISCONNECTED, self.uri)
        return False
    
    def send_msg(self):
      if self.status.id != WebSocket.Statuses.CONNECTED.id:
        return False
      self.do_async(self.send_msg_async)
          
    async def send_msg_async(self):
      print(f"Sending msg websocket")
      await self.sio.emit(event='test_msg', namespace=self.namespace)
      
    def send_data(self, pygame, surface, frame_w, frame_h, fps_counter):
      if self.status.id != WebSocket.Statuses.CONNECTED.id:
        self.do_async(self.update_status)
        return False
      self.do_async(self.send_data_async, pygame, surface, frame_w, frame_h, fps_counter)
      return True
    
    async def send_data_async(self, pygame, surface, frame_w, frame_h, fps_counter):
      try:   
        image_bytes = io.BytesIO()
        subsurface = surface.subsurface((0,0, frame_w, frame_h))
        if self.min_frame_scaling < 0.99:
          if fps_counter.fps < self.target_framerate:
            self.current_frame_scaling -= self.scaling_step
          subsurface = pygame.transform.scale(subsurface, (frame_w*self.current_frame_scaling, frame_h*self.current_frame_scaling))
        elif self.fixed_frame_scaling < 0.99:
          self.current_frame_scaling = self.fixed_frame_scaling
          subsurface = pygame.transform.scale(subsurface, (frame_w*self.current_frame_scaling, frame_h*self.current_frame_scaling))
        pygame.image.save(subsurface, image_bytes, "JPEG")
        self.last_file_size = f"{image_bytes.getbuffer().nbytes/(1024*1024):0.2f}"
        #   print(f"Sending {file_size:0.2f} MB of frame data to WebSocket. FPS: {self.fps}")
        b64_data = self.encode_image_data(image_bytes.getvalue())
        t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        if self.sync_with_server:
          self.set_status(WebSocket.Statuses.WAITING, "", debug=False)
        fps_counter.frame_count += 1
        fps_counter.update()
        await self.sio.emit(event='op_frame', data={'frame_data': b64_data, 'datetime': t}, namespace=self.namespace)
      except Exception as e:
          print(f"Error Sending frame data to WebSocket {e}")
    

ws = WebSocket()

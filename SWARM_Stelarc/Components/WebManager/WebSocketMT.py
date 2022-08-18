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
import pygame
from Utils.FPSCounter import FPSCounter



# sio = socketio.AsyncClient(logger=True, engineio_logger=True)
sio = socketio.Client()

# @sio.event(namespace='/visualization')
def connect():
  global ws
  ws.set_status(WebSocket.Statuses.CONNECTED,  f"{ws.uri}")

# @sio.event(namespace='/visualization')
def connect_error(data):
  global ws
  print(f"CONNECTION ERROR!")
  ws.set_status(WebSocket.Statuses.DISCONNECTED, f"{ws.uri} {data}")

# @sio.event(namespace='/visualization')
def frame_received(*args):
  global ws
  if len(args) > 0:
    data = args[0]
    # print(f"Received ACK from server{data}")
  ws.set_status(WebSocket.Statuses.CONNECTED,  f"{ws.uri} {data}", debug=False)
  
# @sio.event(namespace='/visualization')
def op_frame_new(*args):
  global ws
  if len(args) > 0:
    data = args[0]
    # print(f"Received op_frame_new from {data}")
  ws.set_status(WebSocket.Statuses.CONNECTED,  f"{ws.uri} {data}", debug=False)

# @sio.event(namespace='/visualization')
def disconnect():
  global ws
  ws.set_status(WebSocket.Statuses.DISCONNECTED, f"{ws.uri}")

# @sio.event(namespace='/visualization')
def hey(*args):
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
      pygame = None
      self.surface = None
      self.frame_w = -1
      self.frame_h = -1
      self.fps_counter = None
      self.target_framerate = 30
      self.scaling_step = 0.1
      self.min_frame_scaling = 1
      self.fixed_frame_scaling = 1
      self.current_frame_scaling = 1
      self.sync_with_server = False
      self.max_wait_timeout = 2
      self.wait_time = 0
      self.sio = sio
      self.tag = "WebSocket"
      self.status = WebSocket.Statuses.NOT_INITIALIZED
      # sio = socketio.Client(logger=True, engineio_logger=True)
      self.url = ""
      self.namespace = ""
      self.uri = self.url + self.namespace
      self.last_file_size = -1
      self.thread_started = False
      self.read_lock = threading.Lock()
      self.frame_ready = False
      self.fps_counter = FPSCounter()
      self.frame_scaling = False
      self.frame_adaptive = False
      self.start_mt_stream()
      
    def start_mt_stream(self):
        if self.thread_started:
            print('[!] Threaded video capturing has already been started.')
            return None
        self.thread_started = True
        self.thread = threading.Thread(target=self.loop, args=())
        self.thread.start()
        return self
    
    def loop(self):
        while self.thread_started:
          with self.read_lock:
            if self.frame_ready:
              self.update_status()
              image_bytes = self.get_frame(pygame, self.subsurface, self.frame_w, self.frame_h)
              self.send_data(image_bytes)
              self.frame_ready = False
              self.fps_counter.update()
      
    def notify(self, surface, frame_w, frame_h):
      with self.read_lock:
        if not self.frame_ready:
          if self.fps_counter.fps > self.target_framerate:
            self.fps_counter.update()
            return
          self.subsurface = surface.subsurface((0,0, frame_w, frame_h))
          self.frame_w = frame_w
          self.frame_h = frame_h
          self.frame_ready = True
          
    def init(self):
      self.set_status(WebSocket.Statuses.DISCONNECTED, {self.uri})
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
        self.target_framerate = data.get("ws_target_framerate", 30)
        self.frame_scaling = data.get("ws_frame_scaling", False)
        self.frame_adaptive = data.get("ws_frame_adaptive", False)
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
    
    # def do_async(self, async_function, *args, **kwargs):
    #   try:
    #       self.async_loop.run_until_complete(async_function(*args, **kwargs))
    #       # self.sio.start_background_task(async_function, *args, **kwargs)
    #   except Exception as e:
    #       print(f"Error running WebSocket function: {e}")
      
    def encode_image_data(self, image_data):
        img_str = base64.b64encode(image_data)
        return "data:image/jpeg;base64," + img_str.decode()        
        
    def b64_size(self, b64string):
        return (len(b64string) * 3) / 4 - b64string.count('=', -2)
      
    def update_status(self):
      if self.sio.connected:
        if self.status.id == WebSocket.Statuses.WAITING.id:
          elapsed = time.time() - self.wait_time
          if elapsed > self.max_wait_timeout:
            self.wait_time = 0
            self.set_status(WebSocket.Statuses.CONNECTED, self.uri)
            return True
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
          self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=1)
          # time.sleep(1) # Otherwise it might get stuck in a loop as the status will change to connected WHILE it was in the "sio.connected" else
          return False 
        else:
          self.set_status(WebSocket.Statuses.DISCONNECTED, self.uri)
        return False
    
    def send_msg(self):
      print(f"Sending msg websocket")
      self.sio.emit(event='test_msg', namespace=self.namespace)
    
    def get_fps(self):
      with self.read_lock:
        return self.fps_counter.fps
      
    def get_frame(self, pygame, subsurface, frame_w, frame_h):
      image_bytes = io.BytesIO()
      if self.frame_scaling:
        if self.frame_adaptive:
          if self.fps_counter.fps < self.target_framerate:
            if self.min_frame_scaling < 1 and self.current_frame_scaling > self.min_frame_scaling:
              self.current_frame_scaling -= self.scaling_step
            if self.current_frame_scaling < 1:              
              self.current_frame_scaling += self.scaling_step
        else:
          self.current_frame_scaling = self.fixed_frame_scaling
        subsurface = pygame.transform.scale(subsurface, (frame_w*self.current_frame_scaling, frame_h*self.current_frame_scaling))
        
      pygame.image.save(subsurface, image_bytes, "JPEG")
      return image_bytes
      
    def send_data(self, image_bytes):
      if image_bytes is None:
        return
      if self.status.id != WebSocket.Statuses.CONNECTED.id:
        return False
      try:
        self.last_file_size = f"{image_bytes.getbuffer().nbytes/(1024*1024):0.2f}"
        #   print(f"Sending {file_size:0.2f} MB of frame data to WebSocket. FPS: {self.fps}")
        b64_data = self.encode_image_data(image_bytes.getvalue())
        t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        if self.sync_with_server:
          self.set_status(WebSocket.Statuses.WAITING, "", debug=False)
          self.wait_time = time.time()
          self.sio.emit(event='op_frame', data={'frame_data': b64_data, 'datetime': t}, namespace=self.namespace, callback=frame_received)
        else:
          self.sio.emit(event='op_frame', data={'frame_data': b64_data, 'datetime': t}, namespace=self.namespace)
        self.fps_counter.frame_count += 1
        # await sio.sleep(0.1)
      except Exception as e:
          print(f"Error Sending frame data to WebSocket {e}")
          self.set_status(WebSocket.Statuses.DISCONNECTED, f"{e}")
      return True    

ws = WebSocket()

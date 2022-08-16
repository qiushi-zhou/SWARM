
import socketio
import asyncio
import threading
import time
import io
import base64
import datetime
import math



class WebSocket:
    def __init__(self, enabled=True, url="", namespace="", send_frames=False, target_framerate=30):
        # self.sio = socketio.Client(logger=True, engineio_logger=True)
        self.sio = socketio.AsyncClient()
        self.url = url
        self.namespace = namespace
        self.uri = url + namespace
        self.ws_enabled = enabled
        self.send_frames = send_frames
        self.target_framerate = target_framerate
        self.setup_done = False
        self.setup_msg = "All GOOD!"
        self.frames_to_skip = 0
        self.skipped_frames = 0
        self.last_size = 0
        self.frame_count = 0
        self.fps_reset_time = 10
        self.fps = 0
        self.start_time = time.time() 

    def close(self):
        self.sio.disconnect()

    def setup(self, async_loop): 
      if self.ws_enabled:
        try:
            print(f"Connecting to WebSocket on: {self.uri}")
            async_loop.run_until_complete(self.setup_async())
        except Exception as e:
            print(f"Error running WebSocket setup {e}")

    async def setup_async(self):
        self.setup_done = True
        await self.call_backs()
        try:
          await self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=1)
          self.setup_msg = "All GOOD!"
        except Exception as e:
          self.setup_msg = e
        # self.sio.wait()
        
    def size(self, b64string):
        return (len(b64string) * 3) / 4 - b64string.count('=', -2)
      
    def send_msg(self, async_loop):
        try:
            print(f"Sending msg to WebSocket on: {self.uri}")
            async_loop.run_until_complete(self.send_msg_async())
        except Exception as e:
            print(f"Error Sending data to WebSocket {e}")
            
    async def send_msg_async(self):
      try:
          await self.sio.emit(event='test_msg', namespace=self.namespace)
      except Exception as e:
          print(f"Error sending data to socket {e}")

    def send_data(self, image_data, file_size, b64_size, async_loop):
        if self.ws_enabled:
            try:
                # print(f"Sending msg to WebSocket on: {self.uri}")
                # async_loop.run_until_complete(self.send_msg_async())
                if self.send_frames:      
                    elapsed = time.time() - self.start_time
                    self.fps = self.frame_count / elapsed
                    self.frames_to_skip = round(self.fps/self.target_framerate) if self.fps >= self.target_framerate else 0
                    if elapsed > self.fps_reset_time:
                        self.frame_count = 0 
                        self.start_time = time.time() 
                    else:
                        self.frame_count += 1
                    self.last_size = f"{file_size:0.2f}"
                    #   print(f"Sending {file_size:0.2f} MB of frame data to WebSocket. FPS: {self.fps}")
                    async_loop.run_until_complete(self.send_data_async(image_data))
            except Exception as e:
                print(f"Error Sending data to WebSocket {e}")
            
        
      
    async def send_data_async(self, image_data):
        if not self.sio.connected:
            try:
                await self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=1)
                self.setup_msg = "All GOOD!"
            except Exception as e:
                self.setup_msg = e
        else:
            try:
                # img_data_str = self.encode_image_data(image_data)
                img_data_str = image_data
                t = datetime.datetime.now()
                await self.sio.emit(event='op_frame', data={'frame_data': img_data_str, 'datetime': t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}, namespace=self.namespace)
                # self.sio.wait()
            except Exception as e:
                print(f"Error sending data to socket {e}")

    async def call_backs(self):
        @self.sio.event
        async def connect():
            print(f"Connected to to WebSocket on: {self.uri}")

        @self.sio.on("docs")
        async def raw_data(data):
            print(f"Data Received!")
            # print(f"Data Received {data}")

        @self.sio.event
        async def auth(data):
            print(f"Data Received")
            # print(f"Data Received {data}")

        @self.sio.event
        async def disconnect():
            pass

    def draw_debug(self, logger, start_pos, debug=False): 
        dbg_str = "WebSocket "
        if not self.ws_enabled:
            dbg_str += "Disabled"
        elif self.setup_done:
            dbg_str += "Connected " if self.sio.connected else "NOT Connected"
            dbg_str = f"{dbg_str} - Msg: {self.setup_msg}"
        else:
            dbg_str += "Running Setup "
        start_pos = logger.add_text_line(dbg_str, (255, 50, 0), start_pos)
        dbg_str = f"WebSocket FPS: {self.fps:>0.2f}, FS: {self.frames_to_skip:0.2f}, File Size: {self.last_size}"
        start_pos = logger.add_text_line(dbg_str, (255, 50, 0), start_pos)

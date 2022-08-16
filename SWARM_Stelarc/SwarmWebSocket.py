
import socketio
import asyncio
import threading
import time
import io
import base64
import datetime


class WebSocket:
    def __init__(self, url, namespace, enabled=False):
        # self.sio = socketio.Client(logger=True, engineio_logger=True)
        self.sio = socketio.AsyncClient()
        self.url = url
        self.namespace = namespace
        self.uri = url + namespace
        self.ws_enabled = enabled
        self.setup_done = False
        self.setup_msg = "All GOOD!"

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
        self.call_backs()
        try:
          await self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=2)
        except Exception as e:
          self.setup_msg = e
        # self.sio.wait()

    def encode_image_data(self, image_data):
        img_str = base64.b64encode(image_data)
        return "data:image/jpeg;base64," + img_str.decode()
      
    def send_data(self, image_data, async_loop):
      if self.ws_enabled and self.sio.connected:
        try:
            print(f"Sending data to WebSocket on: {self.uri}")
            async_loop.run_until_complete(self.send_data_async(image_data))
        except Exception as e:
            print(f"Error Sending data to WebSocket {e}")
      
    async def send_data_async(self, image_data):
      try:
          img_data_str = self.encode_image_data(image_data)
          t = datetime.datetime.now()
          # self.sio.start_background_task(self.sio.emit, 'op_frame', {'frame_data': img_data_str, 'time':datetime.datetime().now().ctime()})
          # self.sio.emit(event='op_frame', data={'frame_data': img_data_str, 'time_ms': time.mktime(t.timetuple()), "datetime": t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}, namespace=self.namespace)
          await self.sio.emit(event='op_frame', data={'frame_data': img_data_str}, namespace=self.namespace)
          # self.sio.emit(event='op_frame', data={"WHAT":"what"}, namespace=self.namespace)
          # self.sio.emit('op_frame', {'frame_data': '', 'time_ms': time.mktime(t.timetuple()), "datetime": t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}, namespace=self.namespace)
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

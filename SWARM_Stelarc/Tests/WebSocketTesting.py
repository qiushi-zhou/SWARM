import asyncio
import threading
import time
import socketio
from concurrent.futures import ThreadPoolExecutor

class WebSocketTest:
  async def on_connect():
    global ws
    print(f"{ws.namespace} Connected, Thread ws: {threading.current_thread().getName()}")

  async def on_disconnect():
    global ws
    print(f"{ws.namespace} Disconnected, Thread ws: {threading.current_thread().getName()}")

  async def on_connect_error(data):
    global ws
    print(f"Error connecting to socket on {ws.namespace}")

  async def on_hey_yo(*args):
    global ws
    if len(args) > 0:
      data = args[0]
      print(f"Received hey msg from {data}, Thread ws: {threading.current_thread().getName()}")

  async def on_webcam_data_out(*args):
    global ws
    print(f"{ws.namespace} Received webcam data, Thread ws: {threading.current_thread().getName()}")

  async def attempt_connect(self):
    global ws
    await self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=3)

  def attach_callbacks(self):
    self.sio.on("connect", handler=WebSocketTest.on_connect, namespace=self.namespace)
    self.sio.on("disconnect", handler=WebSocketTest.on_disconnect, namespace=self.namespace)
    self.sio.on("connect_error", handler=WebSocketTest.on_connect_error, namespace=self.namespace)
    self.sio.on("hey_yo", handler=WebSocketTest.on_hey_yo, namespace=self.namespace)
    self.sio.on("webcam_data_out", handler=WebSocketTest.on_webcam_data_out, namespace=self.namespace)

  async def send_loop(self):
    global ws
    print("Starting send loop")
    while self.thread_started:
      if self._stop.isSet():
        return
      if not self.sio.connected:
        await ws.attempt_connect()
      # else:
      #   await ws.sio.emit(event="ping", namespace=ws.namespace)
      await asyncio.sleep(0)

  def send_loop_starter(self):
    self.main_loop.run_until_complete(self.send_loop())

  def __init__(self, url, namespace):
    self.url = url
    self.namespace = namespace
    self.uri = self.url + self.namespace
    self.sio = socketio.AsyncClient(logger=True, engineio_logger=True)
    self.attach_callbacks()

    self.main_loop = asyncio.get_event_loop()
    self._stop = threading.Event()
    self.executor = ThreadPoolExecutor(2) # Create a ProcessPool with 2 processes
    self.thread_started = False
    self.thread = threading.Thread(target=self.send_loop_starter, args=[])

  def start_loop(self):
    self.thread_started = True
    self.thread.start()
    self.thread.join()

  def start_async(self):
    print("Task started")
    self.thread_started = True
    self.main_loop.run_in_executor(self.executor, self.send_loop_starter)
    self.main_loop.run_forever()
    print("Task completed")

# ws = WebSocketTest("wss://domain.com:3000", "/test_namespace")
ws = WebSocketTest("wss://anthropomorphicmachine.com:3006", "/online_interaction")
# ws.start_loop()
ws.start_async()

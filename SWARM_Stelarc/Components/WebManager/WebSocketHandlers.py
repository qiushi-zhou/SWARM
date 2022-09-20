import threading
from .WebSocketStatusManager import Statuses
import datetime
import numpy as np
import io
import base64
from PIL import Image
import cv2


def base64_to_cv2(image_data):
  # print(f"Decoding {base64_string}")
  base64_string = image_data.split(',')[1]
  imgdata = base64.b64decode(base64_string)
  img = Image.open(io.BytesIO(imgdata))
  return cv2.cvtColor(np.asarray(img), cv2.COLOR_BGR2RGB)

class WebSocketHandlers:

  async def on_connect(ws):
    try:
      print(f"{ws.namespace} Connected, Thread ws: {threading.current_thread().getName()}")
      ws.status_manager.set_connected()
      await ws.sio.emit(event="test_msg", namespace=ws.namespace)
      await ws.sio.emit(event="ping", data={}, namespace=ws.namespace)
    except Exception as e:
      print(f"Exception handling on_connect on {ws.namespace}: {e}")

  async def on_msg(ws, *args):
    try:
      data = ""
      if len(args) > 0:
        data = args[0]
        print(f"Received msg on {ws.namespace} from {data}, Thread ws: {threading.current_thread().getName()}")
      ws.status_manager.set_connected(f"Msg received: {data}")
    except Exception as e:
      print(f"Exception handling on_msg on {ws.namespace}: {e}")

  async def on_disconnect(ws):
    try:
      print(f"{ws.namespace} Disconnected, Thread ws: {threading.current_thread().getName()}")
      ws.status_manager.set_disconnected()
    except Exception as e:
      print(f"Exception handling on_disconnect on {ws.namespace}: {e}")


  async def on_connect_error(ws, data):
    try:
      print(f"Error connecting to {ws.namespace} socket")
    except Exception as e:
      print(f"Exception handling on_connect_error on {ws.namespace}. Data {data}: {e}: {e}")


  async def on_frame_received(ws, data):
    try:
      frame = base64_to_cv2(data['image_data'])
      ws.in_buffer.insert_data(frame)
      # print(f"Inserting IN data {ws.namespace}. Data? {data is None} {ws.in_buffer.count()}/{ws.in_buffer.size()}")
      # print(f"elapsed: {(ws.last_emit - datetime.datetime.now()).microseconds / 1000}")
      ws.status_manager.set_connected("Frame received")
    except Exception as e:
      print(f"Exception handling on_frame_received on {ws.namespace}: {e}")

  async def on_frame_received_ACK(ws, *args):
    try:
      # print(f"elapsed: {(ws.last_emit - datetime.datetime.now()).microseconds / 1000}")
      ws.status_manager.set_connected("Frame received ACK")
    except Exception as e:
      print(f"Exception handling on_frame_received_ACK on {ws.namespace}: {e}")


  async def on_scale_request(ws, *args):
    try:
      if len(args) > 0:
        data = args[0]
        ws.set_scaling(float(data.get('scaling_factor', 1.0)))
    except Exception as e:
      print(f"Exception handling on_scale_request on {ws.namespace}: {e}")
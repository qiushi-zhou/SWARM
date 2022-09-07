import asyncio
import datetime
import threading
from .WebSocketMeta import Status, Statuses, WebSocketMeta, SwarmData
import cv2
import time
import socketio


class WebSocketInteraction(WebSocketMeta):
    async def on_webcam_data_out(self, *args):
        print(f"{self.namespace} Webcam frame out, Thread ws: {threading.current_thread().getName() }")

    def loop(self, tasks_manager=None, async_loop=None):
        if self.status.id != Statuses.CONNECTED.id:
            self.update_status(self.main_loop)
            self.fps_counter.reset()
        time.sleep(1)
        return True

    def __init__(self, tasks_manager, url, namespace, frame_w, frame_h):
        WebSocketMeta.__init__(self, tasks_manager, url, namespace, frame_w, frame_h)
        print(f"Creating websocket interaction")
        self.target_framerate = 60
        self.scaling_factor = 1.0
        self.frame_skipping = False
        self.last_file_size = 1

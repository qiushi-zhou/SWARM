import threading

from .WebSocket import ws, WebSocket
from ..SwarmComponentMeta import SwarmComponentMeta
from ..Utils.FPSCounter import FPSCounter
import io
import math
import time
from collections import deque
import datetime
import base64
import pygame

class SwarmData:
    def __init__(self, image_bytes=None, graph_data=None):
        self.image_bytes = image_bytes
        self.graph_data = graph_data
        self.time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    def get_json(self):
        data = {}
        if self.image_bytes is not None:
            img_str = base64.b64encode(self.image_bytes.getvalue())
            data['frame_data'] = "data:image/jpeg;base64," + img_str.decode()
        if self.graph_data is not None:
            data['graph_data'] = self.graph_data
        data['datetime'] = self.time
        return data


class WebSocketManager(SwarmComponentMeta):
    def __init__(self, logger, tasks_manager, frame_w, frame_h):
        super(WebSocketManager, self).__init__(logger, tasks_manager, "WebSocketManager", r'./Config/WebSocketConfig.yaml', self.update_config_data)
        self.ws = ws
        self.tasks_manager = tasks_manager

        self.buffer_size = 10
        self.data_to_send = deque([])
        self.screen_updated = False
        self.send_frames = False
        self.enabled = True
        self.last_file_size = -1

        self.target_framerate = 30
        self.frame_skipping = False
        self.frames_to_skip = 0
        self.skipped_frames = 0

        self.frame_scaling = False
        self.adaptive_scaling = False
        self.scaling_step = 0.1
        self.min_frame_scaling = 1.0
        self.fixed_frame_scaling = 1.0
        self.max_frame_scaling = self.fixed_frame_scaling
        self.current_frame_scaling = 1.0

        self.fps_counter = FPSCounter()
        self.last_fps = self.fps_counter.fps

        self.frame_w = frame_w
        self.frame_h = frame_h
        self.surface = pygame.Surface((frame_w, frame_h))
        self.logger.add_surface(self.surface, self.tag)
        # self.surface = pygame.Surface((frame_w, frame_h))
        self.enqueue_task = None
        self.send_task = None
        self.read_lock = threading.Lock()
    
    def update_config(self, use_websocket=False):
        super().update_config_from_file(self.tag, self.config_filename, self.last_modified_time)
        self.ws.update_config(self.config_data)
        if use_websocket:
            if not self.enabled or self.enqueue_task is None:
                self.enqueue_task = self.tasks_manager.add_task("WS_Q", None, self.enqueue_data, self.read_lock).start()
                self.send_task = self.tasks_manager.add_task("WS_S", None, self.send_packets, self.read_lock).start()
        else:
            if self.enabled:
                if self.enqueue_task:
                    self.enqueue_task.stop()
                    self.enqueue_task = None
                if self.send_task:
                    self.send_task.stop()
                    self.send_task = None
        self.enabled = use_websocket
        
    def update_config_data(self, data, last_modified_time):
        self.config_data = data
        self.frame_scaling = data.get("ws_frame_scaling", False)
        self.adaptive_scaling = data.get("ws_frame_adaptive", False)
        self.min_frame_scaling = data.get("ws_min_frame_scaling", 1)
        self.fixed_frame_scaling = data.get("ws_fixed_frame_scaling", 1)
        self.max_frame_scaling = self.fixed_frame_scaling
        self.send_frames = data.get("ws_send_frames", self.send_frames)
        self.target_framerate = data.get("ws_target_framerate", 30)
        self.frame_skipping = data.get("ws_frame_skip", False)
        self.last_modified_time = last_modified_time

    def send_packets(self, tasks_manager=None):
        with self.read_lock:
            if len(self.data_to_send) <= 0:
                return True
        # self.ws.update_status()
        if self.ws.is_ready():
            if len(self.data_to_send) > 0:
                data_json = self.data_to_send.popleft().get_json()
                self.ws.send_data(data_json)
                self.fps_counter.frame_count += 1
                self.fps_counter.update()
                self.last_fps = self.fps_counter.fps
        return True

    def enqueue_data(self, tasks_manager=None):
        image_bytes = None
        if self.send_frames:
            if len(self.data_to_send) > self.buffer_size:
                return True
            with self.read_lock:
                image_bytes = self.get_frame(self.surface)
            self.last_file_size = image_bytes.getbuffer().nbytes / 1024*1024
        graph_data = self.get_graph_data()
        self.data_to_send.append(SwarmData(image_bytes, graph_data))
        return True

    def get_graph_data(self):
        return None

    def update_scaling(self):
        if self.frame_scaling:
            if self.adaptive_scaling:
                if self.fps_counter.fps < self.target_framerate:
                    self.current_frame_scaling = min(self.min_frame_scaling, self.current_frame_scaling - self.scaling_step)
                else:
                    self.current_frame_scaling = max(self.max_frame_scaling, self.current_frame_scaling + self.scaling_step)
            else:
                self.current_frame_scaling = self.fixed_frame_scaling
        else:
            self.current_frame_scaling = 1.0
        return self.current_frame_scaling

    def get_frame(self, surface):
        scaling_factor = self.update_scaling()
        image_bytes = io.BytesIO()
        subsurface = pygame.transform.scale(surface, (self.frame_w * scaling_factor, self.frame_h * scaling_factor))
        pygame.image.save(subsurface, image_bytes, "JPEG")
        return image_bytes
    
    def update(self, debug=False):
        if debug:
            print(f"Updating WebSocket Manager")

    def update_surface(self, frame):
        with self.read_lock:
            self.logger.draw_frame((0,0,0), frame, self.tag)
    
    def draw(self, start_pos, debug=False, surfaces=None):
        if debug:
            print(f"Drawing WebSocket Manager")
        dbg_str = "WebSocket "
        if not self.enabled:
            dbg_str += "Disabled"
            start_pos = self.logger.add_text_line(dbg_str, (255, 50, 0), start_pos, surfaces)
        else:
            status_dbg_str = self.ws.status.get_dbg_text(self.ws)
            ws_dbg_str = f"WebSocket FPS: {int(self.last_fps)}, FS: {self.current_frame_scaling:0.2f}, File Size: {self.last_file_size}"
            start_pos = self.logger.add_text_line(status_dbg_str, (255, 50, 0), start_pos, surfaces)
            start_pos = self.logger.add_text_line(ws_dbg_str, (255, 50, 0), start_pos, surfaces)

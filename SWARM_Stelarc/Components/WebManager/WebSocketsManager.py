from .WebSocketVideoStream import WebSocketVideoStream
from .WebSocketInteraction import WebSocketInteraction
from .WebSocketMeta import WebSocketMeta
from concurrent.futures import ThreadPoolExecutor
from ..SwarmComponentMeta import SwarmComponentMeta
import pygame
import socketio


class WebSocketsManager(SwarmComponentMeta):
    def __init__(self, logging, ui_drawer, tasks_manager, frame_w, frame_h):
        super(WebSocketsManager, self).__init__(ui_drawer, tasks_manager, "WebSocketManager", r'./Config/WebSocketConfig.yaml', self.update_config_data)
        self.tasks_manager = tasks_manager
        self.logging = logging
        self.multi_threaded = True
        self.executor = ThreadPoolExecutor(3)  #Create a ProcessPool with 2 processes
        self.sockets = {}

        self.frame_w = frame_w
        self.frame_h = frame_h
        self.surface = pygame.Surface((frame_w, frame_h))
        self.ui_drawer.add_surface(self.surface, self.tag)

    def update_config(self):
        super().update_config_from_file(self.tag, self.config_filename, self.last_modified_time)
        sockets_config = self.config_data.get("sockets", self.sockets)
        for s_config in sockets_config:
            namespace = s_config.get("namespace", None)
            # print(f"Namespace {namespace}")
            if namespace is not None and namespace not in self.sockets:
                url = s_config.get("url", "")
                if "gallery" in namespace:
                    self.sockets[namespace] = WebSocketVideoStream.create_ws(self.tasks_manager, url, namespace, self.frame_w, self.frame_h, self.executor)
                elif "inter" in namespace:
                    self.sockets[namespace] = WebSocketInteraction.create_ws(self.tasks_manager, url, namespace, self.frame_w, self.frame_h, self.executor)
            if namespace in self.sockets:
                self.sockets[namespace].update_config(s_config)

    def enqueue_frame(self, namespace, cv2_frame, cameras_data, swarm_data, draw=False):
        if namespace in self.sockets:
            self.sockets[namespace].enqueue_frame(cv2_frame, cameras_data, swarm_data)
        if draw:
            self.ui_drawer.draw_frame((0, 0, 0), cv2_frame, self.tag)

    def get_stream_frame(self, namespace):
        if "inter" in namespace and namespace in self.sockets:
            return self.sockets[namespace].get_latest_received_frame()
        return None

    def update_config_data(self, data, last_modified_time):
        self.config_data = data
        self.last_modified_time = last_modified_time

    def draw(self, start_pos, debug=False, surfaces=None):
        if debug:
            print(f"Drawing WebSocket Manager")
        dbg_str = "WebSocket "
        if not self.enabled:
            dbg_str += "Disabled"
            start_pos = self.ui_drawer.add_text_line(dbg_str, (255, 50, 0), start_pos, surfaces)
        else:
            for key in self.sockets:
                s = self.sockets[key]
                status_dbg_str = f"{s.tag} {s.status_manager.get_status_info()}"
                data_str = f"OUT FPS: {int(s.out_buffer.fps())}, Buff Out: {s.out_buffer.count()}/{s.out_buffer.size()}          "
                data_str += f"IN FPS: {int(s.in_buffer.fps())}, Buff In: {s.in_buffer.count()}/{s.in_buffer.size()}"
                # dbg_str = f"{s.tag} FPS: {int(s.fps_counter.fps)}, Scale: {s.scaling_factor:0.2f},{mt_data} Size: {s.last_file_size}"
                start_pos = self.ui_drawer.add_text_line(status_dbg_str, (255, 50, 0), start_pos, surfaces)
                start_pos.y -= self.ui_drawer.line_height
                start_pos = self.ui_drawer.add_text_line(data_str, (255, 50, 0), start_pos, surfaces)
                # start_pos.y -= self.ui_drawer.line_height
                # start_pos = self.ui_drawer.add_text_line(in_data, (255, 50, 0), start_pos, surfaces)

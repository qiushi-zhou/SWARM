from .WebSocketVideoStreamIn import WebSocketVideoStreamIn
from .WebSocketVideoStreamOut import WebSocketVideoStreamOut
from .WebSocketInteraction import WebSocketInteraction
from .WebSocketMeta import WebSocketMeta
from concurrent.futures import ThreadPoolExecutor
from ..SwarmComponentMeta import SwarmComponentMeta
import pygame
import socketio


class WS_TYPES:
    INTERACTION = "online_interaction"
    VIDEO_STREAM_OUT = "video_stream_out"
    VIDEO_STREAM_IN = "video_stream_in"

class WebSocketsManager(SwarmComponentMeta):

    def __init__(self, app_logger, ui_drawer, tasks_manager, frame_w, frame_h):
        super(WebSocketsManager, self).__init__(ui_drawer, tasks_manager, "WebSocketManager", r'./Config/WebSocketConfig.yaml', self.update_config_data)
        self.tasks_manager = tasks_manager
        self.app_logger = app_logger
        self.multi_threaded = True
        self.executor = ThreadPoolExecutor(3)  #Create a ProcessPool with 2 processes
        self.url = ""
        self.sockets = {}
        self.sockets[WS_TYPES.INTERACTION] = {}
        self.sockets[WS_TYPES.VIDEO_STREAM_OUT] = {}
        self.sockets[WS_TYPES.VIDEO_STREAM_IN] = {}

        self.frame_w = frame_w
        self.frame_h = frame_h
        self.surface = pygame.Surface((frame_w, frame_h))
        self.ui_drawer.add_surface(self.surface, self.tag)


    def update_config(self):
        super().update_config_from_file(self.app_logger, self.tag, self.config_filename, self.last_modified_time)

    def update_config_data(self, data, last_modified_time):
        self.config_data = data
        self.last_modified_time = last_modified_time
        self.url = self.config_data.get("url", "")
        sockets_config = self.config_data.get("sockets", self.sockets)
        for s_config in sockets_config:
            namespace = s_config.get("namespace", None)
            type = s_config.get("type", None)
            ws_id = s_config.get("id", None)
            port = s_config.get("port", "")
            enabled = s_config.get("enabled", "WHAT")
            self.app_logger.info(f"Reading config for {ws_id} {port} {namespace} {type} ({enabled})")
            if namespace is not None and type is not None and ws_id is not None:
                socket = None
                if type in WS_TYPES.VIDEO_STREAM_OUT:
                    if ws_id not in self.sockets[WS_TYPES.VIDEO_STREAM_OUT]:
                        socket = WebSocketVideoStreamOut.create_ws(self.app_logger, ws_id, self.tasks_manager, f"{self.url}:{port}", namespace, self.frame_w, self.frame_h, self.executor)
                        self.sockets[WS_TYPES.VIDEO_STREAM_OUT][ws_id] = socket
                    else:
                        socket = self.sockets[WS_TYPES.VIDEO_STREAM_OUT][ws_id]
                # elif type in WS_TYPES.VIDEO_STREAM_IN:
                #     if ws_id not in self.sockets[WS_TYPES.VIDEO_STREAM_IN]:
                #         socket = WebSocketVideoStreamIn.create_ws(self.app_logger, ws_id, self.tasks_manager, url, namespace, self.frame_w, self.frame_h, self.executor)
                #         self.sockets[WS_TYPES.VIDEO_STREAM_IN][ws_id] = socket
                #     else:
                #         socket = self.sockets[WS_TYPES.VIDEO_STREAM_IN][ws_id]
                elif type in WS_TYPES.INTERACTION:
                    if ws_id not in self.sockets[WS_TYPES.INTERACTION]:
                        socket = WebSocketInteraction.create_ws(self.app_logger, ws_id, self.tasks_manager, f"{self.url}:{port}", namespace, self.frame_w, self.frame_h, self.executor)
                        self.sockets[WS_TYPES.INTERACTION][ws_id] = socket
                    else:
                        socket = self.sockets[WS_TYPES.INTERACTION][ws_id]
                if socket is not None:
                    socket.update_config(s_config, self.url)

    def enqueue_frame(self, namespace, cv2_frame, cameras_data, swarm_data, draw=False):
        if namespace in self.sockets:
            self.sockets[namespace].enqueue_frame(cv2_frame, cameras_data, swarm_data)
        if draw:
            self.ui_drawer.draw_frame((0, 0, 0), cv2_frame, self.tag)

    def get_last_remote_command(self):
        for ws_id in self.sockets[WS_TYPES.INTERACTION]:
            socket = self.sockets[WS_TYPES.INTERACTION][ws_id]
            if not socket.in_buffer.is_empty():
                return [socket.get_last_remote_command(), ws_id]
        return [None, ""]
    def pop_last_remote_command(self, ws_id):
        if ws_id in self.sockets[WS_TYPES.INTERACTION]:
            self.sockets[WS_TYPES.INTERACTION][ws_id].pop_last_command()

    def get_last_stream_frame(self):
        for socket in self.sockets[WS_TYPES.VIDEO_STREAM_IN]:
            if not socket.in_buffer.is_empty():
                return socket.in_buffer.peek()
        return None


    def draw(self, start_pos, debug=False, surfaces=None):
        if debug:
            print(f"Drawing WebSocket Manager")
        dbg_str = "WebSocket "
        if not self.enabled:
            dbg_str += "Disabled"
            start_pos = self.ui_drawer.add_text_line(dbg_str, (255, 50, 0), start_pos, surfaces)
        else:
            for key in self.sockets:
                for ws_id in self.sockets[key]:
                    s = self.sockets[key][ws_id]
                    status_dbg_str = f"{s.ws_id} {s.status_manager.get_status_info()}"
                    data_str = f"OUT FPS: {int(s.out_buffer.fps())}, Buff Out: {s.out_buffer.count()}/{s.out_buffer.size()}          "
                    data_str += f"IN FPS: {int(s.in_buffer.fps())}, Buff In: {s.in_buffer.count()}/{s.in_buffer.size()}"
                    # dbg_str = f"{s.tag} FPS: {int(s.fps_counter.fps)}, Scale: {s.scaling_factor:0.2f},{mt_data} Size: {s.last_file_size}"
                    start_pos = self.ui_drawer.add_text_line(status_dbg_str, (255, 50, 0), start_pos, surfaces)
                    start_pos.y -= self.ui_drawer.line_height
                    start_pos = self.ui_drawer.add_text_line(data_str, (255, 50, 0), start_pos, surfaces)
                    # start_pos.y -= self.ui_drawer.line_height
                    # start_pos = self.ui_drawer.add_text_line(in_data, (255, 50, 0), start_pos, surfaces)

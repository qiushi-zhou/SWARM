from .WebSocketMT import ws, WebSocket
from ..SwarmComponentMeta import SwarmComponentMeta
from Utils.FPSCounter import FPSCounter
import io
import math
import time

class WebSocketManager(SwarmComponentMeta):
    def __init__(self, logger, tasks_manager):
        super(WebSocketManager, self).__init__(logger, tasks_manager, "WebSocketManager", r'./Config/WebSocketConfig.yaml', self.update_config_data)
        self.ws = ws
        self.tasks_manager = tasks_manager
        self.background_task = self.tasks_manager.add_task("WebSocket", None, self.send_packet, None).start()
        self.read_lock = self.background_task.read_lock
        self.send_frames = False
        self.enabled = False
        self.frame_skipping = False
        self.frames_to_skip = 0
        self.skipped_frames = 0
        self.target_framerate = 30
        self.fps = 0
    
    def update_config(self):
        super().update_config_from_file(self.tag, self.config_filename, self.last_modified_time)
        
    def update_config_data(self, data, last_modified_time):
        self.config_data = data
        self.send_frames = data.get("ws_send_frames", self.send_frames)
        self.target_framerate = data.get("ws_target_framerate", 30)
        self.frame_skipping = data.get("ws_frame_skip", False)
        self.enabled = data.get("ws_enabled", True)
        if self.enabled:
            self.ws.update_config(self.config_data)
        self.last_modified_time = last_modified_time

    def send_packet(self, tasks_manager=None):
        if self.frame_ready:
            with tasks_manager.read_lock:
                image_bytes = self.get_frame(self.pygame, self.subsurface, self.frame_w, self.frame_h)
            self.send_data(image_bytes)
            self.frame_ready = False
            self.fps_counter.update()
        self.ws.send_new_frame(tasks_manager)
        return True

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
            subsurface = pygame.transform.scale(subsurface, (
            frame_w * self.current_frame_scaling, frame_h * self.current_frame_scaling))

        pygame.image.save(subsurface, image_bytes, "JPEG")
        return image_bytes

    def notify(self, surface, frame_w, frame_h):
        with self.read_lock:
            self.ws.update_frame(surface, frame_w, frame_h)
    
    def update(self, pygame, surface, frame_w, frame_h, debug=False):
        if debug:
            print(f"Updating WebSocket Manager")
        # Image bytes should be retreived like this:    
        # pygame.image.save(self.scene.screen.subsurface((0,0, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT)), image_data, "JPEG")
        if self.enabled:
            if self.send_frames:
                with self.read_lock:
                    self.fps = self.ws.get_fps()
                if self.frame_skipping:
                    if self.skipped_frames > self.frames_to_skip:
                        self.skipped_frames = 0
                        self.notify(surface, frame_w, frame_h)
                        # self.ws.send_data(pygame, surface, frame_w, frame_h, self.fps_counter)
                        self.frames_to_skip = round(self.fps/self.target_framerate if self.fps > 0 else 0)
                    # self.frames_to_skip = round(self.fps_counter.fps/self.ws.target_framerate) if self.fps_counter.fps >= self.ws.target_framerate else 0
                    self.skipped_frames += 1
                    # self.fps_counter.update()
                else:
                    self.notify(surface, frame_w, frame_h)
                    # self.ws.send_data(pygame, surface, frame_w, frame_h, self.fps_counter)
                # self.fps_counter.update()
    
    def draw(self, start_pos, debug=False):
        if debug:
            print(f"Drawing WebSocket Manager")
        dbg_str = "WebSocket "
        if not self.enabled:
            dbg_str += "Disabled"
            start_pos = self.logger.add_text_line(dbg_str, (255, 50, 0), start_pos)
        else:
            dbg_str = self.ws.status.get_dbg_text(self.ws)
            start_pos = self.logger.add_text_line(dbg_str, (255, 50, 0), start_pos)
            if self.frame_skipping:
                dbg_str = f"WebSocket FPS: {int(self.fps)}, FS: {self.frames_to_skip:0.2f}, File Size: {self.ws.last_file_size}"
            else:
                dbg_str = f"WebSocket FPS: {int(self.fps)}, File Size: {self.ws.last_file_size}"
            start_pos = self.logger.add_text_line(dbg_str, (255, 50, 0), start_pos)
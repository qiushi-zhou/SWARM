from .WebSocketMT import ws, WebSocket
from ..SwarmComponentMeta import SwarmComponentMeta
from Utils.FPSCounter import FPSCounter
import io
import math
import time

class WebSocketManager(SwarmComponentMeta):
    def __init__(self, logger):
        super(WebSocketManager, self).__init__(logger, "WebSocketManager", r'./Config/WebSocketConfig.yaml', self.update_config_data)
        self.ws = ws        
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
    
    def update(self, pygame, surface, frame_w, frame_h):
        # Image bytes should be retreived like this:    
        # pygame.image.save(self.scene.screen.subsurface((0,0, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT)), image_data, "JPEG")
        if self.enabled:
            if self.send_frames:
                self.fps = self.ws.get_fps()
                if self.frame_skipping:
                    if self.skipped_frames > self.frames_to_skip:
                        self.skipped_frames = 0
                        self.ws.notify(surface, frame_w, frame_h)
                        # self.ws.send_data(pygame, surface, frame_w, frame_h, self.fps_counter)
                        self.frames_to_skip = round(self.fps/self.target_framerate if self.fps > 0 else 0)
                    # self.frames_to_skip = round(self.fps_counter.fps/self.ws.target_framerate) if self.fps_counter.fps >= self.ws.target_framerate else 0
                    self.skipped_frames += 1
                    # self.fps_counter.update()
                else:
                    self.ws.notify(surface, frame_w, frame_h)
                    # self.ws.send_data(pygame, surface, frame_w, frame_h, self.fps_counter)
                # self.fps_counter.update()
    
    def draw(self, start_pos, debug=False):
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
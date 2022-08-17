from .WebSocket import *
from ..SwarmComponentMeta import SwarmComponentMeta
from Utils.FPSCounter import FPSCounter

class WebSocketManager(SwarmComponentMeta):
    def __init__(self, logger):
        super(WebSocketManager, self).__init__(logger, "WebSocketManager", r'./Config/WebSocketConfig.yaml', self.update_config_data)
        self.ws = WebSocket()
        self.send_frames = False
        self.target_framerate = 15
        self.fps_counter = FPSCounter()
        self.enabled = False
        self.frames_to_skip = 0
        self.skipped_frames = 0
    
    def update_config(self):
        super().update_config_from_file(self.tag, self.config_filename, self.last_modified_time)
        
    def update_config_data(self, data, last_modified_time):
        self.config_data = data
        self.send_frames = data.get("ws_send_frames", self.send_frames) 
        self.target_framerate = data.get("ws_target_framerate", self.target_framerate)
        self.enabled = data.get("ws_enabled", True)
        if self.enabled:
            self.ws.update_config(self.config_data)
        self.last_modified_time = last_modified_time      
    
    def update(self, pygame, surface, frame_w, frame_h):
        # Image bytes should be retreived like this:    
        # pygame.image.save(self.scene.screen.subsurface((0,0, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT)), image_data, "JPEG")
        if self.enabled:
            # self.ws.send_msg()
            if self.send_frames:
                if self.skipped_frames >= self.frames_to_skip:
                    self.skipped_frames = 0
                    self.frames_to_skip = round(self.fps_counter.fps/self.target_framerate) if self.fps_counter.fps >= self.target_framerate else 0
                    image_data = io.BytesIO() 
                    pygame.image.save(surface.subsurface((0,0, frame_w, frame_h)), image_data, "JPEG")
                    self.ws.send_data(image_data)
                    self.fps_counter.frame_count += 1
                else:
                    self.skipped_frames += 1
                self.fps_counter.update()
    
    def draw(self, start_pos, debug=False):
        dbg_str = "WebSocket "
        if not self.enabled:
            dbg_str += "Disabled"
            start_pos = self.logger.add_text_line(dbg_str, (255, 50, 0), start_pos)
        else:
            dbg_str = self.ws.status.get_dbg_text()
            start_pos = self.logger.add_text_line(dbg_str, (255, 50, 0), start_pos)
            dbg_str = f"WebSocket FPS: {self.fps_counter.fps:>0.2f}, FS: {self.frames_to_skip:0.2f}, File Size: {self.ws.last_file_size}"
            start_pos = self.logger.add_text_line(dbg_str, (255, 50, 0), start_pos)
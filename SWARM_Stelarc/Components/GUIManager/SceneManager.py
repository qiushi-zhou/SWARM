# -*- coding: utf-8 -*-
from ..SwarmComponentMeta import SwarmComponentMeta
from ..SwarmLogger import SwarmLogger

class SceneDrawer:
    PYGAME = 'pygame'
    OPENCV = 'opencv'
    
class SceneManager(SwarmComponentMeta):
    def __init__(self, drawer_type, screen_w=500, screen_h=500, font_size=16):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.drawer_type = drawer_type
        if self.drawer_type == SceneDrawer.PYGAME:
            import pygame
            self.pygame = pygame
            self.pygame.init()
            self.pygame.display.set_mode((int(self.screen_w + self.screen_h*0.27), self.screen_h))
            self.pygame.display.set_caption("SWARM")
            self.screen = self.pygame.display.get_surface()
            self.sceneClock = self.pygame.time.Clock()
            self.font = self.pygame.font.SysFont('Cascadia', font_size)
            self.logger = SwarmLogger(self.pygame, self.screen, font=self.font, font_size=font_size)
            # log.add_widget(PyGameLogWidget(pygame=pygame, font=self.font, font_size=Constants.font_size, canvas=self.scene.screen))
        else:
            import cv2
            self.cv2 = cv2
            self.logger = SwarmLogger(self.cv2, None, font=None, font_size=0.4)
            
        super(SceneManager, self).__init__(self.logger, "SceneManager")
        self.screen_delay = 0
        self.backgroundColor = (0, 0, 0)
    
    def update_config(self):
        pass
            
    def update_config_data(self, data, last_modified_time):
        pass
    
    def update_screen_frame(self, frame):
        self.screen_delay = self.sceneClock.tick()
        self.screen.fill(self.backgroundColor)
        pgImg = self.pygame.image.frombuffer(frame.tostring(), frame.shape[1::-1], "BGR")
        self.screen.blit(pgImg, (0,0))
    
    def update(self, frame, debug=False):
        if frame is None:
            print(f"Frame in update is None!")
            return
        if debug:
            print(f"Updating scene...")
        if self.drawer_type == SceneDrawer.PYGAME:
            self.update_screen_frame(frame)
    
    def draw(self, debug=True):
        self.logger.flush_text_lines(debug=False, draw=True)
        if self.drawer_type == SceneDrawer.PYGAME:
            self.pygame.display.flip()

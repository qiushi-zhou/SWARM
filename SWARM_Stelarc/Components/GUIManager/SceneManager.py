# -*- coding: utf-8 -*-
from ..SwarmComponentMeta import SwarmComponentMeta

class SceneDrawerType:
    PYGAME = 'pygame'
    OPENCV = 'opencv'
    NONE = 'None'
    
class SceneManager(SwarmComponentMeta):
    def __init__(self, logger, tasks_manager, drawer_type, screen_w=500, screen_h=500, font_size=16):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.drawer_type = drawer_type
        self.logger = logger
        if self.drawer_type == SceneDrawerType.PYGAME:
            import pygame
            self.pygame = pygame
            self.pygame.init()
            self.pygame.display.set_mode((int(self.screen_w + self.screen_h*0.27), self.screen_h))
            self.pygame.display.set_caption("SWARM")
            self.screen = self.pygame.display.get_surface()
            self.sceneClock = self.pygame.time.Clock()
            self.font = self.pygame.font.SysFont('Cascadia', font_size)
            self.logger.set_drawer(self.pygame, self.screen)
            self.logger.set_font(self.font, font_size)
            # log.add_widget(PyGameLogWidget(pygame=pygame, font=self.font, font_size=Constants.font_size, canvas=self.scene.screen))
        elif self.drawer_type == SceneDrawerType.OPENCV:
            import cv2
            self.cv2 = cv2
            self.logger.set_drawer(self.cv2, self.screen)
            self.logger.set_font(None, 0.4)
            
        super(SceneManager, self).__init__(self.logger, tasks_manager, "SceneManager")
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
        try:
            self.screen.blit(pgImg, (0,0))
        except Exception as e:
            # Surface might be locked during blip! Rare but might happen
            pass
    
    def update(self, frame, debug=False):
        if debug:
            print(f"Update Scene Manager!")
        if frame is None:
            if debug:
                print(f"Frame in update is None!")
            return
        if debug:
            print(f"Updating scene...")
        if self.drawer_type == SceneDrawerType.PYGAME:
            self.update_screen_frame(frame)
    
    def draw(self, debug=True):
        if debug:
            print(f"Draw Scene Manager!")
        self.logger.flush_text_lines(debug=False, draw=True)
        if self.drawer_type == SceneDrawerType.PYGAME:
            self.pygame.display.flip()

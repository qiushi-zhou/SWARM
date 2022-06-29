# -*- coding: utf-8 -*-
import pygame


class Scene():
    def __init__(self, screen):
        self.screen = screen
        self.screen_delay = 0
        self.sceneClock = pygame.time.Clock()
        self.backgroundColor = (0, 0, 0)

    def render(self, frame):
        frame = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
        pgImg = pygame.image.frombuffer(frame.tostring(), frame.shape[1::-1], "RGB")
        self.screen.blit(pgImg, (0,0))

    def update(self, frame):
        self.screen_delay = self.sceneClock.tick()
        self.screen.fill(self.backgroundColor)
        self.render()
        pygame.display.flip()

# -*- coding: utf-8 -*-
import pygame


class Scene():
    def __init__(self, screen):
        self.screen = screen
        self.screen_delay = 0
        self.sceneClock = pygame.time.Clock()
        self.backgroundColor = (0, 0, 0)

    def render(self, filename='tempOP.jpeg'):
        pygame.display.flip()
        pygame.image.save(self.screen, filename)

    def update(self, frame, debug=False):
        if debug:
            print(f"Updating scene...")
        self.screen_delay = self.sceneClock.tick()
        self.screen.fill(self.backgroundColor)
        pgImg = pygame.image.frombuffer(frame.tostring(), frame.shape[1::-1], "RGB")
        self.screen.blit(pgImg, (0,0))

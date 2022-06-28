#!/usr/bin/env python
# -*- coding: utf-8 -*-
from Input import Input
from Scene import Scene
import Constants
import pygame

class SwarmAPP():
    def __init__(self, observable):
        observable.subscribe(self)
        self.input = Input()

        pygame.init()
        pygame.display.set_mode((Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT))
        pygame.display.set_caption("SWARM")
        screen = pygame.display.get_surface()
        self.scene = Scene(screen, self.input)
    
    def notify(self,observable,*args,**kwargs):
        print ('Got', args, kwargs, 'From', observable)

    def run(self, csvWriter, arduino, tracking_quadrant=0, quad_command="quiver_0"):
        while True:
            self.input.run(csvWriter, arduino, tracking_quadrant, quad_command)
            self.scene.run()
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import re
import time
from Input import Input
from Scene import Scene
import sys
import getopt
import Constants
import pygame
import serial


class Twister():

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

if __name__ == "__main__":
    arduino = Arduino(port="COM4", wait=False)
    options, remainder = getopt.getopt(sys.argv[1:], 's:x:')
    for opt, arg in options:
        if opt in ('-s'):
            song = arg
        elif opt in ('-x'):
            speed = float(arg)

    startTime = re.sub("\s+", "-", str(time.ctime()).strip())
    startTime = re.sub(":", "-", startTime.strip())

    with open(startTime+'data.csv', 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',', quotechar=' ', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(["Timestamp","PoseId", "Nose.x", "Nose.y", "Neck.x", "Neck.y",
                             "RShoulder.x", "RShoulder.y", "RElbow.x", "RElbow.y", "RWrist.x", "RWrist.y",
                             "LShoulder.x", "LShoulder.y", "LElbow.x", "LElbow.y", "LWrist.x", "LWrist.y",
                             "MidHip.x", "MidHip.y",
                             "RHip.x", "RHip.y", "RKnee.x", "RKnee.y", "RAnkle.x", "RAnkle.y",
                             "LHip.x", "LHip.y", "LKnee.x", "LKnee.y", "LAnkle.x", "LAnkle.y",
                             "REye.x", "REye.y", "LEye.x", "LEye.y", "REar.x", "REar.y", "LEar.x", "LEar.y",
                             "LBigToe.x", "LBigToe.y", "LSmallToe.x", "LSmallToe.y", "LHeel.x", "LHeel.y",
                             "RBigToe.x", "RBigToe.y", "RSmallToe.x", "RSmallToe.y", "RHeel.x", "RHeel.y"])

        game = Twister(arduino)
        game.run(spamwriter,arduino, tracking_quadrant=0, quad_command="quiver_0")
    arduino.close()

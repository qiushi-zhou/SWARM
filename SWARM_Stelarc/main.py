#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import re
import time
from Input import Input
from Scene import Scene
from SwarmApp import SwarmAPP
from Arduino import Arduino
import os
import sys
import getopt
import Constants
import pygame
import serial

if __name__ == "__main__":
    log_dir = "./logs"
    options, remainder = getopt.getopt(sys.argv[1:], 's:x:')
    for opt, arg in options:
        if opt in ('-s'):
            song = arg
        elif opt in ('-x'):
            speed = float(arg)

    startTime = re.sub("\s+", "-", str(time.ctime()).strip())
    startTime = re.sub(":", "-", startTime.strip())
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    with open(f"{log_dir}/{startTime}-data.csv", 'w', newline='') as csvfile:
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

        swarm = SwarmAPP(arduino_port="COM4", mockup_commands=True)
        # swarm = SwarmAPP(arduino_port="COM4", mockup_commands=False)
        swarm.run(debug=False)

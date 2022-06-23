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


class Arduino():
    startMarker = 60
    endMarker = 62
    wait_timeout = 10
    commands = {
        "pulse_0":   "$run,pulse,0#",
        "pulse_1":   "$run,pulse,1#",
        "undulate_0":"$run,undulate,0#",
        "undulate_1":"$run,undulate,1#",
        "glitch_0":  "$run,glitch,0#",
        "glitch_1":  "$run,glitch,1#",
        "quiver_0":  "$run,quiver,0#",
        "quiver_1":  "$run,quiver,1#",
        "seq_0":     "$run,seq,0#",
        "seq_1":     "$run,seq,1#",
        "stop":      "$stop#"
    }

    def __init__(self, port="COM4", bps=115200, p_1=8, p_2="N", p_3=1, wait=True):
        self.port = port
        self.bps = bps
        self.p_1 = p_1
        self.p_2 = p_2
        self.p_3 = p_3
        self.connected = False
        self.last_command = ""

        self.ser = serial.Serial()
        self.ser.baudrate = self.bps
        self.ser.port = self.port
        self.ser.open()
        self.connected = True
        time.sleep(1)
        print(self.debug_string())
        # try:
        #     self.ser.open()
        #     self.connected = True
        #     if wait:
        #         self.wait_for_connection(Arduino.wait_timeout if wait else 0)
        #     else:
        #         self.connected = True
        # except Exception as e:
        #     print(f"Error opening serial port: {e}")


    def wait_for_connection(self, timeout=wait_timeout):
        # wait until the Arduino sends 'Arduino Ready' - allows time for Arduino reset
        # it also ensures that any bytes left over from a previous message are discarded
        msg = ""
        start_time = time.time()
        while msg.find("ready") == -1:
            print(f"Waiting for Arduino on {self.port}: bps={self.bps}, {self.p_1}/{self.p_2}/{self.p_3}")
            while self.ser.inWaiting() == 0:
                if time.time() - start_time >= timeout:
                    print(f"No reply after {self.wait_timeout} seconds")
                    return
            msg = self.receive()
        print(f"Connected to Arduino on {self.port}: bps={self.bps}, {self.p_1}/{self.p_2}/{self.p_3}")
        self.connected = True

    def debug_string(self):
        if self.connected:
            return f"Arduino CONNECTED on {self.port}: bps={self.bps}, {self.p_1}/{self.p_2}/{self.p_3}"
        else:
            return f"Arduino NOT found on {self.port}: bps={self.bps}, {self.p_1}/{self.p_2}/{self.p_3}"

    def send_command(self, command):
        if(self.connected):
            if command == self.last_command:
                print(f"command {command} already sent")
                return
            else:
                self.send(Arduino.commands[command])
                self.last_command = command

    def send_seq(self):
        print("Sending command")
        self.ser.write(b'$run,seq,0#')
        self.ser.flush()

    def send(self, string):
        if(self.connected):
            self.ser.write((string+"\n").encode())
            self.ser.flush()

    def close(self):
        self.ser.close()

    def receive(self):
        ck = ""
        x = "z" # any value that is not an end- or Arduino.startMarker
        byte_count = -1 # to allow for the fact that the last increment will be one too many

        # wait for the start character
        while ord(x) != Arduino.startMarker:
            x = self.ser.read()

        # save data until the end marker is found
        while ord(x) != Arduino.endMarker:
            if ord(x) != Arduino.startMarker:
              ck = ck + x
              byte_count += 1
            x = self.ser.read()
        return(ck)

class Twister():

    def __init__(self):
        self.input = Input()

        pygame.init()
        pygame.display.set_mode((Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT))
        pygame.display.set_caption("SWARM")
        screen = pygame.display.get_surface()
        self.scene = Scene(screen, self.input)

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

        game = Twister()
        game.run(spamwriter,arduino, tracking_quadrant=0, quad_command="quiver_0")
    arduino.close()

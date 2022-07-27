#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import re
import time
import sys
import getopt
import Constants
import serial
from serial.tools import list_ports


class Arduino():
    start_marker = "$"
    end_marker = "#"
    prefix="run"
    wait_timeout = 60 # Seconds, the longest command takes 48s
    statuses = ['Command SENT SUCCESFULLY', "Command ALREADY SENT", "Arduino is BUSY", "Arduino NOT CONNECTED"]

    commands = {
        "breathe":  "breathe",
        "undulate": "undulate",
        "glitch":   "glitch",
        "quiver":   "quiver",
        "default":  "default",
        "stop":     "stop",
        "done":     "runcomp"
    }

    def __init__(self, port="COM4", bps=115200, p_1=8, p_2="N", p_3=1, wait=True):
        self.port = port
        self._observers = []
        self.bps = bps
        self.p_1 = p_1
        self.p_2 = p_2
        self.p_3 = p_3
        self.is_connected = False
        self.last_command = "NO COMMAND SENT"
        self.status = "STATUS UNKNOWN"
        self.is_ready = False

        self.ser = serial.Serial()
        self.ser.baudrate = self.bps
        self.ser.port = self.port
        self.init()

        print(self.debug_string())
        # try:
        #     self.ser.open()
        #     self.is_connected = True
        #     if wait:
        #         self.wait_for_connection(Arduino.wait_timeout if wait else 0)
        #     else:
        #         self.is_connected = True
        # except Exception as e:
        #     print(f"Error opening serial port: {e}")
        
    def find_port(self):                
        prompt = "\n\nSelect Arduino port:\n"
        choice = -1
        ports = list(list_ports.comports())
        for i in range(0, len(ports)):
            prompt += f"{i}: {ports[i].device}\n"
        while choice < 0 or choice >= len(ports):
            try:
                choice = int(input(f"{prompt}\n"))
                port = ports[int(choice)].device
            except KeyboardInterrupt:
                sys.exit()
            except:
                print("Please select one of the choices above!")
        return port
    
    def init(self):
        while not self.is_ready:
            if self.port is None:
                self.port = self.find_port()
            try:
                self.ser = serial.Serial()
                self.ser.baudrate = self.bps
                self.ser.port = self.port
                print(f"Initializing Arduino on port {self.port}")
                self.ser.open()
                self.is_connected = True
                time.sleep(1)
                self.is_ready = True
            except Exception as e:
                self.is_connected = False
                self.is_ready = False
                print(f"Error opening port {self.port} for Arduino: {e}")
                self.port = None

    def build_command_str(self, command, loop=False):
        if command == 'stop':
            cmd_string = f"{self.start_marker}{command}{self.end_marker}"
        else:
            loop = 1 if loop else 0
            cmd_string = f"{self.start_marker}{self.prefix},{command},{loop}{self.end_marker}"
        return cmd_string
        
    def subscribe(self, observer):
        self._observers.append(observer)

    def notify_observers(self, *args, **kwargs):
        for obs in self._observers:
            obs.notify(self, *args, **kwargs)

    def unsubscribe(self, observer):
        self._observers.remove(observer)

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
        self.is_connected = True

    def debug_string(self):
        if self.is_connected:
            return f"Arduino CONNECTED on {self.port}: bps={self.bps}, {self.p_1}/{self.p_2}/{self.p_3}"
        else:
            return f"Arduino NOT found on {self.port}: bps={self.bps}, {self.p_1}/{self.p_2}/{self.p_3}"

    def send_command(self, command, loop=False, debug=True):
        if self.is_connected:
        # if True:
            if self.is_ready:
            # if True:
              if command == self.last_command:
                self.is_ready = False
                self.status = f"{self.last_command} + {self.statuses[1]}"
                return self.status
              else:
                cmd_string = self.build_command_str(command, loop)
                if debug:
                    print(f"Sending string: {cmd_string}")
                self.send(cmd_string)
                self.last_command = command
                self.is_ready = False
                self.status = f"{self.last_command} + {self.statuses[0]}"
              return self.status
            self.status = self.statuses[2]
            return self.status
        self.status = self.statuses[3]
        return self.status

    def send(self, string):
        if(self.is_connected):
            self.ser.write((string+"\n").encode())
            self.ser.flush()

    def close(self):
        self.ser.close()

    def update_status(self):
        if self.is_connected:
            try:
                received = self.receive()
                print(f"Received: {str(received)}")
                if "runcomp" in received:
                    print(f"Command Completed!")
                    self.is_ready = True
                    return self.is_ready
                # if received == Arduino.done:
                    # self.is_ready = True
            except serial.serialutil.SerialException:
                return self.is_ready
        self.is_ready = False
        return self.is_ready

    def receive(self):
        # byte_count = -1 # to allow for the fact that the last increment will be one too many

        # # wait for the start character
        # while ord(x) != Arduino.start_marker:
        #     x = self.ser.read()

        # # save data until the end marker is found
        # while ord(x) != Arduino.end_marker:
        #     if ord(x) != Arduino.start_marker:
        #       ck = ck + x
        #       byte_count += 1
        #     x = self.ser.read()
        ret = self.ser.readline()
        return(str(ret))
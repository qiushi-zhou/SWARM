#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import re
import time
import sys
import getopt
import Constants
import serial

class Arduino():
    start_marker = b"$"
    end_marker = b"#"
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
        "stop":      "$stop#",
        "done":      "$done#"
    }

    def __init__(self, port="COM4", bps=115200, p_1=8, p_2="N", p_3=1, wait=True):
        self._observers = []
        self.port = port
        self.bps = bps
        self.p_1 = p_1
        self.p_2 = p_2
        self.p_3 = p_3
        self.connected = False
        self.last_command = ""
        self.is_ready = False

        self.ser = serial.Serial()
        self.ser.baudrate = self.bps
        self.ser.port = self.port
        self.ser.open()
        self.connected = True
        time.sleep(1)
        self.is_ready = True
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
        self.connected = True

    def debug_string(self):
        if self.connected:
            return f"Arduino CONNECTED on {self.port}: bps={self.bps}, {self.p_1}/{self.p_2}/{self.p_3}"
        else:
            return f"Arduino NOT found on {self.port}: bps={self.bps}, {self.p_1}/{self.p_2}/{self.p_3}"

    def send_command(self, command):
        if self.connected:
            if self.is_ready:
              if command == self.last_command:
                  print(f"command {command} already sent")
                  return 2
              else:
                  self.send(Arduino.commands[command])
                  self.last_command = command
                  self.is_ready = False
              return 0
            return 3
        return 1

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

    def update_status(self):
      received = self.receive()
      if received == Arduino.done:
        self.is_ready = True
      return self.is_ready

    def receive(self):
        ck = ""
        x = "z" # any value that is not an end- or Arduino.start_marker
        byte_count = -1 # to allow for the fact that the last increment will be one too many

        # wait for the start character
        while ord(x) != Arduino.start_marker:
            x = self.ser.read()

        # save data until the end marker is found
        while ord(x) != Arduino.end_marker:
            if ord(x) != Arduino.start_marker:
              ck = ck + x
              byte_count += 1
            x = self.ser.read()
        return(ck)
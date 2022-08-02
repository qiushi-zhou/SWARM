#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import datetime
import re
import time
import sys
import getopt
import Constants
import serial
from serial.tools import list_ports

class ArduinoStatus():

    def __init__(self, status_id, name, description):
        self.id = status_id
        self.name = name
        self.description = description

class Arduino():
    start_marker = "$"
    end_marker = "#"
    prefix = "run"
    commands = {
        "breathe":  "breathe",
        "undulate": "undulate",
        "glitch":   "glitch",
        "quiver":   "quiver",
        "default":  "default",
        "stop":     "stop",
        "done":     "runcomp"
    }

    def __init__(self, port="COM4", bps=115200, p_1=8, p_2="N", p_3=1, time_between_commands=5, max_feedback_wait=10, max_execution_wait=60):
        self.port = port
        self._observers = []
        self.bps = bps
        self.p_1 = p_1
        self.p_2 = p_2
        self.p_3 = p_3
        self.last_command = None
        self.last_completed_command_time =  datetime.datetime.now()
        self.last_sent_command_time = datetime.datetime.now()
        self.last_status_update_time = datetime.datetime.now()
        self.time_between_commands = time_between_commands  # Seconds
        self.max_feedback_wait = max_feedback_wait  # Seconds, the longest command takes 48s
        self.max_execution_wait = max_execution_wait  # Seconds, the longest command takes 48s

        self.statuses = {
            'not_initialized': ArduinoStatus(-1, 'Not Initialized', 'Arduino not initialized'),
            'command_sent': ArduinoStatus(0, 'Command Sent', 'Command SENT SUCCESSFULLY, waiting for feedback...'),
            'command_received': ArduinoStatus(1, 'Executing Command', 'Command received by Arduino, waiting for completion...'),
            'cooling_down': ArduinoStatus(2, 'Cooling Down', f'Arduino is cooling down between commands {self.time_between_commands}'),
            'already_sent': ArduinoStatus(3, 'Command already sent', 'Command ALREADY SENT'),
            'not_connected': ArduinoStatus(4, 'NOT CONNECTED', 'Arduino NOT CONNECTED'),
            'debug_mode': ArduinoStatus(5, 'DEBUG MODE', 'Arduino NOT CONNECTED (debug mode)'),
            'ready': ArduinoStatus(6, 'READY', f'Arduino is ready to start a new command! Port {self.port}')
        }
        self.status = self.statuses['not_initialized']
        self.ser = serial.Serial()
        self.ser.baudrate = self.bps
        self.ser.port = self.port
        self.update_status()
    
    def debug_send_wait(self, cmd_string, manual_update=0, debug=True):
        self.send_command(cmd_string, debug=debug, testing_command=self.mockup_commands)
        if manual_update <= 0:
            print(f"Waiting for Arduino to be ready...")
            while self.status.id != self.statuses['ready'].id:
                self.update_status(debug=debug)
        else:
            help_str = f"\n\nManual update is on..."
            help_str += f"\nAny key - update arduino status"
            help_str += f"\nq - go back to previous menu"
            choice = ""
            while self.status.id != self.statuses['ready'].id and choice != 'q':
                choice = input(f"{help_str}\n")
                if choice == 'q':
                    return
                self.update_status(debug=debug)
            print("\nArduino is ready! Going back to previous menu!\n")
        return
        
    def debug_commands(self, manual_update=0, debug=True):
        choice = ""
        help_str = '\n\nSelect a command to send:\n'
        for i in range(0, len(self.commands.values())):
            cmd = list(self.commands.values())[i]
            help_str += f"{i} - {cmd:<10}:{self.build_command_str(cmd)}\n"
        help_str += f"\na - all in a loop\n"
        help_str += f"\nu - update arduino's status\n"
        help_str += f"q - exit\n"
        help_str += f"Update: {'AUTO' if manual_update <= 0 else 'MANUAL'}"

        while choice != 'q':
            choice = input(f"{help_str}\n")
            try:
                if choice == 'q':
                    return
                elif choice == 'a':
                    print(self.debug_string())
                    for cmd_i in range(0, len(self.commands.values())):
                        command = list(self.commands.values())[int(cmd_i)]
                        self.debug_send_wait(command, manual_update=manual_update, debug=debug)
                elif choice == 'u':
                    print(self.debug_string())
                    self.update_status()
                elif 0 <= int(choice) <= len(self.commands.values()):
                    print(self.debug_string())
                    command = list(self.commands.values())[int(choice)]
                    self.debug_send_wait(command, manual_update=manual_update, debug=debug)
                else:
                    print("Invalid choice!")
            except Exception as e:
                print(f"Error! : {e}")

    def find_port(self):          
        prompt = "\n\nSelect Arduino port:\n"
        prompt += "-1: Leave Arduino disconnected (debug)\n"
        choice = -2
        port = None
        ports = list(list_ports.comports())
        for i in range(0, len(ports)):
            prompt += f"{i}: {ports[i].device}\n"
        while choice < -1 or choice >= len(ports):
            try:
                choice = int(input(f"{prompt}\n"))
                if choice == -1:
                    return None
                port = ports[int(choice)].device
            except KeyboardInterrupt:
                sys.exit()
            except:
                print("Please select one of the choices above!")
        return port

    def init(self):
        print(f'Initializing Arduino...')
        if self.port is None:
            self.port = self.find_port()
            if self.port is None:
                print("Arduino disconnected (debug mode)")
                self.status = self.statuses["debug_mode"]
                return
        try:
            self.ser = serial.Serial()
            self.ser.baudrate = self.bps
            self.ser.port = self.port
            print(f"Initializing Arduino on port {self.port}, baud rate: {self.bps}")
            self.ser.open()
            time.sleep(1)
            # Flushing initial setup
            initial_string = ""
            while True:
                received = self.receive(prefix="Flushing init data...")
                if received is None:
                    break
                initial_string += received
            if len(initial_string) > 1:
                print(f"Flushed initial string: {initial_string}")
            self.status = self.statuses['ready']
        except Exception as e:
            print(f"Error opening port {self.port} for Arduino: {e}")
            self.status = self.statuses['not_initialized']
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

    def debug_string(self):
        if self.status.id != self.statuses['not_connected'].id:
            return f"Arduino CONNECTED on {self.port}: bps={self.bps}, {self.p_1}/{self.p_2}/{self.p_3}"
        else:
            if self.status.id == self.statuses["debug_mode"].id:
                return f"Arduino NOT CONNECTED (debug mode) on {self.port}: bps={self.bps}, {self.p_1}/{self.p_2}/{self.p_3}"
            return f"Arduino NOT found on {self.port}: bps={self.bps}, {self.p_1}/{self.p_2}/{self.p_3}"

    def send_command(self, command, loop=False, debug=True, testing_command=True):
        if self.status.id == self.statuses['ready'].id:
            cmd_string = self.build_command_str(command, loop)
            if debug:
                print(f"Sending command string: {cmd_string}")
            if not testing_command:
                self.send(cmd_string)
            self.last_command = command
            self.last_sent_command_time = datetime.datetime.now()
            prev_status = self.status
            self.status = self.statuses['command_sent']
            print(f"{'(Testing)' if testing_command else ''}Command '{self.last_command}' sent! Status updated: {prev_status.name} -> {self.status.name}!")
        else:
            print(f"Arduino not ready to receive command {command}, status {self.status.name}: {self.status.description}!")
        return self.status

    def send(self, string):
        self.ser.write((string+"\n").encode())
        self.ser.flush()

    def close(self):
        self.ser.close()

    def update_status(self, blocking_wait=False, debug=True):
        while self.status.id == self.statuses['not_initialized'].id:
            self.init()
        if self.status.id == self.statuses['not_connected'].id:
            return self.status
        elif self.status.id == self.statuses['cooling_down'].id:
            elapsed = (datetime.datetime.now() - self.last_completed_command_time).seconds
            if elapsed >= self.time_between_commands:
                self.status = self.statuses['ready']
                self.last_status_update_time = datetime.datetime.now()
            # else:
            #     print(f"Arduino is cooling down. Wait another {self.time_between_commands - elapsed} (Time between commands is set to {self.time_between_commands}s)")
        elif self.status.id == self.statuses['command_sent'].id:
            if (datetime.datetime.now() - self.last_sent_command_time).seconds >= self.max_feedback_wait:
                print(f"Max wait time waiting for feedback reached...")
                self.status = self.statuses['command_received']
            else:
                try:
                    received = self.receive(debug=debug, prefix="Waiting for received command msg")
                    if received is None:
                        received = ""
                except serial.serialutil.SerialException:
                    received = ""
                if "received" in received.lower():
                    print(f"Received feedback from Arduino!")
                    self.status = self.statuses['command_received']
        elif self.status.id == self.statuses['command_received'].id:
            if (datetime.datetime.now() - self.last_sent_command_time).seconds >= self.max_execution_wait:
                print(f"Max wait time between commands reached...")
                self.status = self.statuses['cooling_down']
                self.last_completed_command_time = datetime.datetime.now()
            else:
                while True:
                    try:
                        received = self.receive(debug=debug, prefix="Waiting for completiong msg")
                        if received is None:
                            received = ""
                    except serial.serialutil.SerialException:
                        received = ""
                    if "runcomp" in received:
                        print(f"Command Completed! Cooling down for {self.time_between_commands} seconds...")
                        self.last_completed_command_time = datetime.datetime.now()
                        self.last_command = None
                        self.status = self.statuses['cooling_down']
                        self.last_status_update_time = datetime.datetime.now()
                        break
                    if not blocking_wait:
                        break
        return self.status

    def receive(self, prefix="Received from Arduino", debug=False):
        ret = None
        if self.ser.in_waiting > 0:
            ret = self.ser.readline().decode('ascii')
            if debug:
                print(f"{prefix}: {ret}", end="")
        return ret
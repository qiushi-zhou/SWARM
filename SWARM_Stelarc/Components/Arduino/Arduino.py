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
import collections

class ArduinoStatus():

    def __init__(self, status_id=-1, title="", description="", timeout=0, prev_status_id=-1, next_status_id=-1, testing_timeout=0):
        self.id = status_id
        self.title = title
        self.description = description
        self.timeout = timeout
        self.testing_timeout = testing_timeout
        self.started_time = datetime.datetime.now()
        self.prev_status_id = prev_status_id
        self.next_status_id = next_status_id
        self.extra = ''

    def get_timeout(self, mockup_commands, not_operational):
        if mockup_commands or not_operational:
            return self.testing_timeout
        return self.timeout

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

    def __init__(self, port="COM4", bps=115200, p_1=8, p_2="N", p_3=1, config_data=None, mockup_commands=True):
        self.port = port
        self._observers = []
        self.bps = bps
        self.p_1 = p_1
        self.p_2 = p_2
        self.p_3 = p_3
        self.last_command = None
        self.mockup_commands = mockup_commands
        self.working_days = ["tue", "wed", "thu", "fri", "sat", "sun"]
        self.working_hours = ["10:45", "21:00"]

        self.default_statuses = {
            'not_initialized': ArduinoStatus(0, 'Not Initialized', 'Arduino not initialized', 0),
            'command_sent': ArduinoStatus(1, 'Command Sent', 'Command SENT SUCCESSFULLY, waiting for feedback...', 10),
            'command_received': ArduinoStatus(2, 'Executing Command', 'Command received by Arduino, waiting for completion...', 60),
            'cooling_down': ArduinoStatus(3, 'Cooling Down', f'Arduino is cooling down between commands {5}', 5),
            'already_sent': ArduinoStatus(4, 'Command already sent', 'Command ALREADY SENT', 0),
            'not_connected': ArduinoStatus(5, 'NOT CONNECTED', 'Arduino NOT CONNECTED', 0),
            'debug_mode': ArduinoStatus(6, 'DEBUG MODE', 'Arduino NOT CONNECTED (debug mode)', 0),
            'ready': ArduinoStatus(7, 'READY', f'Arduino is ready to start a new command! Port {self.port}', 0)
        }
        if config_data is None:
            self.statuses = self.default_statuses
            self.status = self.statuses['not_initialized']
        else:
            self.update_config(config_data)
            self.status = list(self.statuses.values())[0]
        self.ser = serial.Serial()
        self.ser.baudrate = self.bps
        self.ser.port = self.port

    def update_config(self, config_data=None):
        self.port = config_data.get('last_port', "COM4")
        self.working_hours = config_data.get('working_hours', self.working_hours)
        self.working_hours = [time.strptime(self.working_hours[0], "%H:%M"), time.strptime(self.working_hours[1], "%H:%M")]
        self.working_days = config_data.get('working_days', self.working_days)
        s_list = config_data.get('statuses', [])
        for s in s_list:
            name = s['name']
            if name not in self.statuses:
                self.statuses[name] = ArduinoStatus()
            self.statuses[name].title = s.get('title', 'NO TITLE')
            self.statuses[name].id = s.get('id', -1)
            self.statuses[name].description = s.get('description', 'NO DESCRIPTION')
            self.statuses[name].timeout = s.get('timeout', 0)
            self.statuses[name].testing_timeout = s.get('testing_timeout', 0)
            self.statuses[name].prev_status_id = s.get('prev_status_id', -1)
            self.statuses[name].next_status_id = s.get('next_status_id', -1)
    
    def debug_send_wait(self, cmd_string, manual_update=0, debug=True):
        self.send_command(cmd_string, debug=debug)
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
        if self.port is None:
            if self.mockup_commands:
                self.port = None
            else:
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
                initial_string += received.replace('\x00', '')
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

    def send_command(self, command, loop=False, debug=True, dbg_vals=''):
        if self.status.id == self.statuses['ready'].id:
            prefix = '(Normal)'
            cmd_string = self.build_command_str(command, loop)
            if debug:
                print(f"Sending command string: {cmd_string}")
            if not self.not_operational:
                if not self.mockup_commands:
                    print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Command {command} - {dbg_vals}")
                    self.send(cmd_string)
                else:
                    prefix = '(Testing)'
            else:
                prefix = '(Not Operational)'
            self.last_command = command
            prev_status = self.status
            self.status = self.statuses['command_sent']
            self.statuses['command_received'].extra = f"Waiting for confirmation ({command})"
            self.status.extra = f"{command} sent..."
            self.status.started_time = datetime.datetime.now()
            if debug:
                print(f"{e.strftime('%Y-%m-%d %H:%M:%S')} {prefix} Command '{self.last_command}' sent! Status updated: {prev_status.title} -> {self.status.title}!")
        else:
            if debug:
                print(f"Arduino not ready to receive command {command}, status {self.status.title}: {self.status.description}!")
        return self.status

    def send(self, string):
        self.ser.write((string+"\n").encode())
        self.ser.flush()

    def close(self):
        self.ser.close()

    def update_status(self, blocking_wait=False, debug=True):
        try:
            now = datetime.datetime.now()
            day = now.strftime('%A').lower()
            
            if any([True if x in day else False for x in self.working_days]):
                start = now.replace(hour=self.working_hours[0].tm_hour, minute=self.working_hours[0].tm_min, second=0, microsecond=0)
                end = now.replace(hour=self.working_hours[1].tm_hour, minute=self.working_hours[1].tm_min, second=0, microsecond=0)
                self.not_operational = not (start <= now <= end)
            else: self.not_operational = True
            
            # if debug:
            #     if self.not_operational:
            #         print(f"MACHINE NOT OPERATIONAL")

            for s_idx in self.statuses:
                s = self.statuses[s_idx]
                s.not_operational = self.not_operational

            while self.status.id == self.statuses['not_initialized'].id:
                self.init()
            if self.status.id == self.statuses['not_connected'].id:
                return self.status
            elif self.status.id == self.statuses['cooling_down'].id:
                elapsed = (datetime.datetime.now() - self.status.started_time).seconds
                if elapsed >= self.status.get_timeout(self.mockup_commands, self.not_operational):
                    self.status = self.statuses['ready']
                    self.status.started_time = datetime.datetime.now()
            elif self.status.id == self.statuses['command_sent'].id:
                if (datetime.datetime.now() - self.status.started_time).seconds >= self.status.get_timeout(self.mockup_commands, self.not_operational):
                    print(f"Max wait time waiting for feedback reached...")
                    self.status.extra = f"Arduino did not respond..."
                    self.status = self.statuses['command_received']
                    self.status.started_time = datetime.datetime.now()
                else:
                    try:
                        received = self.receive(debug=debug, prefix="Waiting for received command msg")
                        if received is None:
                            received = ""
                    except serial.serialutil.SerialException:
                        received = ""
                    if "received" in received.lower():
                        # print(f"Received feedback from Arduino!")
                        self.status = self.statuses['command_received']
                        self.status.extra = received.replace('\x00', '')
                        self.status.started_time = datetime.datetime.now()
            elif self.status.id == self.statuses['command_received'].id:
                if (datetime.datetime.now() - self.status.started_time).seconds >= self.status.get_timeout(self.mockup_commands, self.not_operational):
                    print(f"Max wait time between commands reached...")
                    self.status = self.statuses['cooling_down']
                    self.status.started_time = datetime.datetime.now()
                else:
                    while True:
                        try:
                            received = self.receive(debug=False, prefix="Waiting for completiong msg")
                            if received is None:
                                received = ""
                        except serial.serialutil.SerialException:
                            received = ""
                        if "runcomp" in received:
                            print(f"Command Completed: {received} ")
                            self.status = self.statuses['cooling_down']
                            self.status.extra = received.replace('\x00', '')
                            # print(f"Command Completed! Cooling down for {self.status.get_timeout(self.mockup_commands, self.not_operational)} seconds...")
                            self.status.started_time = datetime.datetime.now()
                            self.last_command = None
                            break
                        if not blocking_wait:
                            break
        except Exception as e:
            print(f"Error updating Arduino's status {e}")
        return self.status

    def receive(self, prefix="Received from Arduino", debug=False):
        ret = None
        if self.ser.in_waiting > 0:
            ret = self.ser.readline().decode('ascii')
            if debug:
                print(f"{prefix}: {ret}", end="")
        return ret

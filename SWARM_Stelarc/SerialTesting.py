#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import re
import time
from Arduino import Arduino
import sys
import getopt
import Constants
import serial

def send_wait(cmd_string):
  res = arduino.send_command(command)
  print(res)
  print("Waiting for Arduino...")
  while not arduino.is_ready:
    arduino.update_status()
  print(arduino.debug_string())
      
arduino = Arduino(port=None, wait=False)

choice = ""
help_str = '\n\nSelect a command to send:\n'
i = 1
for i in range(0, len(arduino.commands.values())):
  cmd = list(arduino.commands.values())[i]
  help_str += f"{i} - {cmd:<10}:{arduino.build_command_str(cmd)}\n"
help_str += f"\na - all in a loop\n"
help_str += f"q - exit\n"

while choice != 'q':
  choice = input(f"{help_str}\n")
  if choice == 'q':
    exit()
  elif choice == 'a':
    for cmd_i in range(0, len(arduino.commands.values())):
      command = list(arduino.commands.values())[int(cmd_i)]
      send_wait(command)

  elif int(choice) >= 0 and int(choice) <= len(arduino.commands.values()):
    command = list(arduino.commands.values())[int(choice)]
    send_wait(command)
    print(arduino.debug_string())
  else:
    print("Invalid choice!")



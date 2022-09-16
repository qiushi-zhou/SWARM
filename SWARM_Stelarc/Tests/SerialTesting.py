#!/usr/bin/env python
# -*- coding: utf-8 -*-
from Components.Arduino.ArduinoManager import ArduinoManager

arduino_manager = ArduinoManager(None, None, arduino_port=None, mockup_commands=True)
arduino_manager.update_config()
# arduino = Arduino(port=None, mockup_commands=True)
arduino_manager.arduino.debug_commands(manual_update=0, debug=True)




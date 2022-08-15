#!/usr/bin/env python
# -*- coding: utf-8 -*-
from Arduino import Arduino

arduino = Arduino(port=None, mockup_commands=True)
arduino.debug_commands(manual_update=0, debug=True)




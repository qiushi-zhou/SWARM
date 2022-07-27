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

arduino = Arduino(port=None, wait=False)
arduino.debug_commands()




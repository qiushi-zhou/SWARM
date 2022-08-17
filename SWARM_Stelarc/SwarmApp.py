#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path
from Utils.pylogger import log, FileLogWidget, ConsoleLogWidget, PyGameLogWidget
from Utils.utils import *
import datetime
import numpy as np
import Constants
import time
from sys import platform
from Components.GUIManager.SceneManager import *
from Components.VideoProcessor.VideoInputManager import VideoInputManager 
from Components.VideoProcessor.OpenposeManager import OpenposeManager 
from Components.Camera.CamerasManager import CamerasManager
from Components.Arduino.ArduinoManager import ArduinoManager
from Components.WebManager.WebSocketManager import WebSocketManager
from Components.SwarmManager.SwarmManager import SwarmManager


class SwarmAPP():
    def __init__(self, arduino_port="COM4", mockup_commands=True, multi_threaded=True):
        self.tag = "SwarmApp"
        
        self.components = []
        
        self.scene_manager = SceneManager(SceneDrawer.PYGAME, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT, Constants.font_size)
        self.logger = self.scene_manager.logger     
        self.components.append(self.scene_manager)
        
        self.video_manager = VideoInputManager(self.logger, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT, Constants.start_capture_index, multi_threaded=True)  
        self.components.append(self.video_manager)  
        
        self.cameras_manager = CamerasManager(self.logger, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT)   
        self.components.append(self.cameras_manager)
        
        if Constants.use_openpose:
            self.openpose_manager = OpenposeManager(self.logger, self.cameras_manager, multi_threaded=multi_threaded)
            self.components.append(self.openpose_manager)   
            
        self.arduino_manager = ArduinoManager(self.logger, arduino_port, mockup_commands)    
        self.components.append(self.arduino_manager)
            
        self.websocket_manager = WebSocketManager(self.logger)    
        self.components.append(self.websocket_manager)
            
        self.swarm_manager = SwarmManager(self.logger, self.arduino_manager)
        self.components.append(self.swarm_manager)
        
    
    def run(self, debug=False):
        offset = Point(10, 10)
        while True:
            if debug:
                e = datetime.datetime.now()
                print(f"--- Start loop ---\n\n{e.strftime('%Y-%m-%d %H:%M:%S')}")
            
            for component in self.components:
                component.update_config()
            
            self.video_manager.update()
            frame = self.video_manager.get_frame()
            self.scene_manager.update(frame, clean_frame=True, debug=debug)

            left_text_pos = Point(Constants.SCREEN_WIDTH * 0.5 + offset.x, Constants.SCREEN_HEIGHT * 0.5 + offset.y)
            right_text_pos = Point(Constants.SCREEN_WIDTH + offset.x, 0 + offset.y)
            
            self.arduino_manager.update(debug=debug)

            if Constants.use_openpose:
                self.openpose_manager.update(self.frame)
                frame = self.openpose_manager.get_updated_frame()

            self.cameras_manager.update(debug=debug)
            self.swarm_manager.update(self.cameras_manager.cameras, left_text_pos, right_text_pos, debug=True)
            self.websocket_manager.update(self.scene_manager.pygame, self.scene_manager.screen, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT)
            
            self.cameras_manager.draw(draw_graph_data=False)
            self.video_manager.draw(left_text_pos)
            
            self.websocket_manager.draw(left_text_pos, debug=debug)
            left_text_pos.y += self.logger.line_height
            
            self.arduino_manager.draw(left_text_pos, debug=debug)
            left_text_pos.y += self.logger.line_height

            self.scene_manager.update(frame, clean_frame=False, debug=debug)
            self.scene_manager.draw()

            if debug:
                print(f"--- End loop ---\n")
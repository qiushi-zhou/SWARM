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
from collections import deque


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
        
        if Constants.use_processing:
            self.openpose_manager = OpenposeManager(self.logger, self.cameras_manager, multi_threaded=False, use_openpose=Constants.use_openpose)
            self.components.append(self.openpose_manager)   
            
        self.arduino_manager = ArduinoManager(self.logger, arduino_port, mockup_commands)    
        self.components.append(self.arduino_manager)
            
        if Constants.use_websocket:
            self.websocket_manager = WebSocketManager(self.logger)    
            self.components.append(self.websocket_manager)
            
        self.swarm_manager = SwarmManager(self.logger, self.arduino_manager)
        self.components.append(self.swarm_manager)
        
        self.frame_buffer_size = 3
        self.frames_processed = deque([])
        self.frames_to_process = deque([])
    
    def run(self, debug=False):
        offset = Point(10, 10)
        while True:
            if debug:
                e = datetime.datetime.now()
                print(f"--- Start loop ---\n\n{e.strftime('%Y-%m-%d %H:%M:%S')}")
            left_text_pos = Point(Constants.SCREEN_WIDTH * 0.5 + offset.x, Constants.SCREEN_HEIGHT * 0.5 + offset.y)
            right_text_pos = Point(Constants.SCREEN_WIDTH + offset.x, 0 + offset.y)
            
            for component in self.components:
                component.update_config()
            
            self.video_manager.update()
            frame = self.video_manager.get_frame()
            self.frames_to_process.append(frame)
            # self.scene_manager.update(frame, clean_frame=True, debug=debug)
            
            left_text_pos = self.logger.add_text_line(f"Frames to process: {len(self.frames_to_process)}, Frames Processed: {len(self.frames_processed)}", (255, 255, 0), left_text_pos)

            if len(self.frames_to_process) < self.frame_buffer_size:
                continue # let the buffer build first!
            
            self.arduino_manager.update(debug=debug)
            new_frame_to_process = self.frames_to_process.popleft() if self.frames_to_process else None
            if Constants.use_processing:
                self.openpose_manager.update(new_frame_to_process)
                self.frames_processed.append(self.openpose_manager.get_updated_frame())
            else:
                self.frames_processed.append(new_frame_to_process)
            

            self.cameras_manager.update(debug=debug)
            
            self.video_manager.draw(left_text_pos)
            self.cameras_manager.draw(draw_graph_data=False)
            
            if Constants.use_websocket:
                self.websocket_manager.draw(left_text_pos, debug=debug)
            left_text_pos.y += self.logger.line_height
            
            self.swarm_manager.update(self.cameras_manager.cameras, left_text_pos, right_text_pos, debug=True)
            if Constants.use_websocket:
                self.websocket_manager.update(self.scene_manager.pygame, self.scene_manager.screen, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT)
            
            self.arduino_manager.draw(left_text_pos, debug=debug)
            left_text_pos.y += self.logger.line_height

            self.scene_manager.update(self.frames_processed.popleft() if self.frames_processed else None, debug=debug)
            self.scene_manager.draw()
                

            if debug:
                print(f"--- End loop ---\n")
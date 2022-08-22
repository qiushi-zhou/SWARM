#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import datetime
import Constants
from Components.SwarmLogger import SwarmLogger
from Components.GUIManager.SceneManager import SceneManager, SceneDrawerType
from Components.BackgroundTasksManager import BackgroundTasksManager
from Components.VideoProcessor.VideoInputManager import VideoInputManager 
from Components.VideoProcessor.OpenposeManager import OpenposeManager 
from Components.Camera.CamerasManager import CamerasManager
from Components.Arduino.ArduinoManager import ArduinoManager
from Components.WebManager.WebSocketManager import WebSocketManager
from Components.SwarmManager.SwarmManager import SwarmManager
from Components.Utils.utils import Point
from Components.Utils import utils


class SwarmAPP():
    def __init__(self, arduino_port="COM4", mockup_commands=True, multi_threaded=True):
        self.tag = "SwarmApp"
        self.logger = SwarmLogger()
        self.last_modified_time = -1
        self.use_processing = False
        self.use_openpose = False
        self.multithreaded_processing = False
        self.use_websocket = False
        utils.update_config_from_file("SwarmApp", r"Config/AppConfig.yaml", self.last_modified_time, self.update_data)
        self.components = []

        self.tasks_manager = BackgroundTasksManager(self.logger)
        self.scene_manager = SceneManager(self.logger, self.tasks_manager, SceneDrawerType.PYGAME, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT, Constants.font_size)
        self.components.append(self.scene_manager)
        
        self.video_manager = VideoInputManager(self.logger, self.tasks_manager, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT, Constants.start_capture_index, multi_threaded=True)
        self.components.append(self.video_manager)  
        
        self.cameras_manager = CamerasManager( self.logger, self.tasks_manager, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT)   
        self.components.append(self.cameras_manager)

        self.openpose_manager = OpenposeManager( self.logger, self.tasks_manager, self.cameras_manager, use_processing=self.use_processing, use_openpose=self.use_openpose)
        self.components.append(self.openpose_manager)
            
        self.arduino_manager = ArduinoManager(self.logger, self.tasks_manager, arduino_port, mockup_commands)
        self.components.append(self.arduino_manager)

        self.websocket_manager = WebSocketManager(self.logger, self.tasks_manager, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT)
        self.components.append(self.websocket_manager)
            
        self.swarm_manager = SwarmManager(self.logger, self.tasks_manager, self.arduino_manager)
        self.components.append(self.swarm_manager)

    def update_data(self, data, last_modified_time):
        self.use_processing = data.get("use_processing", False)
        self.use_openpose = data.get("use_openpose", False)
        self.multithreaded_processing = data.get("multithreaded_processing", False)
        self.use_websocket = data.get("use_websocket", False)
        self.last_modified_time = last_modified_time
    
    def run(self, debug=False):
        debug = False
        offset = Point(10, 10)
        running = True
        while running:
            for event in self.scene_manager.pygame.event.get():
                if event.type == self.scene_manager.pygame.QUIT:
                    running = False
            if debug:
                e = datetime.datetime.now()
                print(f"--- Start loop ---\n\n{e.strftime('%Y-%m-%d %H:%M:%S')}")
            left_text_pos = Point(Constants.SCREEN_WIDTH * 0.5 + offset.x, Constants.SCREEN_HEIGHT * 0.5 + offset.y)
            right_text_pos = Point(Constants.SCREEN_WIDTH + offset.x, 0 + offset.y)

            utils.update_config_from_file("SwarmApp", r"./Config/AppConfig.yaml", self.last_modified_time, self.update_data)
            self.tasks_manager.update_config()
            self.scene_manager.update_config()
            self.video_manager.update_config()
            self.openpose_manager.update_config(self.use_processing, self.use_openpose, self.multithreaded_processing)
            self.swarm_manager.update_config()
            self.cameras_manager.update_config()

            self.arduino_manager.update_config()
            self.arduino_manager.update(debug=debug)

            self.websocket_manager.update_config(self.use_websocket)
            self.video_manager.update()
            frame = self.video_manager.get_frame()
            processed_frame = frame
            processed_frame = self.openpose_manager.update_frames(frame)
            self.websocket_manager.update_frame(processed_frame)
            self.openpose_manager.update(debug=debug, surfaces=[self.scene_manager.tag, self.websocket_manager.tag])
            self.openpose_manager.update(debug=debug, surfaces=[self.scene_manager.tag])
            self.scene_manager.update(processed_frame, debug=False)

            # self.websocket_manager.update_surface(processed_frame)

            self.cameras_manager.update(debug=debug)

            self.video_manager.draw(left_text_pos, debug=debug, surfaces=[self.scene_manager.tag])
            self.openpose_manager.draw(left_text_pos, debug=debug, surfaces=[self.scene_manager.tag])
            self.tasks_manager.draw(left_text_pos, debug=debug, surfaces=[self.scene_manager.tag])
            self.cameras_manager.draw(draw_graph_data=False, debug=debug, surfaces=[self.scene_manager.tag])

            self.websocket_manager.draw(left_text_pos, debug=debug, surfaces=[self.scene_manager.tag])
            left_text_pos.y += self.logger.line_height
            
            self.swarm_manager.update(self.cameras_manager.cameras, left_text_pos, right_text_pos, debug=False, surfaces=[self.scene_manager.tag])
            
            self.arduino_manager.draw(left_text_pos, debug=debug, surfaces=[self.scene_manager.tag])
            left_text_pos.y += self.logger.line_height

            self.scene_manager.draw(debug=debug, surfaces=[self.scene_manager.tag])

            if debug:
                print(f"--- End loop ---\n")
        self.tasks_manager.stop_all()

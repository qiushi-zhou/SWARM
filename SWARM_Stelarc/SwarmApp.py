#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import datetime
import Constants
from Components.UIDrawer import UIDrawer
from Components.GUIManager.SceneManager import SceneManager, SceneDrawerType
from Components.BackgroundTasksManager import BackgroundTasksManager
from Components.VideoProcessor.VideoInputManager import VideoInputManager
from Components.VideoProcessor.ProcessingManager import ProcessingManager
from Components.Camera.CamerasManager import CamerasManager
from Components.Arduino.ArduinoManager import ArduinoManager
from Components.WebManager.WebSocketsManager import WebSocketsManager
from Components.SwarmManager.SwarmManager import SwarmManager
from Components.Utils.utils import Point
from Components.Utils import utils
from Components.Logger import app_logger



class SwarmAPP:
  def __init__(self, arduino_port="COM4", mockup_commands=True):
    self.tag = "SwarmApp"
    self.ui_drawer = UIDrawer()
    self.last_modified_time = -1
    self.processing_type = False
    self.config_data = None

    self.tasks_manager = BackgroundTasksManager(app_logger, self.ui_drawer)
    self.scene_manager = SceneManager(app_logger, self.ui_drawer, self.tasks_manager, SceneDrawerType.PYGAME, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT, Constants.font_size)
    self.video_manager = VideoInputManager(app_logger, self.ui_drawer, self.tasks_manager, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT)
    self.cameras_manager = CamerasManager(app_logger, self.ui_drawer, self.tasks_manager, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT)
    self.local_processing_manager = ProcessingManager("LC", app_logger, self.ui_drawer, self.tasks_manager, self.cameras_manager)
    # self.stream_processing_manager = ProcessingManager("ST", self.ui_drawer, self.tasks_manager, self.cameras_manager, cont_color=(255,0,0))
    self.arduino_manager = ArduinoManager(app_logger, self.ui_drawer, self.tasks_manager, arduino_port, mockup_commands)
    self.websocket_manager = WebSocketsManager(app_logger, self.ui_drawer, self.tasks_manager, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT)
    self.swarm_manager = SwarmManager(app_logger, self.ui_drawer, self.tasks_manager, self.arduino_manager, self.websocket_manager)

  def update_data(self, data, last_modified_time):
    self.processing_type = data.get("processing", False)
    self.video_manager.multi_threaded = data.get("mt_capture", False)
    self.local_processing_manager.processing_type = data.get("processing", 'simple')
    self.local_processing_manager.multi_threaded = data.get("mt_processing", False)
    # self.stream_processing_manager.processing_type = data.get("processing", 'simple')
    # self.stream_processing_manager.multi_threaded = data.get("mt_processing", False)
    self.arduino_manager.multi_threaded = data.get("mt_arduino", False)
    self.websocket_manager.multi_threaded = data.get("mt_networking", False)
    self.websocket_manager.enabled = data.get("websocket_enabled", False)
    self.last_modified_time = last_modified_time
    self.config_data = data

  def update_config(self):
    self.tasks_manager.update_config()
    self.scene_manager.update_config()
    self.video_manager.update_config()
    self.local_processing_manager.update_config()
    # self.stream_processing_manager.update_config()
    self.swarm_manager.update_config()
    self.cameras_manager.update_config()
    self.arduino_manager.update_config()
    self.websocket_manager.update_config()
    utils.update_config_from_file(app_logger, "SwarmApp", r"./Config/AppConfig.yaml", self.last_modified_time, self.update_data)
    self.local_processing_manager.update_config()
    # self.stream_processing_manager.update_config()

  def start_managers(self):
    self.update_config()
    self.tasks_manager.init()
    self.scene_manager.init()
    self.video_manager.init(Constants.start_capture_index)
    self.local_processing_manager.init()
    # self.stream_processing_manager.init()
    self.swarm_manager.init()
    self.cameras_manager.init()
    self.arduino_manager.init()
    self.websocket_manager.init()

    self.websocket_manager.send_config_update(
      {
       "app": {"data" :self.config_data, "time" : self.last_modified_time},
        "cameras": {"data": self.cameras_manager.config_data, "time": self.cameras_manager.last_modified_time},
        "arduino": {"data": self.arduino_manager.config_data, "time": self.arduino_manager.last_modified_time},
        "swarm": {"data": self.swarm_manager.config_data, "time": self.swarm_manager.last_modified_time},
        "websockets": {"data": self.websocket_manager.config_data, "time": self.websocket_manager.last_modified_time}
      }
    )

  def update_components(self, debug=False):
      self.update_config()
      # self.video_manager.add_stream_frame(self.websocket_manager.get_stream_frame("/online_interaction"))
      local_frame = self.video_manager.get_frame()
      processed_local_frame = self.local_processing_manager.get_processed_frame(local_frame, return_last=True)
      self.local_processing_manager.update(debug=debug, surfaces=[self.scene_manager.tag])

      # stream_frame = self.websocket_manager.get_stream_frame("/online_interaction")
      # remote_command = self.websocket_manager.get_last_remote_command("/online_interaction")
      # stream_frame = self.websocket_manager.get_stream_frame("/online_interaction")
      # processed_stream_frame = self.stream_processing_manager.get_processed_frame(stream_frame, return_last=False)
      # self.stream_processing_manager.update(debug=debug, surfaces=[self.scene_manager.tag])

      self.scene_manager.update(processed_local_frame, debug=False)

      # self.websocket_manager.enqueue_frame("/online_interaction", processed_stream_frame, self.cameras_manager.get_cameras_data())
      # self.websocket_manager.enqueue_frame("/gallery_stream", processed_local_frame, self.cameras_manager.get_cameras_data(), self.swarm_manager.get_swarm_data())

      self.cameras_manager.update(debug=debug)
      self.arduino_manager.update(debug=debug)
      self.swarm_manager.update(self.cameras_manager.cameras, debug=False, surfaces=[self.scene_manager.tag])

  def draw_components(self, debug, left_text_pos, right_text_pos):
      self.video_manager.draw(left_text_pos, debug=debug, surfaces=[self.scene_manager.tag])
      self.local_processing_manager.draw(left_text_pos, debug=debug, surfaces=[self.scene_manager.tag])
      # self.stream_processing_manager.draw(left_text_pos, debug=debug, surfaces=[self.scene_manager.tag])
      self.tasks_manager.draw(left_text_pos, debug=debug, surfaces=[self.scene_manager.tag])
      self.cameras_manager.draw(draw_graph_data=False, debug=debug, surfaces=[self.scene_manager.tag])
      self.websocket_manager.draw(left_text_pos, debug=debug, surfaces=[self.scene_manager.tag])

      self.swarm_manager.draw(left_text_pos, right_text_pos, debug=debug, surfaces=[self.scene_manager.tag])
      self.arduino_manager.draw(right_text_pos, debug=debug, surfaces=[self.scene_manager.tag])
      right_text_pos.y += self.ui_drawer.line_height

      self.scene_manager.draw(debug=debug, surfaces=[self.scene_manager.tag])

  async def run(self, debug=False):
    debug = False
    offset = Point(10, 10)
    self.start_managers()
    running = True
    while running:
      for event in self.scene_manager.pygame.event.get():
        if event.type == self.scene_manager.pygame.QUIT:
          running = False
      if debug:
        e = datetime.datetime.now()
        app_logger.debug(f"--- Start loop ---\n\n{e.strftime('%Y-%m-%d %H:%M:%S')}")
      left_text_pos = Point(Constants.SCREEN_WIDTH * 0.5 + offset.x, Constants.SCREEN_HEIGHT * 0.5 + offset.y)
      right_text_pos = Point(Constants.SCREEN_WIDTH + offset.x, 0 + offset.y)

      self.update_components(debug)
      self.draw_components(debug, left_text_pos, right_text_pos)


      if debug:
        app_logger.debug(f"--- End loop ---\n")
    self.tasks_manager.stop_all()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path

from SwarmLogger import SwarmLogger
import utils
from Input import Input
from Scene import Scene
import datetime
import cv2
import numpy as np
import Constants
import pygame
from Arduino import Arduino
from people_graph import *
import time
from sys import platform
import oyaml as yaml
from Camera import Camera
from FrameBufferData import FrameBuffer
from utils import Point
import asyncio
import socketio
import base64
import logging
import json
import io


class WebSocket:

    def __init__(self, url, namespace, enabled=False):
        # self.sio = socketio.Client(logger=True, engineio_logger=True)
        self.sio = socketio.Client()
        self.url = url
        self.namespace = namespace
        self.uri = url +"/" + namespace
        self.ws_connected = False
        self.ws_enabled = enabled

    def setup(self):
        if self.ws_enabled:
            self.call_backs()
            print(f"Connecting to WebSocket on: {self.uri}")
            self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=2)
            # self.sio.wait()

    def encode_image_data(self, image_data):
        img_str = base64.b64encode(image_data.getvalue())
        return "data:image/jpeg;base64," + img_str.decode()

    def send_data(self, image_data):
        if self.ws_enabled and self.sio.connected:
            try:
                img_data_str = self.encode_image_data(image_data)
                t = datetime.datetime.now()
                # self.sio.start_background_task(self.sio.emit, 'op_frame', {'frame_data': img_data_str, 'time':datetime.datetime().now().ctime()})
                # self.sio.emit(event='op_frame', data={'frame_data': img_data_str, 'time_ms': time.mktime(t.timetuple()), "datetime": t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}, namespace=self.namespace)
                self.sio.emit(event='op_frame', data={'frame_data': img_data_str}, namespace=self.namespace)
                # self.sio.emit(event='op_frame', data={"WHAT":"what"}, namespace=self.namespace)
                # self.sio.emit('op_frame', {'frame_data': '', 'time_ms': time.mktime(t.timetuple()), "datetime": t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}, namespace=self.namespace)
                # self.sio.wait()
            except Exception as e:
                print(f"Error sending data to socket {e}")
        else:
            print(f"WS NOT CONNECTED!")

    def call_backs(self):
        @self.sio.event
        def connect():
            print(f"Connected to to WebSocket on: {self.uri}")

        @self.sio.on("docs")
        def raw_data(data):
            print(f"Data Received!")
            # print(f"Data Received {data}")


        @self.sio.event
        def auth(data):
            print(f"Data Received")
            # print(f"Data Received {data}")

        @self.sio.event
        def disconnect():
            pass
    def draw_debug(self, logger, start_pos, debug=False):
        dbg_str = "WebSocket "
        if not self.ws_enabled:
            dbg_str += "Disabled"
        else:
            dbg_str += "Connected " if self.ws_connected else "NOT Connected"
        start_pos = logger.add_text_line(dbg_str, (255, 50, 0), start_pos)


class SwarmAPP():
    def __init__(self, observable=None, arduino_port="COM4", ws_enabled=False, mockup_commands=True):
        self.arduino = Arduino(port=arduino_port, mockup_commands=mockup_commands)
        if observable:
            observable.subscribe(self)
        self.mockup_commands = mockup_commands
        self.cv2 = cv2
        self.capture_index = 2
        self.capture0 = None
        self.frame = None
        self.cameras_config = None
        self.behavior_config = None
        self.arduino_config = None
        self.behaviors = []
        self.cameras = []
        self.update_cameras_config()
        self.update_behaviors_config()
        self.update_arduino_config()
        self.frame_buffer = FrameBuffer(self.behavior_config.get('buffer_size', 10))
        self.current_behavior = None
        self.font = None
        self.logger = None
        while True:
            try:
                if platform == "win32":
                    self.capture0 = cv2.VideoCapture(self.capture_index, cv2.CAP_DSHOW)
                else:
                    # On MacOS, make sure to install opencv with "brew install opencv" and then link it with "brew link --overwrite opencv"
                    # Also remove CAP_DSHOW for MacOS
                    self.capture0 = cv2.VideoCapture(self.capture_index, cv2.CAP_AVFOUNDATION)
                time.sleep(1)
                if self.capture0.isOpened():  # Checks the stream
                    print(f"VideoCapture {self.capture_index} OPEN")
                    break
                else:
                    print(f"VideoCapture {self.capture_index} CLOSED")
                    self.capture_index += 1
                if self.capture_index > Constants.max_capture_index:
                    break
            except Exception as e:
                print(f"Exception opening VideoCapture {self.capture_index}, stopping...")
                return

        self.capture0.set(self.cv2.CAP_PROP_FRAME_WIDTH, Constants.SCREEN_WIDTH)
        self.capture0.set(self.cv2.CAP_PROP_FRAME_HEIGHT, Constants.SCREEN_HEIGHT)
        self.frameSize = (int(self.capture0.get(self.cv2.CAP_PROP_FRAME_WIDTH)),
                          int(self.capture0.get(self.cv2.CAP_PROP_FRAME_HEIGHT)))
        # Constants.SCREEN_WIDTH = self.frameSize[0]
        # Constants.SCREEN_HEIGHT = self.frameSize[1]

        self.input = Input(self, cv2)
        pygame.init()
        pygame.display.set_mode((int(Constants.SCREEN_WIDTH+Constants.SCREEN_WIDTH*0.27), Constants.SCREEN_HEIGHT))
        pygame.display.set_caption("SWARM")
        # if you want to use this module.
        screen = pygame.display.get_surface()
        self.scene = Scene(screen)
        # self.async_loop = asyncio.get_event_loop()
        self.screenshot_filename = 'tempOP.jpeg'
        self.sio = WebSocket(Constants.ws_url, Constants.ws_namespace, ws_enabled)
        self.sio.setup()

    def notify(self, observable, *args, **kwargs):
        print('Got', args, kwargs, 'From', observable)

    def update_behaviors_config(self):
        file_path = r'./Behaviour_Config.yaml'
        if self.behavior_config is None or (self.behavior_config['last_modified_time'] < os.path.getmtime(file_path)):
            print(f"Updating Behaviors configuration from file...")
            try:
                with open(file_path) as file:
                    self.behavior_config = yaml.load(file, Loader=yaml.FullLoader)
                    self.behaviors = self.behavior_config.get("behaviors", [])
                self.behavior_config['last_modified_time'] = os.path.getmtime(file_path)
            except Exception as e:
                print(f"Error opening behavior config file {e}")
                return

    def update_cameras_config(self):
        file_path = r'./CamerasConfig.yaml'
        if self.cameras_config is None or (self.cameras_config['last_modified_time'] < os.path.getmtime(file_path)):
            print(f"Updating Cameras configuration from file...")
            try:
                with open(file_path) as file:
                    self.cameras_config = yaml.load(file, Loader=yaml.FullLoader)
            except:
                return
            cameras_data = self.cameras_config.get("cameras", [])
            threshold = self.cameras_config.get("group_distance_threshold", -1)
            for i in range(0, len(cameras_data)):
                cameras_data[i]["group_distance_threshold"] = threshold
                if len(self.cameras) <= i:
                    self.cameras.append(Camera(i, Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT, cameras_data[i]))
                else:
                    self.cameras[i].update_config(Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT, cameras_data[i])
            self.cameras_config['last_modified_time'] = os.path.getmtime(file_path)

    def update_arduino_config(self):
        file_path = r'./ArduinoConfig.yaml'
        if self.arduino_config is None or (self.arduino_config['last_modified_time'] < os.path.getmtime(file_path)):
            print(f"Updating Cameras configuration from file...")
            try:
                with open(file_path) as file:
                    self.arduino_config = yaml.load(file, Loader=yaml.FullLoader)
            except:
                return
            self.arduino.update_config(self.arduino_config)
            self.arduino_config['last_modified_time'] = os.path.getmtime(file_path)

    def update_tracks(self, tracks, keypoints, logger, debug=True):
        if debug:
            print(f"Updating tracks")
        for camera in self.cameras:
            camera.p_graph.init_graph()

        for track in tracks:
            color = (255, 255, 255)
            if not track.is_confirmed():
                color = (0, 0, 255)
            bbox = track.to_tlbr()
            p1 = Point(int(bbox[0]), int(bbox[1]))
            p2 = Point(int(bbox[2]), int(bbox[3]))
            min_p = Point(min(p1.x, p2.x), min(p1.y, p2.y))
            chest_offset = Point(0, 0)
            center_x, center_y = (min_p.x + ((p2.x-p1.x)/2) + chest_offset.x, min_p.y + ((p2.y-p1.y)/2) + chest_offset.y) # ((x1+x2)/2, (y1+y2)/2).
            center_p = Point(center_x, center_y)
            # if Constants.draw_openpose:
            #     if draw_type == 'cv':
            #         drawer.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), color, 1)
            #         drawer.putText(frame, "id%s - ts%s" % (track.track_id, track.time_since_update), (int(bbox[0]), int(bbox[1]) - 20), 0, 0.3, (0, 255, 0), 1)
            #     else:
            #         drawer.draw.rect(frame, color, pygame.Rect(int(bbox[0]), int(bbox[1]), int(bbox[2])-int(bbox[0]), int(bbox[3])-int(bbox[1])), 1)

            color = (0,255,0)
            thickness = 1
            if track.is_confirmed():
                for pair in self.input.POSE_PAIRS:
                    idFrom = self.input.BODY_PARTS[pair[0]]
                    idTo = self.input.BODY_PARTS[pair[1]]
                    points = track.last_seen_detection.pose
                    if points[idFrom] is not None and points[idTo] is not None:
                        kp1 = points[idFrom]
                        kp2 = points[idTo]
                        p1 = Point(kp1[0], kp1[1])
                        p2 = Point(kp2[0], kp2[1])
                        if p1.x > 1 and p1.y > 1 and p2.x > 1 and p2.y > 1:
                            logger.draw_line(p1, p2, color, thickness)
            for camera in self.cameras:
                # camera.check_track([p1,p2], center_p)
                camera.check_track([center_p], center_p)
            if debug:
                print(f"Center: ({center_x:.2f}, {center_y:.2f})")

    def update_cameras_data(self, debug=True):
        if debug:
            print(f"Updating Cameras data")
        for camera in self.cameras:
            if camera.enabled:
                camera.update_graph()

    def check_parameter(self, param, param_name, behavior, is_running, frame_buffer, text_pos, inactive_color, active_color, debug=False):
        param_name = param_name.lower()
        enabled = param.get("enabled", True)
        if not enabled:
            return False, enabled
        value = -1
        if param_name == "time":
            last_time = behavior.get("last_executed_time", None)
            if last_time is None:
                return True, enabled
            timeout = param.get("timeout", 600)
            elapsed = (datetime.datetime.now() - last_time).seconds
            if debug:
                if is_running:
                    text_pos = self.logger.add_text_line(f"{param_name}: {elapsed}/{timeout}", active_color, text_pos)
                else:
                    text_pos = self.logger.add_text_line(f"  {param_name}: {elapsed}/{timeout}", inactive_color, text_pos)
            if elapsed >= timeout:
                return True, enabled
            return False, enabled
        elif param_name == "people":
            value = frame_buffer.people_data.avg
        elif param_name == "groups":
            value = frame_buffer.groups_data.avg
        elif param_name == "people_in_groups_ratio":
            value = 0
            if frame_buffer.people_data.avg > 0:
                value = frame_buffer.groups_data.avg / frame_buffer.people_data.avg
        elif param_name == "avg_distance_between_people":
            value = frame_buffer.distance_data.avg
        elif param_name == "avg_distance_from_machine":
            value = frame_buffer.machine_distance_data.avg

        min_value = param.get('min', 0)
        max_value = param.get('max', 0)
        criteria_met = min_value <= value <= max_value
        if is_running:
            color = active_color
        else:
            if criteria_met:
                color = (inactive_color[0] * 1.5, inactive_color[1] * 1.5, inactive_color[2] * 1.5)
            else:
                color = inactive_color
        text_pos = self.logger.add_text_line(f"  {param_name}: {min_value} < {value:.2f} < {max_value}", color, text_pos)
        return criteria_met, enabled

    def check_behavior(self, behavior, curr_behavior, right_text_pos, debug=False):
        right_text_pos_orig = Point(right_text_pos.x, right_text_pos.y)
        right_text_pos.y += self.logger.line_height
        # print(f"Checking Behaviour: {behavior}")
        enabled = behavior.get("enabled", True)
        total_enabled_criteria = 0
        criteria_met = 0
        name = behavior.get('name', 'unknown')
        curr_behavior_name = curr_behavior.get('name', 'None')
        is_running = (name == curr_behavior_name)
        inactive_color = (140, 0, 140)
        active_color = (255, 200, 0)
        if debug:
            color = active_color if is_running else inactive_color
            prefix = 'x'
            postfix = ''
            if enabled:
                prefix = '-'
            else:
                postfix = '(disabled)'
            if name == curr_behavior_name:
                prefix = '>'
                postfix = '(running)'
        else:
            if not enabled:
                return False

        parameters = behavior.get("parameters", [])
        for param_name in parameters:
            criterium_met, is_enabled = self.check_parameter(parameters[param_name], param_name, behavior, is_running, self.frame_buffer, right_text_pos, inactive_color, active_color, debug=debug)
            criteria_met += 1 if criterium_met else 0
            total_enabled_criteria += 1 if is_enabled else 0
        right_text_pos.y += self.logger.line_height
        self.logger.add_text_line(f"{prefix} {name.upper()} {postfix} {criteria_met}/{total_enabled_criteria}", color, right_text_pos_orig)
        return criteria_met == total_enabled_criteria

    def update_action(self, left_text_pos, right_text_pos, debug=True):
        text_debug = False
        right_text_pos_orig = Point(right_text_pos.x, right_text_pos.y)
        right_text_pos.y += self.logger.line_height*1.5
        self.current_behavior = None
        self.frame_buffer.add_frame_data(self.cameras)
        action_updated = False
        # if self.frame_buffer.empty_frames > 0:
        #     return left_text_pos, right_text_pos
        for behavior in self.behaviors:
            all_criteria_met = self.check_behavior(behavior, {}, right_text_pos, debug=debug)
            if all_criteria_met and not action_updated:
                action_updated = True
                self.current_behavior = behavior
                name = self.current_behavior.get("name", "unknown")
                command = self.current_behavior.get("arduino_command", "")
                if text_debug:
                    print(f"Action updated: {name} ({command})")
                    print(f"\r\nNew ACTION: Running command {command} from behavior {name}\n\r")
                self.arduino.send_command(command, debug=text_debug)
                behavior["last_executed_time"] = datetime.datetime.now()
                # We found the command to execute so we can stop here
                if not debug:
                    return
        curr_behavior_name = self.current_behavior.get('name', 'NONE').upper() if self.current_behavior is not None else '-'
        self.logger.add_text_line(f"Current Behaviour: {curr_behavior_name}", (255, 0, 0), right_text_pos_orig)
        b_color = (150, 150, 150) if curr_behavior_name == "None" else (255, 255, 0)
        left_text_pos = self.logger.add_text_line(f"Running Action {curr_behavior_name}", b_color, left_text_pos)
        data = self.frame_buffer.people_data
        left_text_pos = self.logger.add_text_line(
            f"People - avg: {data.avg:.2f}, minmax: [{data.min:.2f}, {data.max:.2f}], n: {data.non_zeroes}/{self.frame_buffer.size()}",
            b_color, left_text_pos)
        data = self.frame_buffer.groups_data
        left_text_pos = self.logger.add_text_line(
            f"Groups - avg: {data.avg:.2f}, minmax: [{data.min:.2f}, {data.max:.2f}], n: {data.non_zeroes}/{self.frame_buffer.size()}",
            b_color, left_text_pos)
        data = self.frame_buffer.distance_data
        left_text_pos = self.logger.add_text_line(
            f"P_Distance - avg: {data.avg:.2f}, minmax: [{data.min:.2f}, {data.max:.2f}], n: {data.non_zeroes}/{self.frame_buffer.size()}",
            b_color, left_text_pos)
        data = self.frame_buffer.machine_distance_data
        left_text_pos = self.logger.add_text_line(
            f"M_Distance - avg: {data.avg:.2f}, minmax: [{data.min:.2f}, {data.max:.2f}], n: {data.non_zeroes}/{self.frame_buffer.size()}",
            b_color, left_text_pos)
        return

    def draw_cameras_debug(self, draw_graph_data):
        for i in range(0, len(self.cameras)):
            camera = self.cameras[i]
            camera.draw_debug(self.logger, draw_graph_data=draw_graph_data)

    def update_map(self):
        height = 500
        width = 500
        map_canvas = np.ones((height, width, 3), np.uint8)
        map_canvas *= 255
        self.cv2.circle(map_canvas, (int(height/2), int(width/2)), Constants.inner_radius, (0, 0, 0), 2)
        self.cv2.circle(map_canvas, (int(height/2), int(width/2)), Constants.outer_radius, (0, 0, 0), 2)
        self.cv2.imshow("SWARM map", map_canvas)

    def run(self, debug=False):
        draw_type = SwarmLogger.PYGAME
        if draw_type == SwarmLogger.PYGAME:
            self.font = pygame.font.SysFont('Cascadia', Constants.font_size)
            self.logger = SwarmLogger(pygame, self.scene.screen, font=self.font, font_size=Constants.font_size)
        else:
            self.logger = SwarmLogger(self.cv2, None, font=None, font_size=0.4)

        offset = Point(10, 10)
        image_data = io.BytesIO()
        while True:
            if debug:
                print(f"--- Start loop ---")
                e = datetime.datetime.now()
                print(f"\r\n{e.strftime('%Y-%m-%d %H:%M:%S')}", end="\r")

            result, self.frame = self.capture0.read()
            if self.logger.draw_type == SwarmLogger.OPENCV:
                self.logger.update_canvas(self.frame)
            else:
                self.scene.update(self.cv2.cvtColor(self.frame, self.cv2.COLOR_BGR2RGB), debug=debug)

            left_text_pos = Point(Constants.SCREEN_WIDTH * 0.5 + offset.x, Constants.SCREEN_HEIGHT * 0.5 + offset.y)
            right_text_pos = Point(Constants.SCREEN_WIDTH + offset.x, 0 + offset.y)

            self.update_arduino_config()
            self.arduino.update_status(debug=debug)
            if debug:
                print(f"Arduino status updated!")

            tracks, poses, frame_updated = self.input.update_trackers(self.frame)
            if Constants.draw_openpose and frame_updated is not None:
                self.frame = frame_updated

            self.update_tracks(tracks, poses, self.logger, debug=debug)

            self.update_cameras_config()
            self.update_cameras_data(debug=debug)

            self.update_behaviors_config()

            self.draw_cameras_debug(draw_graph_data=False)

            # pygame.image.save(self.scene.screen, image_data, "JPEG")

            self.sio.draw_debug(self.logger, left_text_pos)
            left_text_pos.y += self.logger.line_height
            self.arduino.draw_debug(self.logger, left_text_pos, debug=True)
            left_text_pos.y += self.logger.line_height
            self.update_action(left_text_pos=left_text_pos, right_text_pos=right_text_pos, debug=True)

            self.logger.flush_text_lines(debug=debug)

            if self.logger.draw_type == SwarmLogger.OPENCV:
                self.scene.update(self.cv2.cvtColor(self.frame, self.cv2.COLOR_BGR2RGB), debug=debug)
            self.scene.render()

            pygame.image.save(self.scene.screen, image_data, "JPEG")
            self.sio.send_data(image_data)

            if Constants.draw_map:
                if debug:
                    print(f"Updating map...")
                self.update_map()

            if debug:
                print(f"--- End loop ---")
            self.cv2.waitKey(1)

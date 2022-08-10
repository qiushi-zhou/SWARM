#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path

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


class SwarmAPP():
    def __init__(self, observable=None, arduino_port="COM3", ws_enabled=False, mockup_commands=True):
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
        self.ws_enabled = ws_enabled
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
        self.font = pygame.font.SysFont('Cascadia', Constants.font_size)
        screen = pygame.display.get_surface()
        self.scene = Scene(screen)
        # self.async_loop = asyncio.get_event_loop()
        self.screenshot_filename = 'tempOP.jpeg'
        if self.ws_enabled:
            self.sio = socketio.Client()
            self.setupSocketio()

    def setupSocketio(self):
        print(f"Connecting to WebSocket on: {Constants.ws_uri}")
        self.call_backs()
        # self.sio.start_background_task(self.sio.connect, Constants.ws_uri)
        self.sio.connect(Constants.ws_uri)

    def call_backs(self):
        @self.sio.event
        def connect():
            print("I'm connected!")

        @self.sio.event
        def connect_error(data):
            print("The connection failed!")

        @self.sio.event
        def disconnect():
            print("I'm disconnected!")
        
    def encode_image_data(self, img_filename):
        image_data = self.cv2.imread(img_filename)
        b64_data = base64.b64encode(image_data)
        b64_data = b64_data.decode()
        image_data = "data:image/jpeg;base64," + b64_data 
        return image_data
    
    def sendData(self, graphData=None):
        if self.sio.connected:
            img_data_str = self.encode_image_data(self.screenshot_filename)
            t = datetime.datetime.now()

            # self.sio.start_background_task(self.sio.emit, 'op_frame', {'frame_data': img_data_str, 'time':datetime.datetime().now().ctime()})
            self.sio.emit('op_frame', {'frame_data': img_data_str, 'time_ms': time.mktime(t.timetuple()), "datetime": t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]})
        else:
            print(f"WS NOT CONNECTED!")

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
                    self.cameras.append(Camera(Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT, cameras_data[i]))
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

    def update_tracks(self, tracks, keypoints, frame, drawer, draw_type='cv', debug=True):
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
                            if draw_type == 'cv':
                                drawer.line(frame, (int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), color, thickness)
                            else:
                                drawer.draw.line(frame, color=color, start_pos=(int(p1.x), int(p1.y)), end_pos=(int(p2.x), int(p2.y)), width=thickness)
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

    def update_action(self, debug=True):
        if debug:
            print(f"Updating Action!")
        arduino = self.arduino
        self.current_behavior = None
        self.frame_buffer.add_frame_data(self.cameras)
        avg_total_people = self.frame_buffer.people_data.avg
        avg_total_groups = self.frame_buffer.groups_data.avg
        avg_distance = self.frame_buffer.distance_data.avg
        avg_distance_from_machine = self.frame_buffer.machine_distance_data.avg

        for behavior in self.behaviors:
            # print(f"Checking Behaviour: {behavior}")
            enabled = behavior.get("enabled", True)
            name = behavior.get("name", "unknown")
            command = behavior.get("arduino_command", "")
            if not enabled:
                continue
            parameters = behavior.get("parameters", [])
            for param_name in parameters:
                print(f"Param name: {param_name}")
                parameter = parameters[param_name]
                param_name = param_name.lower()
                enabled = parameter.get("enabled", True)
                run_action = True
                if not enabled:
                    continue
                value = -1
                if param_name == "time":
                    last_time = behavior.get("last_executed_time", None)
                    if last_time is None:
                        run_action = True
                        break
                    timeout = parameter.get("timeout", 600)
                    elapsed = (datetime.datetime.now() - last_time).seconds
                    if elapsed >= timeout:
                        run_action = True
                        break
                elif param_name == "people": value = avg_total_people
                elif param_name == "groups": value = avg_total_groups
                elif param_name == "avg_distance_between_people": value = avg_distance
                elif param_name == "avg_distance_from_machine": value = avg_distance_from_machine
                
                min_value = parameter.get('min', 0)
                max_value = parameter.get('max', 0)
                criteria_met = min_value <= value <= max_value
                if not criteria_met:
                    run_action = False
                    break
                
            if run_action:
                self.current_behavior = behavior
                print(f"Action updated: {name} ({command})")
                # arduino.send_command(arduino.commands["stop"])
                arduino.send_command(command, testing_command=self.mockup_commands)
                behavior["last_executed_time"] = datetime.datetime.now()
                print(f"\r\nNew ACTION: Running command {command} from behavior {name}\n\r")
            return # We found the command to execute so we can stop here

    def draw_actions_debug(self, drawer, canvas, draw_type='cv', debug=True, text_x=0, text_y=0, offset_x=20,
                            offset_y=300):
        if debug:
            print(f"Drawing behavior debug")
        p_data = self.frame_buffer.people_data
        g_data = self.frame_buffer.groups_data
        d_data = self.frame_buffer.distance_data
        dm_data = self.frame_buffer.machine_distance_data
        text_x = int(text_x + offset_x)
        text_y = int(text_y + offset_y)
        curr_behavior_name = "None"
        if self.current_behavior is not None:
            curr_behavior_name = self.current_behavior["name"]
        for behavior in self.behaviors:
            b_enabled = behavior.get("enabled", True)
            name = behavior.get("name", "unknown")
            color = (255, 0, 200) if name == curr_behavior_name else (140, 0, 140)
            lines = []
            prefix = 'x'
            if b_enabled:
                prefix = '-'
            if name == curr_behavior_name:
                prefix = '>'
            lines.append(f"{prefix} {name}")
            parameters = behavior.get("parameters", [])
            for param_name in parameters:
                parameter = parameters[param_name]
                param_name = param_name.lower()
                p_enabled = parameter.get("enabled", True)
                if not p_enabled:
                    continue
                value = -999
                if param_name == "time":
                    last_time = behavior.get("last_executed_time", None)
                    elapsed = 0
                    timeout = parameter.get("timeout", 600)
                    if last_time is not None:
                        elapsed = (datetime.datetime.now() - last_time).seconds
                    if name == curr_behavior_name:
                        lines[0] += f"{param_name}: {elapsed}/{timeout}"
                    else:
                        lines.append(f"  {param_name}: {elapsed}/{timeout}")
                    continue
                elif param_name == "people":
                    value = p_data.avg
                elif param_name == "groups":
                    value = g_data.avg
                elif param_name == "people_in_groups_ratio":
                    value = 0
                    if p_data.avg > 0:
                        value = g_data.avg / p_data.avg
                elif param_name == "avg_distance_between_people":
                    value = d_data.avg
                elif param_name == "avg_distance_from_machine":
                    value = dm_data.avg

                min_value = parameter.get('min', 0)
                max_value = parameter.get('max', 0)
                if name == curr_behavior_name:
                    lines[0] += f"{param_name}: [{min_value}, {max_value}]"
                else:
                    lines.append(f"  {param_name}: {min_value} < {value:.2f} < {max_value}")
            text_y = utils.draw_debug_lines(lines, color, drawer, canvas, text_x, text_y, draw_type)
        return text_y

    def draw_behavior_debug(self, drawer, canvas, draw_type='cv', debug=True, text_x=0, text_y=0, offset_x=20,
                            offset_y=300):
        if debug:
            print(f"Drawing behavior debug")
        p_data = self.frame_buffer.people_data
        g_data = self.frame_buffer.groups_data
        d_data = self.frame_buffer.distance_data
        dm_data = self.frame_buffer.machine_distance_data
        text_x = int(text_x + offset_x)
        text_y = int(text_y + offset_y)
        behavior_dbg = "None"
        if self.current_behavior is not None:
            behavior_dbg = self.current_behavior["name"]
        lines = [f"Running Action {behavior_dbg}"]
        lines.append(f"People - avg: {p_data.avg:.2f}, minmax: [{p_data.min:.2f}, {p_data.max:.2f}], n: {p_data.non_zeroes}/{self.frame_buffer.size()}")
        lines.append(f"Groups - avg: {g_data.avg:.2f}, minmax: [{g_data.min:.2f}, {g_data.max:.2f}], n: {g_data.non_zeroes}/{self.frame_buffer.size()}")
        lines.append(f"P_Distance - avg: {d_data.avg:.2f}, minmax: [{d_data.min:.2f}, {d_data.max:.2f}], n: {d_data.non_zeroes}/{self.frame_buffer.size()}")
        lines.append(f"M_Distance - avg: {dm_data.avg:.2f}, minmax: [{dm_data.min:.2f}, {dm_data.max:.2f}], n: {dm_data.non_zeroes}/{self.frame_buffer.size()}")
        color = (255, 50, 0)
        b_color = (150, 150, 150) if behavior_dbg == "None" else (255, 255, 0)
        text_y = utils.draw_debug_lines(lines, color, drawer, canvas, text_x, text_y, draw_type)
        return text_y

    def draw_camera_debug(self, drawer, canvas, draw_type='cv', debug=True, offset_x=20, offset_y=-20):
        if debug:
            print(f"Drawing camera debug")
        for i in range(0, len(self.cameras)):
            camera = self.cameras[i]
            if camera.enabled:
                # text_x = int(camera.start_x + offset_x)
                # text_y = int(camera.end_y + offset_y)
                if len(camera.path_vertices) > 0:
                    for j in range(0, len(camera.path_vertices)-1):
                        p1 = camera.path_vertices[j]
                        p2 = camera.path_vertices[j+1]
                        thickness = 2
                        if draw_type.lower() == 'cv':
                            drawer.line(canvas, (int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), camera.color, thickness)
                        else:
                            drawer.draw.line(self.scene.screen, color=camera.color, start_pos=(int(p1.x), int(p1.y)), end_pos=(int(p2.x), int(p2.y)), width=thickness)

                # self.cv2.rectangle(frame, (int(camera.start_x), int(camera.start_y)), (int(camera.end_x), int(camera.end_y)), (255, 0, 0), 2)
                # self.cv2.putText(frame, f"Q{i + 1}: {camera.num_people}", (text_x, text_y), 0, 0.4, (0, 0, 255), 2)
        # if debug:
        #     print(f"Quadrant {i + 1} [{camera.q_row}, {camera.q_col}] - Count: {camera.num_people} x=[{camera.start_x}, {camera.end_x}] - y=[{camera.start_y}, {camera.end_y}]")

    def update_map(self):
        height = 500
        width = 500
        map_canvas = np.ones((height, width, 3), np.uint8)
        map_canvas *= 255
        self.cv2.circle(map_canvas, (int(height/2), int(width/2)), Constants.inner_radius, (0, 0, 0), 2)
        self.cv2.circle(map_canvas, (int(height/2), int(width/2)), Constants.outer_radius, (0, 0, 0), 2)
        self.cv2.imshow("SWARM map", map_canvas)

    def draw_graph(self, drawer, font_drawer, canvas, draw_type='cv', debug=True, offset_x=20, offset_y=200):
        if debug:
            print(f"Drawing graph debug")
        for i in range(0, len(self.cameras)):
            camera = self.cameras[i]
            if camera.enabled:
                camera.p_graph.draw_nodes(drawer, canvas, draw_type=draw_type)
                camera.p_graph.draw_edges(drawer, canvas, draw_type=draw_type, debug=debug)
                camera.p_graph.draw_dist_from_machine(drawer, canvas, camera.machine_position.x, camera.machine_position.y, draw_type=draw_type, debug=debug)
                camera.p_graph.draw_debug(font_drawer, canvas, camera.text_position.x, camera.text_position.y, 10, 10, draw_type=draw_type, debug=debug, prefix=i)

    def run(self, debug=False):
        while True:
            print(f"--- Start loop ---")
            e = datetime.datetime.now()
            print(f"\r\n{e.strftime('%Y-%m-%d %H:%M:%S')}", end="\r")
            draw_type = 'pygame'
            result, self.frame = self.capture0.read()
            if draw_type == 'cv':
                drawer = self.cv2
                font_drawer = self.cv2
                canvas = self.frame
            else:
                drawer = pygame
                font_drawer = self.font
                self.scene.update(self.cv2.cvtColor(self.frame, self.cv2.COLOR_BGR2RGB), debug=debug)
                canvas = self.scene.screen

            self.update_arduino_config()
            self.arduino.update_status(debug=debug)
            if debug:
                print(f"Arduino status updated!")
            offset_y = 0

            tracks, poses, frame_updated = self.input.update_trackers(self.frame)
            if Constants.draw_openpose and frame_updated is not None:
                self.frame = frame_updated

            self.update_tracks(tracks, poses, canvas, drawer=drawer, draw_type=draw_type, debug=debug)

            self.update_cameras_config()
            self.update_cameras_data(debug=debug)

            if Constants.draw_cameras_data:
                self.draw_camera_debug(drawer, canvas, draw_type=draw_type, debug=debug, offset_y=-15)

            if Constants.draw_graph:
                offset_y += 20
                self.draw_graph(drawer, font_drawer, canvas, draw_type=draw_type, offset_y=offset_y, debug=debug)

            self.update_behaviors_config()
            self.update_action(debug=True)
            if Constants.draw_behavior_data:
                text_x = Constants.SCREEN_WIDTH*0.5
                text_y = Constants.SCREEN_HEIGHT*0.5
                offset_x = 10
                offset_y = 10
                text_y = self.arduino.draw_arduino_debug(font_drawer, canvas, draw_type=draw_type, text_x=text_x, text_y=text_y, offset_x=offset_x, offset_y=offset_y, debug=debug)
                self.draw_behavior_debug(font_drawer, canvas, draw_type=draw_type, text_x=text_x, text_y=text_y+10, offset_x=offset_x, offset_y=offset_y, debug=debug)
                text_x = Constants.SCREEN_WIDTH
                text_y = Constants.SCREEN_HEIGHT*0
                self.draw_actions_debug(font_drawer, canvas, draw_type=draw_type, text_x=text_x, text_y=text_y, offset_x=offset_x, offset_y=offset_y, debug=debug)

            if draw_type.lower() == 'cv':
                self.scene.update(self.cv2.cvtColor(canvas, self.cv2.COLOR_BGR2RGB), debug=debug)
            self.scene.render(filename=self.screenshot_filename)

            if Constants.draw_map:
                if debug:
                    print(f"Updating map...")
                self.update_map()

            if self.ws_enabled:
                self.sendData()

            print(f"--- End loop ---")
            self.cv2.waitKey(1)

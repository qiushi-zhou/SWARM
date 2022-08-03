#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

        
class SwarmAPP():
    def update_config(self):
        self.behavior_config = {}
        try:
            with open(r'./Behaviour_Config.yaml') as file:
                self.behavior_config = yaml.load(file, Loader=yaml.FullLoader)
                self.buffer_size = self.behavior_config.get("buffer_size", 10)
                self.behaviors = self.behavior_config.get("behaviors", [])
        except:
            return
        
        self.cameras_config = {}
        try:
            with open(r'./CamerasConfig.yaml') as file:
                self.cameras_config = yaml.load(file, Loader=yaml.FullLoader)
                self.cameras_config = self.cameras_config.get("cameras", [])
        except:
            return
        
    def __init__(self, observable=None, arduino_port="COM4", time_between_commands=-1, max_feedback_wait=-1, max_execution_wait=-1, mockup_commands=True):
        if max_feedback_wait < 0:
            max_feedback_wait = 5 if mockup_commands else 5
        if max_execution_wait < 0:
            max_execution_wait = 10 if mockup_commands else 90
        if time_between_commands < 0:
            time_between_commands = 5 if mockup_commands else 5

        self.arduino = Arduino(port=arduino_port, time_between_commands=time_between_commands, max_feedback_wait=max_feedback_wait, max_execution_wait=max_execution_wait)
        if observable:
            observable.subscribe(self)
        self.mockup_commands = mockup_commands
        self.cv2 = cv2
        self.capture_index = 2
        self.capture0 = None
        self.behavior_config = {}
        self.cameras_config = {}
        self.buffer_size = 10
        self.behaviors = []
        self.update_config()
        self.frame_buffer = FrameBuffer(self.buffer_size)
        self.current_behavior = None
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
        pygame.display.set_mode((Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT))
        pygame.display.set_caption("SWARM")
        screen = pygame.display.get_surface()
        self.scene = Scene(screen)
        self.cameras = []
        self.init_cameras()

    def notify(self, observable, *args, **kwargs):
        print('Got', args, kwargs, 'From', observable)

    def init_cameras(self):
        for i in range(0, len(self.cameras_config)):
            camera_config = self.cameras_config[i]
            self.cameras.append(Camera(Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT, camera_config))

    def update_tracks(self, tracks, frame, debug=True):
        if debug:
            print(f"Updating tracks")
        for camera in self.cameras:
            camera.people_graph.init_graph()

        for track in tracks:
            color = (255, 255, 255)
            if not track.is_confirmed():
                color = (0, 0, 255)
            bbox = track.to_tlbr()
            min_p = Point(min(int(bbox[0]), int(bbox[2])), min(int(bbox[1]), int(bbox[3])))
            chest_offset = Point(0, 0)
            center_x, center_y = (min_p.x + ((bbox[2]-bbox[0])/2) + chest_offset.x, min_p.y + ((bbox[3]-bbox[1])/2) + chest_offset.y) # ((x1+x2)/2, (y1+y2)/2).
            center_p = Point(center_x, center_y)
            if Constants.draw_openpose:
                self.cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), color, 2)
                self.cv2.putText(frame, "id%s - ts%s" % (track.track_id, track.time_since_update), (int(bbox[0]), int(bbox[1]) - 20), 0, 0.4, (0, 255, 0), 2)
            for camera in self.cameras:
                camera.check_track(min_p, center_p)
            if debug:
                print(f"Center: ({center_x:.2f}, {center_y:.2f})")
    
    def update_cameras_data(self, debug=True):
        if debug:
            print(f"Updating Cameras data")
        for camera in self.cameras:
            camera.update_camera_data()        

    def update_action(self, debug=True):
        if debug:
            print(f"Updating Action!")
        arduino = self.arduino
        # self.update_config()
        self.current_behavior = None
        self.frame_buffer.add_frame_data(self.cameras)
        avg_total_people = self.frame_buffer.people_data.avg
        avg_total_groups = self.frame_buffer.distance_data.avg
        avg_distance = self.frame_buffer.distance_data.avg
        avg_distance_from_machine = self.frame_buffer.machine_distance_data.avg
        
        for behavior in self.behaviors:
            # print(f"Checking Behaviour: {behavior}")
            enabled = behavior.get("enabled", True)
            if not enabled:
                continue
            name = behavior.get("name", "unknown")
            command = behavior.get("arduino_command", "")
            min_people = behavior.get("min_people", 0)
            max_people = behavior.get("max_people", 10000)
            min_avg_distance = behavior.get("min_avg_distance", 0)
            max_avg_distance = behavior.get("max_avg_distance", 10000)
            min_avg_distance_from_machine = behavior.get("min_avg_distance_from_machine", 0)
            max_avg_distance_from_machine = behavior.get("max_avg_distance_from_machine", 10000)
            print(f"\r\ncommand {command} from behavior {name}\r\t"
                  f"\ravg_distance: {avg_distance}\t[{min_avg_distance}, {max_avg_distance}]\n\r"
                  f"\ravg_distance_from_machine: {self.avg_distance_from_machine}\t[{min_avg_distance_from_machine}, {max_avg_distance_from_machine}]\n\r"
                  f"\ravg_people: {avg_total_people}\t[{min_people}, {max_people}]\n", end="\r")
            if(min_people <= avg_total_people <= max_people and
                min_avg_distance <= avg_distance <= max_avg_distance and
                min_avg_distance_from_machine <= avg_distance_from_machine <= max_avg_distance_from_machine):
                self.current_behavior = behavior
                print(f"Action updated: {name} ({command})")
                # arduino.send_command(arduino.commands["stop"])
                arduino.send_command(command, testing_command=self.mockup_commands)
                print(f"\r\nNew ACTION: Running command {command} from behavior {name}\n\r")
                break

    def draw_behavior_debug(self, frame, debug=True, offset_x=20, offset_y=300):
        if debug:
            print(f"Drawing behavior debug")
        avg_total_people = self.frame_buffer.total_avg_people
        avg_distance = self.frame_buffer.avg_distance
        avg_distance_from_machine = self.frame_buffer.avg_distance_from_machine
        text_x = int(0 + offset_x)
        text_y = int(0 + offset_y)
        behavior_dbg = "None"
        if self.current_behavior is not None:
            behavior_dbg = self.current_behavior["name"]
        self.cv2.putText(frame, f"Running {behavior_dbg}, Buffer size: {self.frame_buffer.size()}", (text_x, text_y), 0, 0.4, (255, 0, 0), 2)
        text_y += 20
        self.cv2.putText(frame, f"Avg People: {avg_total_people:.2f}, Avg Dist: {avg_distance:.2f}, Avg Dist_m: {avg_distance_from_machine:.2f}", (text_x, text_y), 0, 0.4, (255, 0, 0), 2)

    def draw_arduino_debug(self, frame, debug=True, offset_x=20, offset_y=300):
        if debug:
            print(f"Drawing arduino debug")
        text_x = int(0 + offset_x)
        text_y = int(0 + offset_y)
        arduino_cmd_dbg = f"Last Command: {self.arduino.last_command}"
        if self.arduino.last_command is not None:
            arduino_cmd_dbg += f" sent at {self.arduino.last_sent_command_time.strftime('%Y-%m-%d %H:%M:%S')}"
        arduino_status_dbg = f"Arduino Status: "
        if self.arduino.status.id == self.arduino.statuses['cooling_down'].id:
            arduino_status_dbg += f"{self.arduino.status.name}. "
            elapsed = (datetime.datetime.now() - self.arduino.last_completed_command_time).seconds
            arduino_status_dbg += f" Cooldown: {self.arduino.time_between_commands - elapsed} s"
        elif self.arduino.status.id == self.arduino.statuses['command_received'].id:
            arduino_status_dbg += f"{self.arduino.status.name} {self.arduino.last_command}. "
            elapsed = (datetime.datetime.now() - self.arduino.last_sent_command_time).seconds
            arduino_status_dbg += f"Awaiting completion: {self.arduino.max_execution_wait-elapsed}s"
            # arduino_status_dbg += f" (max wait: {self.arduino.max_execution_wait}s)"
        elif self.arduino.status.id == self.arduino.statuses['command_sent'].id:
            arduino_status_dbg += f"{self.arduino.status.name} {self.arduino.last_command}. "
            elapsed = (datetime.datetime.now() - self.arduino.last_sent_command_time).seconds
            arduino_status_dbg += f"Awaiting ACK: {self.arduino.max_feedback_wait-elapsed}s"
            # arduino_status_dbg += f"(max wait: {self.arduino.max_feedback_wait}s)"
        # self.cv2.putText(frame, self.arduino.debug_string(), (text_x, text_y), 0, 0.4, (0, 0, 255), 2)
        else:
            arduino_status_dbg += f"{self.arduino.status.name}. "
        self.cv2.putText(frame, arduino_cmd_dbg, (text_x, text_y), 0, 0.4, (0, 0, 255), 2)
        text_y += 20
        self.cv2.putText(frame, arduino_status_dbg, (text_x, text_y), 0, 0.4, (0, 0, 255), 2)

    def draw_camera_debug(self, frame, debug=True, offset_x=20, offset_y=-20):
        if debug:
            print(f"Drawing camera debug")
        for i in range(0, len(self.cameras)):
            camera = self.cameras[i]
            text_x = int(camera.start_x + offset_x)
            text_y = int(camera.end_y + offset_y)
            self.cv2.rectangle(frame, (int(camera.start_x), int(camera.start_y)), (int(camera.end_x), int(camera.end_y)), (255, 0, 0), 2)
            self.cv2.putText(frame, f"Q{i + 1}: {camera.num_people}", (text_x, text_y), 0, 0.4, (0, 0, 255), 2)
        if debug:
            print(f"Quadrant {i + 1} [{camera.q_row}, {camera.q_col}] - Count: {camera.num_people} x=[{camera.start_x}, {camera.end_x}] - y=[{camera.start_y}, {camera.end_y}]")

    def update_map(self):
        height = 500
        width = 500
        map_canvas = np.ones((height, width, 3), np.uint8)
        map_canvas *= 255
        self.cv2.circle(map_canvas, (int(height/2), int(width/2)), Constants.inner_radius, (0, 0, 0), 2)
        self.cv2.circle(map_canvas, (int(height/2), int(width/2)), Constants.outer_radius, (0, 0, 0), 2)
        self.cv2.imshow("SWARM map", map_canvas)

    def draw_graph(self, canvas, debug=True, offset_x=20, offset_y=200):
        if debug:
            print(f"Drawing graph debug")
        for i in range(0, len(self.cameras)):
            camera = self.cameras[i]
            camera.people_graph.cv_draw_nodes(self.cv2, canvas)
            camera.people_graph.cv_draw_edges(self.cv2, canvas, debug=debug)
            camera.people_graph.cv_draw_debug(self.cv2, canvas, camera.start_x, camera.start_y, offset_x, offset_y, debug=debug, prefix=i)
            camera.people_graph.cv_draw_dist_from_machine(self.cv2, canvas, camera.machine_x, camera.machine_y, debug=debug)

    def run(self, debug=False):
        while True:
            print(f"--- Start loop ---")
            e = datetime.datetime.now()
            print(f"\r\n{e.strftime('%Y-%m-%d %H:%M:%S')}", end="\r")
            result, frame = self.capture0.read()
            self.arduino.update_status(debug=debug)
            if debug:
                print(f"Arduino status updated!")
            offset_y = 0

            tracks, frame_updated = self.input.update_trackers(frame)
            if Constants.draw_openpose and frame_updated is not None:
                frame = frame_updated

            self.update_tracks(tracks, frame, debug=debug)
            self.update_cameras_data(debug=debug)
            if Constants.draw_cameras_data:
                self.draw_camera_debug(frame, debug=debug, offset_y=-15)
            if Constants.draw_graph:
                offset_y += 20
                self.draw_graph(frame, offset_y=offset_y, debug=debug)

            self.update_action(debug=True)
            if Constants.draw_behavior_data:
                offset_y = 150
                self.draw_behavior_debug(frame,offset_y=offset_y, debug=debug)
                offset_y += 40
                self.draw_arduino_debug(frame, offset_y=offset_y, debug=debug)

            self.scene.update(self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB), debug=debug)
            # self.scene.update(frame, debug=debug)

            if Constants.draw_map:
                if debug:
                    print(f"Updating map...")
                self.update_map()

            print(f"--- End loop ---")
            self.cv2.waitKey(1)

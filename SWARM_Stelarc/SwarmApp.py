#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path

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
        self.frame = None

        self.cameras_config = None
        self.behavior_config = None
        self.behaviors = []
        self.cameras = []
        self.update_cameras_config()
        self.update_behaviors_config()
        self.frame_buffer = FrameBuffer(self.behavior_config.get('buffer_size', 10))
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
        # if you want to use this module.
        self.font = pygame.font.SysFont('Cascadia', Constants.font_size)
        screen = pygame.display.get_surface()
        self.scene = Scene(screen)

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
            except:
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
            for i in range(0, len(cameras_data)):
                if len(self.cameras) <= i:
                    self.cameras.append(Camera(Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT, cameras_data[i]))
                else:
                    self.cameras[i].update_config(Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT, cameras_data[i])
            self.cameras_config['last_modified_time'] = os.path.getmtime(file_path)

    def update_tracks(self, tracks, frame, debug=True):
        if debug:
            print(f"Updating tracks")
        for camera in self.cameras:
            camera.p_graph.init_graph()

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
            if camera.enabled:
                camera.update_graph()

    def update_action(self, debug=True):
        if debug:
            print(f"Updating Action!")
        arduino = self.arduino
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
                  f"\ravg_distance_from_machine: {avg_distance_from_machine}\t[{min_avg_distance_from_machine}, {max_avg_distance_from_machine}]\n\r"
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

    def draw_behavior_debug(self, drawer, canvas, draw_type='cv', debug=True, text_x=0, text_y=0, offset_x=20, offset_y=300):
        if debug:
            print(f"Drawing behavior debug")
        avg_total_people = self.frame_buffer.people_data.avg
        avg_distance = self.frame_buffer.distance_data.avg
        avg_distance_from_machine = self.frame_buffer.machine_distance_data.avg
        text_x = int(text_x + offset_x)
        text_y = int(text_y + offset_y)
        behavior_dbg = "None"
        curr_behavior_name = "None"
        if self.current_behavior is not None:
            behavior_dbg = self.current_behavior["name"]
            curr_behavior_name =  self.current_behavior["name"]
        behavior_dbg1 = f"Running {behavior_dbg}, Buffer size: {self.frame_buffer.size()}"
        behavior_dbg2 = f"Avg People: {avg_total_people:.2f}, Avg Dist: {avg_distance:.2f}, Avg Dist_m: {avg_distance_from_machine:.2f}"
        color = (255, 0, 0)
        if draw_type.lower() == 'cv':
            drawer.putText(canvas, behavior_dbg1, (text_x, text_y), 0, 0.4, color, 2)
            drawer.putText(canvas, behavior_dbg2, (text_x, text_y+20), 0, 0.4, color, 2)
        else:
            canvas.blit(drawer.render(behavior_dbg1, True, color), (text_x, text_y))
            canvas.blit(drawer.render(behavior_dbg2, True, color), (text_x, text_y+20))
        text_y += 20
        for behavior in self.behaviors:
            text_y += 20
            enabled = behavior.get("enabled", True)
            name = behavior.get("name", "unknown")
            min_people = behavior.get("min_people", 0)
            max_people = behavior.get("max_people", 10000)
            min_avg_distance = behavior.get("min_avg_distance", 0)
            max_avg_distance = behavior.get("max_avg_distance", 10000)
            min_avg_distance_from_machine = behavior.get("min_avg_distance_from_machine", 0)
            max_avg_distance_from_machine = behavior.get("max_avg_distance_from_machine", 10000)
            behavior_dbg = f"{name} ({'enabled' if enabled else 'disabled'} - People: [{min_people}, {max_people}, People dist: [{min_avg_distance}, {max_avg_distance}] Machine dist: [{min_avg_distance_from_machine}, {max_avg_distance_from_machine}]"
            color = (255, 0, 0) if name == curr_behavior_name else (255, 0, 255)
            if draw_type.lower() == 'cv':
                drawer.putText(canvas, behavior_dbg, (text_x, text_y), 0, 0.4, color, 2)
            else:
                canvas.blit(drawer.render(behavior_dbg, True, color), (text_x, text_y))
        return text_y

    def draw_arduino_debug(self, drawer, canvas, draw_type='cv', debug=True, text_x=0, text_y=0, offset_x=20, offset_y=300):
        if debug:
            print(f"Drawing arduino debug")
        text_x = int(text_x + offset_x)
        text_y = int(text_y + offset_y)
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
        color = (0, 0, 255)
        if draw_type.lower() == 'cv':
            drawer.putText(canvas, arduino_cmd_dbg, (text_x, text_y), 0, 0.4, color, 2)
            drawer.putText(canvas, arduino_status_dbg, (text_x, text_y+20), 0, 0.4, color, 2)
        else:
            canvas.blit(drawer.render(arduino_cmd_dbg, True, color), (text_x, text_y))
            canvas.blit(drawer.render(arduino_status_dbg, True, color), (text_x, text_y+20))

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

            self.arduino.update_status(debug=debug)
            if debug:
                print(f"Arduino status updated!")
            offset_y = 0

            tracks, frame_updated = self.input.update_trackers(self.frame)
            if Constants.draw_openpose and frame_updated is not None:
                self.frame = frame_updated

            self.update_tracks(tracks, self.frame, debug=debug)

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
                text_y = self.draw_behavior_debug(font_drawer, canvas, draw_type=draw_type, text_x=text_x, text_y=text_y, offset_x=offset_x, offset_y=offset_y, debug=debug)
                text_y += 40
                self.draw_arduino_debug(font_drawer, canvas, draw_type=draw_type, text_x=text_x, text_y=text_y, offset_x=offset_x, offset_y=offset_y, debug=debug)

            if draw_type.lower() == 'cv':
                self.scene.update(self.cv2.cvtColor(canvas, self.cv2.COLOR_BGR2RGB), debug=debug)
            self.scene.render()

            if Constants.draw_map:
                if debug:
                    print(f"Updating map...")
                self.update_map()

            print(f"--- End loop ---")
            self.cv2.waitKey(1)

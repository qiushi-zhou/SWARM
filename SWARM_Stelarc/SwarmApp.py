#!/usr/bin/env python
# -*- coding: utf-8 -*-
from Input import Input
from Scene import Scene
import cv2
import numpy as np
import Constants
import pygame
from Arduino import Arduino
from people_graph import *
import time
from sys import platform

class Camera:
    def __init__(self, start_x, start_y, end_x, end_y, q_row, q_col):
        self.count = 0
        self.avg_distance = 0
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.q_row = q_row
        self.q_col = q_col
        self.people_graph = PeopleGraph()

    def is_in_camera(self, x, y):
        return self.start_x <= x <= self.end_x and self.start_y <= y <= self.end_y

class SwarmAPP():
    def __init__(self, n_cameras=4, observable=None, arduino_port="COM4"):
        if observable:
            observable.subscribe(self)
        self.cv2 = cv2
        self.capture_index = 3
        self.capture0 = None
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

        self.capture0.set(self.cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.capture0.set(self.cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.frameSize = (int(self.capture0.get(self.cv2.CAP_PROP_FRAME_WIDTH)),
                          int(self.capture0.get(self.cv2.CAP_PROP_FRAME_HEIGHT)))
        Constants.SCREEN_WIDTH = self.frameSize[0]
        Constants.SCREEN_HEIGHT = self.frameSize[1]

        self.input = Input(self, cv2)
        pygame.init()
        pygame.display.set_mode((Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT))
        pygame.display.set_caption("SWARM")
        screen = pygame.display.get_surface()
        self.scene = Scene(screen)

        self.arduino = Arduino(port=arduino_port, wait=False)
        self.n_cameras = n_cameras
        self.cameras = []
        self.total_people = 0
        self.avg_distance = 0
        self.init_cameras()

    def notify(self, observable, *args, **kwargs):
        print('Got', args, kwargs, 'From', observable)

    def init_cameras(self):
        for i in range(0, self.n_cameras):
            if len(self.cameras) < i + 1:
                q_col = 0 if (i % 2) == 0 else 1
                q_row = 0 if i < 2 else 1
                start_x = 0 if q_col <= 0 else Constants.SCREEN_WIDTH / 2
                end_x = Constants.SCREEN_WIDTH / 2 if q_col <= 0 else Constants.SCREEN_WIDTH
                start_y = 0 if q_row <= 0 else Constants.SCREEN_HEIGHT / 2
                end_y = Constants.SCREEN_HEIGHT / 2 if q_row <= 0 else Constants.SCREEN_HEIGHT
                self.cameras.append(Camera(start_x, start_y, end_x, end_y, q_row, q_col))

    def update_tracks(self, tracks, frame, debug=True):
        for camera in self.cameras:
            camera.people_graph.init_graph()
            camera.count = 0

        for track in tracks:
            color = (255, 255, 255)
            if not track.is_confirmed():
                color = (0, 0, 255)
            bbox = track.to_tlbr()
            min_x = min(int(bbox[0]), int(bbox[2]))
            min_y = min(int(bbox[1]), int(bbox[3]))
            chest_offset_x = 0
            chest_offset_y = 0
            center_x, center_y = (min_x + ((bbox[2]-bbox[0])/2) + chest_offset_x, min_y + ((bbox[3]-bbox[1])/2) + chest_offset_y) # ((x1+x2)/2, (y1+y2)/2).
            dist_from_camera = -1
            if Constants.draw_openpose:
                self.cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), color, 2)
                self.cv2.putText(frame, "id%s - ts%s" % (track.track_id, track.time_since_update), (int(bbox[0]), int(bbox[1]) - 20), 0, 0.5, (0, 255, 0), 1)
            for camera in self.cameras:
                if camera.is_in_camera(min_x, min_y):
                    camera.count += 1
                    camera.people_graph.add_node(center_x, center_y, dist_from_camera)
            if debug:
                print(f"Center: ({center_x:.2f}, {center_y:.2f})")

    def update_action(self, debug=True):
        arduino = self.arduino
        if self.total_people == 0:
            command = commands[0]
        if self.total_people == 1:
            command =  commands[1]
        if self.total_people == 2:
            command =  commands[2]
        if self.total_people == 3:
            command =  commands[3]
        if self.total_people == 4:
            command =  commands[4]
        res = arduino.send_command(commands["stop"])
        res = arduino.send_command(command)

    def draw_behavior_debug(self, frame, debug=True, offset_x=20, offset_y=300):
        text_x = int(0 + offset_x)
        text_y = int(0 + offset_y)
        self.cv2.putText(frame, self.arduino.debug_string(), (text_x, text_y), 0, 0.4, (255, 255, 0), 1)
        self.cv2.putText(frame, self.arduino.status, (text_x, text_y+20), 0, 0.6, (0, 0, 255), 2)

    def draw_camera_debug(self, frame, debug=True, offset_x=20, offset_y=-20):
        for i in range(0, len(self.cameras)):
            camera = self.cameras[i]
            text_x = int(camera.start_x + offset_x)
            text_y = int(camera.end_y + offset_y)
            self.cv2.rectangle(frame, (int(camera.start_x), int(camera.start_y)), (int(camera.end_x), int(camera.end_y)), (255, 0, 0), 1)
            self.cv2.putText(frame, f"Q{i + 1}: {camera.count}", (text_x, text_y), 0, 0.6, (0, 0, 255), 2)
        if debug:
            print(f"Quadrant {i + 1} [{camera.q_row}, {camera.q_col}] - Count: {camera.count} x=[{camera.start_x}, {camera.end_x}] - y=[{camera.start_y}, {camera.end_y}]")

    def update_map(self):
        height = 500
        width = 500
        map_canvas = np.ones((height, width, 3), np.uint8)
        map_canvas *= 255
        self.cv2.circle(map_canvas, (int(height/2), int(width/2)), Constants.inner_radius, (0, 0, 0), 2)
        self.cv2.circle(map_canvas, (int(height/2), int(width/2)), Constants.outer_radius, (0, 0, 0), 2)
        self.cv2.imshow("SWARM map", map_canvas)

    def draw_graph(self, canvas, debug=True, offset_x=20, offset_y=200):
        for i in range(0, len(self.cameras)):
            camera = self.cameras[i]
            camera.people_graph.calculate_edges()
            camera.people_graph.cv_draw_nodes(self.cv2, canvas)
            camera.people_graph.cv_draw_edges(self.cv2, canvas, debug=debug)
            camera.people_graph.cv_draw_debug(self.cv2, canvas, camera.start_x, camera.start_y, offset_x, offset_y, debug=debug, prefix=i)

    def run(self):
        while True:
            result, frame = self.capture0.read()
            self.arduino.update_status()
            offset_y = 50

            tracks, frame_updated = self.input.update_trackers(frame)
            if Constants.draw_openpose and frame_updated is not None:
                frame = frame_updated

            self.update_tracks(tracks, frame, debug=False)
            if Constants.draw_cameras_data:
                self.draw_camera_debug(frame, debug=False, offset_y=-15)
            if Constants.draw_graph:
                offset_y += 20
                self.draw_graph(frame, offset_y=offset_y, debug=False)

            self.update_action(debug=False)
            if Constants.draw_behavior_data:
                offset_y += 20
                self.draw_behavior_debug(frame, offset_y=offset_y)

            self.scene.update(self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB))
            # self.scene.update(frame)

            if Constants.draw_map:
                self.update_map()
            self.cv2.waitKey(1)

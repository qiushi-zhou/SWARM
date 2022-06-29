#!/usr/bin/env python
# -*- coding: utf-8 -*-
from Input import Input
from Scene import Scene
from cv2 import cv2
import numpy as np
import Constants
import pygame
from Arduino import Arduino

class Camera:
    def __init__(self, start_x, start_y, end_x, end_y, q_row, q_col):
        self.count = 0
        self.start_x = start_x
        self.end_x = end_x
        self.start_y = start_y
        self.end_y = end_y
        self.q_row = q_row
        self.q_col = q_col

    def is_in_camera(self, x, y):
        return self.start_x <= x <= self.end_x and self.start_y <= y <= self.end_y

class Person:
    def __init__(self, id=-1, x=0, y=0, z=0):
        self.id = id
        self.x = x
        self.y = y
        self.z = z

    def update_location(self, tracks):
        pass

    def draw_debug_data(self, cv2, frame):
        pass




class SwarmAPP():
    def __init__(self, observable, n_cameras=4):
        observable.subscribe(self)
        self.cv2 = cv2
        self.capture0 = self.cv2.VideoCapture(3, self.cv2.CAP_DSHOW)
        if self.capture0.isOpened():  # Checks the stream
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

        self.arduino = Arduino(port="COM4", wait=False)
        self.n_cameras = 4
        self.cameras = []
        self.people = []
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
                self.cameras.append(Camera(start_x, end_x, start_y, end_y, q_row, q_col))

    def update_cameras(self, tracks, frame):
        for i in range(0, len(self.cameras)):
            camera = self.cameras[i]
            text_x = int(camera.start_x)
            text_y = int(camera.end_y)
            offset = 20
            for track in tracks:
                color = (255, 255, 255)
                if not track.is_confirmed():
                    color = (0, 0, 255)
                bbox = track.to_tlbr()
                min_y = min(int(bbox[1]), int(bbox[3]))
                min_x = min(int(bbox[0]), int(bbox[2]))

                if camera.is_in_camera(min_x, min_y):
                    camera.count += 1

                self.cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), color, 2)
                self.cv2.putText(frame, "id%s - ts%s" % (track.track_id, track.time_since_update),(int(bbox[0]), int(bbox[1]) - 20), 0, 0.5, (0, 255, 0), 1)

            print(f"Quadrant {i + 1} [{camera.q_row}, {camera.q_col}] - Count: {camera.count} x=[{camera.start_x}, {camera.end_x}] - y=[{camera.start_y}, {camera.end_y}]")
            self.cv2.rectangle(frame, (int(camera.start_x), int(camera.start_y)),(int(camera.end_x), int(camera.end_y)), (255, 0, 0), 1)
            self.cv2.putText(frame, f"Q{i + 1}: {camera.count}", (text_x + offset, text_y - offset), 0, 0.6, (0, 0, 255), 2)

    def update_behavior(self, frame):
        for i in range(0, len(self.cameras)):
            camera = self.cameras[i]
            text_x = int(camera.start_x)
            offset = 20
            command = ""
            arduino = self.arduino
            if camera.count == 0:
                arduino.send_command("stop")
                command = "pulse_1"
            if camera.count == 1:
                arduino.send_command("stop")
                command = "quiver_1"
            if camera.count == 2:
                arduino.send_command("stop")
                command = "undulate_1"
            if camera.count == 3:
                arduino.send_command("stop")
                command = "glitch_1"
            res = arduino.send_command(command)

            log_str = "Arduino UNKNOWN ERROR"
            if res <= 0:
                log_str = f"{command} sent"
            elif res == 1:
                log_str = "Arduino NOT CONNECTED"
            elif res == 2:
                log_str = "Command ALREADY SENT"
            elif res == 3:
                log_str = "Arduino is BUSY"

            self.cv2.putText(frame, log_str, (int(text_x) + offset, int(camera.start_y) + offset), 0,0.6, (0, 0, 255), 2)

    def update_map(self):
        height = 500
        width = 500
        map_canvas = np.ones((height, width, 3), np.uint8)
        map_canvas *= 255
        self.cv2.circle(map_canvas, (height/2, width/2), Constants.inner_radius, (0, 0, 0), 2)
        self.cv2.circle(map_canvas, (height/2, width/2), Constants.outer_radius, (0, 0, 0), 2)
        self.cv2.imshow("SWARM map", map_canvas)

    def run(self, csvWriter, arduino):
        while True:
            result, frame = self.capture0.read()
            self.arduino.update_status()
            self.cv2.putText(frame, arduino.debug_string(), (20, 70), 0, 0.4, (255, 255, 0), 1)

            tracks = self.input.update_trackers(frame)
            self.update_cameras(tracks)
            self.update_behavior(frame)

            self.scene.update(frame)

            self.update_map()

            self.cv2.waitKey(1)

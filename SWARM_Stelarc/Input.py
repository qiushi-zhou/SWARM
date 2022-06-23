# -*- coding: utf-8 -*-
import math

import cv2
import sys
import time
import numpy as np
import sys
import cv2
import os
from sys import platform
import argparse
import serial
import json
import time
import csv
import pygame
from datetime import datetime
from scipy.interpolate import interp1d
import imagiz
from flask import Flask, render_template, Response

app = Flask(__name__)

# Load OpenPose:
dir_path = os.path.dirname(os.path.realpath(__file__))
try:
        # Windows Import
    if platform == "win32":
            # Change these variables to point to the correct folder (Release/x64 etc.)
        sys.path.append(dir_path + '/../build/python/openpose/Release');
        os.environ['PATH']  = os.environ['PATH'] + ';' + dir_path + '/../build/x64/Release;' +  dir_path + '/../build/bin;'
        import pyopenpose as op
    else:
            # Change these variables to point to the correct folder (Release/x64 etc.)
        sys.path.append('../build/python');
            # If you run `make install` (default path is `/usr/local/python` for Ubuntu), you can also access the OpenPose/python module from there. This will install OpenPose and the python library at your desired installation path. Ensure that this is in your python path in order to use it.
            # sys.path.append('/usr/local/python')
        from openpose import pyopenpose as op
except ImportError as e:
    print('Error: OpenPose library could not be found. Did you enable `BUILD_PYTHON` in CMake and have this Python script in the right folder?')
    raise e

from deep_sort.iou_matching import iou_cost
from deep_sort.kalman_filter import KalmanFilter
from deep_sort.detection import Detection
from deep_sort.tracker import Tracker as DeepTracker
from deep_sort import nn_matching
from deep_sort import preprocessing
from deep_sort.linear_assignment import min_cost_matching
from deep_sort.detection import Detection as ddet
from tools import generate_detections as gdet
from utils import poses2boxes

import Constants

class Input():
    def __init__(self, debug = False):
        #from openpose import *
        params = dict()
        params["model_folder"] = Constants.openpose_modelfolder
        params["net_resolution"] = "-1x320"
        self.openpose = op.WrapperPython()
        self.openpose.configure(params)
        self.openpose.start()

        max_cosine_distance = Constants.max_cosine_distance
        nn_budget = Constants.nn_budget
        self.nms_max_overlap = Constants.nms_max_overlap
        max_age = Constants.max_age
        n_init = Constants.n_init

        model_filename = 'model_data/mars-small128.pb'
        self.encoder = gdet.create_box_encoder(model_filename,batch_size=1)
        metric = nn_matching.NearestNeighborDistanceMetric("cosine", max_cosine_distance, nn_budget)
        self.tracker = DeepTracker(metric, max_age = max_age,n_init= n_init)

        self.capture0 = cv2.VideoCapture(3, cv2.CAP_DSHOW)

        if self.capture0.isOpened():         # Checks the stream
            self.capture0.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.capture0.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            self.frameSize = (int(self.capture0.get(cv2.CAP_PROP_FRAME_WIDTH)),
                               int(self.capture0.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        Constants.SCREEN_WIDTH = self.frameSize[0]
        Constants.SCREEN_HEIGHT = self.frameSize[1]

        self.start_time = time.time()

        # For calculating angels:

        self.BODY_PARTS = {"Nose": 0, "Neck": 1, "RShoulder": 2, "RElbow": 3, "RWrist": 4,
                           "LShoulder": 5, "LElbow": 6, "LWrist": 7, "MHip": 8,"RHip": 9, "RKnee": 10,
                           "RAnkle": 11, "LHip": 12, "LKnee": 13, "LAnkle": 14, "REye": 15,
                           "LEye": 16, "REar": 17, "LEar": 18}

        self.POSE_PAIRS = [["Neck", "RShoulder"], ["Neck", "LShoulder"], ["RShoulder", "RElbow"],
                           ["RElbow", "RWrist"], ["LShoulder", "LElbow"], ["LElbow", "LWrist"],
                           ["MHip", "RHip"], ["RHip", "RKnee"], ["RKnee", "RAnkle"], ["MHip", "LHip"],
                           ["LHip", "LKnee"], ["LKnee", "LAnkle"], ["Neck", "Nose"], ["Nose", "REye"],
                           ["REye", "REar"], ["Nose", "LEye"], ["LEye", "LEar"]]

        self.POINTS = []

        # key angles: RightArm is the angle between Rshoulder, RElbow,RWrist
        # note for some calcs we can reuse the same connects!
        '''
        self.KEY_DISTANCES = {"RArm": {"RShoulder-RElbow": None, "RElbow-RWrist": None, "Neck-RShoulder": None},
                              "LArm": {"LShoulder-LElbow": None, "LElbow-LWrist": None, "Neck-LShoulder": None},
                              "RLeg": {"MHip-RHip": None, "RHip-RKnee": None, "RKnee-RAnkle": None},
                              "LLeg": {"MHip-LHip": None, "LHip-RKnee": None, "LKnee-RAnkle": None}}

        self.KEY_ANGLES = {"RShoulder": collections.deque(self.queue_size * [0], self.queue_size), "LShoulder": collections.deque(self.queue_size * [0], self.queue_size),
                           "RArm": collections.deque(self.queue_size * [0], self.queue_size), "LArm": collections.deque(self.queue_size * [0], self.queue_size),
                           "RHip": collections.deque(self.queue_size * [0], self.queue_size), "LHip": collections.deque(self.queue_size * [0], self.queue_size),
                           "RLeg": collections.deque(self.queue_size * [0], self.queue_size), "LLeg": collections.deque(self.queue_size * [0], self.queue_size)}
        '''
    def getCurrentFrameAsImage(self):
        frame = self.currentFrame
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pgImg = pygame.image.frombuffer(frame.tostring(), frame.shape[1::-1], "RGB")
        return pgImg

    def printCSV(self, track, csvWriter):
        s = str(time.time() - self.start_time)+','+str(track.track_id)
        for i in track.last_seen_detection.pose:
            for j in i:
                s += (',' + str(j))
        csvWriter.writerow([s])
        s = ""

    def printCSVforVideo(self, track, csvWriter):
        s = str(self.capture0.get(cv2.CAP_PROP_POS_MSEC)) + ',' + str(track.track_id)
        for i in track.last_seen_detection.pose:
            for j in i:
                s += (',' + str(j))
        csvWriter.writerow([s])
        s = ""

    def debugKeypoints(datums):
        datum = datums[0]
        # print(datum.poseKeypoints[0][0][0])
        if abs(datum.poseKeypoints[0][4][0] - datum.poseKeypoints[0][7][0]) < abs(
                datum.poseKeypoints[0][6][0] - datum.poseKeypoints[0][3][0]):
            print("wide")
            # ser.write(b'A')
        else:
            print("narrow")
            # ser.write(b'B')
        # time.sleep(6)
        # ser.write(b'B')
        # x = ser.read()
        # print(x)

    def Average(self,lst):
        return sum(lst) / len(lst)

    def rad_to_deg(self, rad):
        return rad * (180 / math.pi)

    def get_pose_key_angles(self, track):
        """applies pose estimation on frame, gets the distances between points"""
        pose = track.last_seen_detection.pose
        # for the key points that do not come in pairs
        RShoulder_pos = None
        RWrist_pos = None
        LShoulder_pos = None
        LWrist_pos = None
        Neck_pos = None
        RElbow_pos = None
        LElbow_pos = None
        MHip_pos = None
        RHip_pos = None
        RKnee_pos = None
        RAnkle_pos = None
        LHip_pos = None
        LKnee_pos = None
        LAnkle_pos = None

        self.POINTS = track.last_seen_detection.pose

        for pair in self.POSE_PAIRS:
            # ex: pair 1: [["Neck","RShoulder"]]
            # partFrom = Neck, partTo = RShoulder
            partFrom = pair[0]
            partTo = pair[1]
            assert (partFrom in self.BODY_PARTS)
            assert (partTo in self.BODY_PARTS)

            # continuing ex: idFrom = BODY_PART["Neck"] returns 1
            # similarly, idTo = BODY_PARTS["RShoulder"] returns 2
            idFrom = self.BODY_PARTS[partFrom]
            idTo = self.BODY_PARTS[partTo]

            # if found points (if not found, returns None)
            if self.POINTS[idFrom] is not None and self.POINTS[idTo] is not None:

                # now we check each of the key points.
                # "a", "b" correspond to the lengths of the limbs, "c" is the length between the end dots on the triangle. See video.
                # we use law of cosines to find angle c:
                # cos(C) = (a^2 + b^2 - c^2) / 2ab
                # we first check for the points that do not come in pairs (make up the longest side of the triangle in the vid)

                if (partFrom == "RShoulder"):
                    RShoulder_pos = self.POINTS[idFrom]

                if (partTo == "RWrist"):
                    RWrist_pos = self.POINTS[idTo]

                if (partFrom == "LShoulder"):
                    LShoulder_pos = self.POINTS[idFrom]

                if (partTo == "LWrist"):
                    LWrist_pos = self.POINTS[idTo]

                if (partFrom == "Neck"):
                    Neck_pos = self.POINTS[idFrom]

                if (partTo == "RElbow"):
                    RElbow_pos = self.POINTS[idTo]

                if (partTo == "LElbow"):
                    LElbow_pos = self.POINTS[idTo]

                if (partFrom == "MHip"):
                    MHip_pos = self.POINTS[idFrom]

                if (partFrom == "RHip"):
                    RHip_pos = self.POINTS[idFrom]

                if (partTo == "RKnee"):
                    RKnee_pos = self.POINTS[idTo]

                if (partTo == "RAnkle"):
                    RAnkle_pos = self.POINTS[idTo]

                if (partFrom == "LHip"):
                    LHip_pos = self.POINTS[idFrom]

                if (partTo == "LKnee"):
                    LKnee_pos = self.POINTS[idTo]

                if (partTo == "LAnkle"):
                    LAnkle_pos = self.POINTS[idTo]

                # START (R) Shoulder -> Elbow -> Wrist

                if (partFrom == "RShoulder" and partTo == "RElbow"):
                    dist_2 = (self.POINTS[idFrom][0] - self.POINTS[idTo][0]) ** 2 + (
                                self.POINTS[idFrom][1] - self.POINTS[idTo][1]) ** 2
                    self.KEY_DISTANCES["RArm"]["RShoulder-RElbow"] = dist_2

                elif (partFrom == "RElbow" and partTo == "RWrist"):
                    dist_2 = (self.POINTS[idFrom][0] - self.POINTS[idTo][0]) ** 2 + (
                                self.POINTS[idFrom][1] - self.POINTS[idTo][1]) ** 2
                    self.KEY_DISTANCES["RArm"]["RElbow-RWrist"] = dist_2

                # END (R) Shoulder -> Elbow -> Wrist

                # START (L) Shoulder -> Elbow -> Wrist

                elif (partFrom == "LShoulder" and partTo == "LElbow"):
                    dist_2 = (self.POINTS[idFrom][0] - self.POINTS[idTo][0]) ** 2 + (
                                self.POINTS[idFrom][1] - self.POINTS[idTo][1]) ** 2
                    self.KEY_DISTANCES["LArm"]["LShoulder-LElbow"] = dist_2

                elif (partFrom == "LElbow" and partTo == "LWrist"):
                    dist_2 = (self.POINTS[idFrom][0] - self.POINTS[idTo][0]) ** 2 + (
                                self.POINTS[idFrom][1] - self.POINTS[idTo][1]) ** 2
                    self.KEY_DISTANCES["LArm"]["LElbow-LWrist"] = dist_2

                # END (L) Shoulder -> Elbow -> Wrist

                # START (R) Neck -> Shoulder -> Elbow, (L) Neck -> Shoulder -> Elbow
                # note we have already gotten Shoulder-Elbow values!

                elif (partFrom == "Neck" and partTo == "RShoulder"):
                    dist_2 = (self.POINTS[idFrom][0] - self.POINTS[idTo][0]) ** 2 + (
                                self.POINTS[idFrom][1] - self.POINTS[idTo][1]) ** 2
                    self.KEY_DISTANCES["RArm"]["Neck-RShoulder"] = dist_2

                elif (partFrom == "Neck" and partTo == "LShoulder"):
                    dist_2 = (self.POINTS[idFrom][0] - self.POINTS[idTo][0]) ** 2 + (
                                self.POINTS[idFrom][1] - self.POINTS[idTo][1]) ** 2
                    self.KEY_DISTANCES["LArm"]["Neck-LShoulder"] = dist_2

                # END (R) Neck -> Shoulder -> Elbow, (L) Neck -> Shoulder -> Elbow

                # START (R) Hip -> Knee -> Ankle

                elif (partFrom == "RHip" and partTo == "RKnee"):
                    dist_2 = (self.POINTS[idFrom][0] - self.POINTS[idTo][0]) ** 2 + (
                                self.POINTS[idFrom][1] - self.POINTS[idTo][1]) ** 2
                    self.KEY_DISTANCES["RLeg"]["RHip-RKnee"] = dist_2

                elif (partFrom == "RKnee" and partTo == "RAnkle"):
                    dist_2 = (self.POINTS[idFrom][0] - self.POINTS[idTo][0]) ** 2 + (
                                self.POINTS[idFrom][1] - self.POINTS[idTo][1]) ** 2
                    self.KEY_DISTANCES["RLeg"]["RKnee-RAnkle"] = dist_2

                # END (R) Hip -> Knee -> Ankle

                # START (L) Hip -> Knee -> Ankle

                elif (partFrom == "LHip" and partTo == "LKnee"):
                    dist_2 = (self.POINTS[idFrom][0] - self.POINTS[idTo][0]) ** 2 + (
                                self.POINTS[idFrom][1] - self.POINTS[idTo][1]) ** 2
                    self.KEY_DISTANCES["LLeg"]["LHip-LKnee"] = dist_2

                elif (partFrom == "LKnee" and partTo == "LAnkle"):
                    dist_2 = (self.POINTS[idFrom][0] - self.POINTS[idTo][0]) ** 2 + (
                                self.POINTS[idFrom][1] - self.POINTS[idTo][1]) ** 2
                    self.KEY_DISTANCES["LLeg"]["LKnee-LAnkle"] = dist_2

                # START (R) MHip -> RHip -> RKnee, (L) MHip -> LHip -> LKnee
                # note we have already gotten Hip-Knee values!

                elif (partFrom == "MHip" and partTo == "RHip"):
                    dist_2 = (self.POINTS[idFrom][0] - self.POINTS[idTo][0]) ** 2 + (
                            self.POINTS[idFrom][1] - self.POINTS[idTo][1]) ** 2
                    self.KEY_DISTANCES["RLeg"]["MHip-RHip"] = dist_2

                elif (partFrom == "MHip" and partTo == "LHip"):
                    dist_2 = (self.POINTS[idFrom][0] - self.POINTS[idTo][0]) ** 2 + (
                            self.POINTS[idFrom][1] - self.POINTS[idTo][1]) ** 2
                    self.KEY_DISTANCES["LLeg"]["MHip-LHip"] = dist_2

        # we get the angles at the end.
        if (RShoulder_pos is not None and RWrist_pos is not None):

            c_2 = (RShoulder_pos[0] - RWrist_pos[0]) ** 2 + (RShoulder_pos[1] - RWrist_pos[1]) ** 2

            a_2 = self.KEY_DISTANCES["RArm"]["RShoulder-RElbow"]
            b_2 = self.KEY_DISTANCES["RArm"]["RElbow-RWrist"]

            # because degrees are easily to visualize for me:
            try:
                theta = self.rad_to_deg(math.acos((a_2 + b_2 - c_2) / (2 * math.sqrt(a_2 * b_2))))

            except ZeroDivisionError:
                theta = "Error"
            if (math.isnan(theta)):
                theta = self.KEY_ANGLES["RArm"][-1]
            self.KEY_ANGLES["RArm"].append(theta)

        if (LShoulder_pos is not None and LWrist_pos is not None):

            c_2 = (LShoulder_pos[0] - LWrist_pos[0]) ** 2 + (LShoulder_pos[1] - LWrist_pos[1]) ** 2

            a_2 = self.KEY_DISTANCES["LArm"]["LShoulder-LElbow"]
            b_2 = self.KEY_DISTANCES["LArm"]["LElbow-LWrist"]

            # because degrees are easily to visualize for me:
            try:
                theta = self.rad_to_deg(math.acos((a_2 + b_2 - c_2) / (2 * math.sqrt(a_2 * b_2))))

            except ZeroDivisionError:
                theta = None

            if (math.isnan(theta)):
                theta = self.KEY_ANGLES["LArm"][-1]
            self.KEY_ANGLES["LArm"].append(theta)

        if (Neck_pos is not None and LElbow_pos is not None):

            c_2 = (Neck_pos[0] - LElbow_pos[0]) ** 2 + (Neck_pos[1] - LElbow_pos[1]) ** 2

            a_2 = self.KEY_DISTANCES["LArm"]["Neck-LShoulder"]
            b_2 = self.KEY_DISTANCES["LArm"]["LShoulder-LElbow"]

            # because degrees are easily to visualize for me:
            try:
                theta = self.rad_to_deg(math.acos((a_2 + b_2 - c_2) / (2 * math.sqrt(a_2 * b_2))))

            except ZeroDivisionError:
                theta = None
            if (math.isnan(theta)):
                theta = self.KEY_ANGLES["LShoulder"][-1]
            if (self.POINTS[6][1] < self.POINTS[1][1]):
                theta = 360 - theta
            self.KEY_ANGLES["LShoulder"].append(theta)

        if (Neck_pos is not None and RElbow_pos is not None):

            c_2 = (Neck_pos[0] - RElbow_pos[0]) ** 2 + (Neck_pos[1] - RElbow_pos[1]) ** 2

            a_2 = self.KEY_DISTANCES["RArm"]["Neck-RShoulder"]
            b_2 = self.KEY_DISTANCES["RArm"]["RShoulder-RElbow"]

            # because degrees are easily to visualize for me:
            try:
                theta = self.rad_to_deg(math.acos((a_2 + b_2 - c_2) / (2 * math.sqrt(a_2 * b_2))))

            except ZeroDivisionError:
                theta = None
            if (math.isnan(theta)):
                theta = self.KEY_ANGLES["RShoulder"][-1]
            if (self.POINTS[3][1] < self.POINTS[1][1]):
                theta = 360 - theta
            self.KEY_ANGLES["RShoulder"].append(theta)

        if (RHip_pos is not None and RAnkle_pos is not None):

            c_2 = (RHip_pos[0] - RAnkle_pos[0]) ** 2 + (RHip_pos[1] - RAnkle_pos[1]) ** 2

            a_2 = self.KEY_DISTANCES["RLeg"]["RHip-RKnee"]
            b_2 = self.KEY_DISTANCES["RLeg"]["RKnee-RAnkle"]

            # because degrees are easily to visualize for me:
            try:
                theta = self.rad_to_deg(math.acos((a_2 + b_2 - c_2) / (2 * math.sqrt(a_2 * b_2))))

            except ZeroDivisionError:
                theta = None

            if (math.isnan(theta)):
                theta = self.KEY_ANGLES["RLeg"][-1]
            self.KEY_ANGLES["RLeg"].append(theta)

        if (LHip_pos is not None and LAnkle_pos is not None):

            c_2 = (LHip_pos[0] - LAnkle_pos[0]) ** 2 + (LHip_pos[1] - LAnkle_pos[1]) ** 2

            a_2 = self.KEY_DISTANCES["LLeg"]["LHip-LKnee"]
            b_2 = self.KEY_DISTANCES["LLeg"]["LKnee-LAnkle"]

            # because degrees are easily to visualize for me:
            try:
                theta = self.rad_to_deg(math.acos((a_2 + b_2 - c_2) / (2 * math.sqrt(a_2 * b_2))))

            except ZeroDivisionError:
                theta = None

            if (math.isnan(theta)):
                theta = self.KEY_ANGLES["LLeg"][-1]
            self.KEY_ANGLES["LLeg"].append(theta)

        if (MHip_pos is not None and RKnee_pos is not None):

            c_2 = (MHip_pos[0] - RKnee_pos[0]) ** 2 + (MHip_pos[1] - RKnee_pos[1]) ** 2

            a_2 = self.KEY_DISTANCES["RLeg"]["RHip-RKnee"]
            b_2 = self.KEY_DISTANCES["RLeg"]["MHip-RHip"]

            # because degrees are easily to visualize for me:
            try:
                theta = self.rad_to_deg(math.acos((a_2 + b_2 - c_2) / (2 * math.sqrt(a_2 * b_2))))

            except ZeroDivisionError:
                theta = None

            if (math.isnan(theta)):
                theta = self.KEY_ANGLES["RHip"][-1]
            if (self.POINTS[10][1] < self.POINTS[8][1]):
                theta = 360 - theta
            self.KEY_ANGLES["RHip"].append(theta)

        if (MHip_pos is not None and LKnee_pos is not None):

            c_2 = (MHip_pos[0] - LKnee_pos[0]) ** 2 + (MHip_pos[1] - LKnee_pos[1]) ** 2

            a_2 = self.KEY_DISTANCES["LLeg"]["LHip-LKnee"]
            b_2 = self.KEY_DISTANCES["LLeg"]["MHip-LHip"]

            # because degrees are easily to visualize for me:
            try:
                theta = self.rad_to_deg(math.acos((a_2 + b_2 - c_2) / (2 * math.sqrt(a_2 * b_2))))

            except ZeroDivisionError:
                theta = None

            if (math.isnan(theta)):
                theta = self.KEY_ANGLES["LHip"][-1]
            if (self.POINTS[13][1] < self.POINTS[8][1]):
                theta = 360 - theta
            self.KEY_ANGLES["LHip"].append(theta)

    def run(self, csvWriter, arduino, tracking_quadrant=0, quad_command="seq_0"):
        result, self.currentFrame = self.capture0.read()
        datum = op.Datum()
        datum.cvInputData = self.currentFrame
        self.openpose.emplaceAndPop(op.VectorDatum([datum]))
        keypoints, self.currentFrame = np.array(datum.poseKeypoints), datum.cvOutputData
        cv2.putText(self.currentFrame, arduino.debug_string(), (20, 70), 0, 0.4, (255,255,0), 1)
        #print(keypoints)
        # Doesn't use keypoint confidence


        if keypoints.any():
            poses = keypoints[:,:,:2]
            # Get containing box for each seen body
            boxes = poses2boxes(poses)
            boxes_xywh = [[x1,y1,x2-x1,y2-y1] for [x1,y1,x2,y2] in boxes]
            features = self.encoder(self.currentFrame,boxes_xywh)
            #print(features)

            nonempty = lambda xywh: xywh[2] != 0 and xywh[3] != 0
            detections = [Detection(bbox, 1.0, feature, pose) for bbox, feature, pose in zip(boxes_xywh, features, poses) if nonempty(bbox)]
            # Run non-maxima suppression.
            boxes_det = np.array([d.tlwh for d in detections])
            scores = np.array([d.confidence for d in detections])
            indices = preprocessing.non_max_suppression(boxes_det, self.nms_max_overlap, scores)
            detections = [detections[i] for i in indices]
            # Call the tracker
            self.tracker.predict()
            self.tracker.update(self.currentFrame, detections)

            hand_count = 0
            raise_count = 0

            quadrants=[]
            for track in self.tracker.tracks:
                color = None
                if not track.is_confirmed():
                    color = (0,0,255)
                else:
                    color = (255,255,255)
                bbox = track.to_tlbr()
                #print(track.last_seen_detection.pose)

                #self.printCSV(track, csvWriter)
                #self.printCSVforVideo(track, csvWriter)
                for i in range(0,4):
                    if len(quadrants) < i+1:
                        q_col = 0 if (i % 2) == 0 else 1
                        q_row = 0 if i < 2 else 1
                        start_x = 0 if q_col <= 0 else Constants.SCREEN_WIDTH/2
                        end_x = Constants.SCREEN_WIDTH/2 if q_col <= 0 else Constants.SCREEN_WIDTH
                        start_y = 0 if q_row <= 0 else Constants.SCREEN_HEIGHT/2
                        end_y = Constants.SCREEN_HEIGHT/2 if q_row <= 0 else Constants.SCREEN_HEIGHT
                        quadrants.append({"count": 0, "start_x": start_x, "end_x":end_x, "start_y":start_y, "end_y":end_y })
                    min_y = min(int(bbox[1]), int(bbox[3]))
                    min_x = min(int(bbox[0]), int(bbox[2]))
                    print(f"Quadrant {i+1} [{q_row}, {q_col}] - Count: {quadrants[i]['count']} x=[{quadrants[i]['start_x']}, {quadrants[i]['end_x']}] - y=[{quadrants[i]['start_y']}, {quadrants[i]['end_y']}]")
                    if quadrants[i]["start_x"] <= min_x <= quadrants[i]["end_x"] and quadrants[i]["start_y"] <= min_y <= quadrants[i]["end_y"]:
                        quadrants[i]["count"] += 1

                cv2.rectangle(self.currentFrame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])),color, 2)
                cv2.putText(self.currentFrame, "id%s - ts%s"%(track.track_id,track.time_since_update),(int(bbox[0]), int(bbox[1])-20),0, 0.5, (0,255,0),1)
            for i in range(0,len(quadrants)):
                quad = quadrants[i]
                text_x = int(quad['start_x'])
                text_y = int(quad['end_y'])
                offset = 20
                cv2.rectangle(self.currentFrame, (int(quad["start_x"]), int(quad["start_y"])), (int(quad["end_x"]), int(quad["end_y"])), (255,0,0), 1)
                cv2.putText(self.currentFrame, f"Q{i+1}: {quad['count']}",(text_x+offset, text_y-offset),0, 0.6, (0,0,255),2)
                if i == tracking_quadrant:
                    if(quad["count"] > 0):
                        arduino.send_command(quad_command)
                        # cv2.putText(self.currentFrame, f"{quad_command} sent",((text_x+offset, text_y-(offset*2)),0, 0.6, (0,0,255),2))


            """
                # detect hand raise
                if track.last_seen_detection.pose[1][1] > 0:
                    hand_count += 2
                    if track.last_seen_detection.pose[4][1] < track.last_seen_detection.pose[2][1]:
                        raise_count += 1
                #if track.last_seen_detection.pose[7][1] > 0:

                    if track.last_seen_detection.pose[7][1] < track.last_seen_detection.pose[5][1]:
                        raise_count += 1

            # change on/off frequency
            if hand_count == 0:
                percentage = 0
            else:
                percentage = raise_count / hand_count

            m = interp1d([0, 1], [2500, 350])
            #ser.write((str(int(m(percentage)))+'\n').encode())
            #ser.write((str(percentage*100)+'\n').encode())
            #ser.flush()

            print((str(percentage*100)+'\n').encode())
            """

            #joint angles
            """
            self.KEY_ANGLES = {"RShoulder": collections.deque(self.queue_size * [0], self.queue_size),
                               "LShoulder": collections.deque(self.queue_size * [0], self.queue_size),
                               "RArm": collections.deque(self.queue_size * [0], self.queue_size),
                               "LArm": collections.deque(self.queue_size * [0], self.queue_size),
                               "RHip": collections.deque(self.queue_size * [0], self.queue_size),
                               "LHip": collections.deque(self.queue_size * [0], self.queue_size),
                               "RLeg": collections.deque(self.queue_size * [0], self.queue_size),
                               "LLeg": collections.deque(self.queue_size * [0], self.queue_size)}
            """
            #self.printCSVforVideo(track, csvWriter)
            #self.get_pose_key_angles(track)
            #self.movement_value = self.Average(self.KEY_ANGLES["RShoulder"]) + self.Average(self.KEY_ANGLES["LShoulder"]) - self.Average(self.KEY_ANGLES["RArm"]) - self.Average(self.KEY_ANGLES["LArm"]) + self.Average(self.KEY_ANGLES["RHip"]) + self.Average(self.KEY_ANGLES["LHip"]) - self.Average(self.KEY_ANGLES["RLeg"]) - self.Average(self.KEY_ANGLES["LLeg"])
            #print(self.movement_value)
            #self.movement_value = max(min(self.movement_value, 200), -300)
            #m = interp1d([-300, 200], [0, 29])
            #print(str(int(m(self.movement_value))))
            #csvWriter.writerow(str(int(m(self.movement_value))))

            #time.sleep(0.5)
            cv2.waitKey(1)

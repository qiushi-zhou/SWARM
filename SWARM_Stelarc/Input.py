# -*- coding: utf-8 -*-
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
import cv2

# Load OpenPose:
dir_path = os.path.dirname(os.path.realpath(__file__))
try:
        # Windows Import
    if platform == "win32":
            # Change these variables to point to the correct folder (Release/x64 etc.)
        sys.path.append(dir_path + '/../../python/openpose/Release');
        os.environ['PATH']  = os.environ['PATH'] + ';' + dir_path + '/../../x64/Release;' +  dir_path + '/../../bin;'
        import pyopenpose as op
    else:
            # Change these variables to point to the correct folder (Release/x64 etc.)
        sys.path.append('../../python');
            # If you run `make install` (default path is `/usr/local/python` for Ubuntu), you can also access the OpenPose/python module from there. This will install OpenPose and the python library at your desired installation path. Ensure that this is in your python path in order to use it.
            # sys.path.append('/usr/local/python')
        from openpose import pyopenpose as op
except ImportError as e:
    print('Error: OpenPose library could not be found. Did you enable `BUILD_PYTHON` in CMake and have this Python script in the right folder?')
    raise e

server = imagiz.TCP_Server(9990)# TCP testing code
server.start()# TCP testing code

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
        #params["write_video"] = "test.avi"
        params["write_images"] = "videos/"
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

        #self.capture = cv2.VideoCapture('Video/DJI_0561.mp4')
        self.capture = cv2.VideoCapture(0)

        if self.capture.isOpened():         # Checks the stream
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1080)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1920)
            self.frameSize = (int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                               int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)))
        Constants.SCREEN_HEIGHT = self.frameSize[0]
        Constants.SCREEN_WIDTH = self.frameSize[1]
        self.start_time = time.time()


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
        s = str(self.capture.get(cv2.CAP_PROP_POS_MSEC)) + ',' + str(track.track_id)
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

    def run(self, csvWriter, ser):
        #message = server.receive() # TCP testing code
        result, self.currentFrame = self.capture.read()
        datum = op.Datum()
        datum.cvInputData = self.currentFrame
        #datum.cvInputData = cv2.imdecode(message.image,1) # TCP testing code
        self.openpose.emplaceAndPop(op.VectorDatum([datum]))

        keypoints, self.currentFrame = np.array(datum.poseKeypoints), datum.cvOutputData
        #print(keypoints)
        # Doesn't use keypoint confidence

        if keypoints.any():
            poses = keypoints[:,:,:2]
            # Get containing box for each seen body
            boxes = poses2boxes(poses)
            boxes_xywh = [[x1,y1,x2-x1,y2-y1] for [x1,y1,x2,y2] in boxes]
            features = self.encoder(self.currentFrame,boxes_xywh)
            # print(features)

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

            for track in self.tracker.tracks:
                color = None
                if not track.is_confirmed():
                    color = (0,0,255)
                else:
                    color = (255,255,255)
                bbox = track.to_tlbr()
                #print(track.last_seen_detection.pose)

                #self.printCSV(track, csvWriter)
                self.printCSVforVideo(track, csvWriter)
                cv2.rectangle(self.currentFrame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])),color, 2)
                cv2.putText(self.currentFrame, "id%s - ts%s"%(track.track_id,track.time_since_update),(int(bbox[0]), int(bbox[1])-20),0, 5e-3 * 200, (0,255,0),2)
                #print(track.last_seen_detection.pose[4])
                #print(track.last_seen_detection.pose[7])
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

            #m = interp1d([0, 1], [2500, 350])
            #ser.write((str(int(m(percentage)))+'\n').encode())
            #ser.write((str(percentage*100)+'\n').encode())
            #ser.flush()
            #print((str(percentage*100)+'\n').encode())
            cv2.waitKey(1)

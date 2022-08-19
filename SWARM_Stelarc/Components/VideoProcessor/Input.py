# -*- coding: utf-8 -*-
import numpy as np
import sys
import os
from sys import platform
import time
from deep_sort.detection import Detection
from deep_sort.tracker import Tracker as DeepTracker
from deep_sort import nn_matching
from deep_sort import preprocessing
from tools import generate_detections as gdet
from Utils.utils import poses2boxes
import Constants

# app = Flask(__name__)

# Load OpenPose:
dir_path = os.path.dirname(os.path.realpath(__file__))
openpose_modelfolder = Constants.openpose_modelfolder
if Constants.use_processing:
    try:
        # Windows Import
        if platform == "win32":
            # Change these variables to point to the correct folder (Release/x64 etc.)
            sys.path.append(dir_path + '/../openpose/windows/python')
            os.environ['PATH'] = os.environ['PATH'] + ';' + dir_path + '/../build/x64/Release;' + dir_path + '/../build/bin;'
            import pyopenpose as op
        else:
            # Change these variables to point to the correct folder (Release/x64 etc.)
            sys.path.append('../openpose/mac/python/')
            # If you run `make install` (default path is `/usr/local/python` for Ubuntu), you can also access the OpenPose/python module from there. This will install OpenPose and the python library at your desired installation path. Ensure that this is in your python path in order to use it.
            # sys.path.append('/usr/local/python')
            # Fix Issue with attempt to free invalid pointer:
            # https://github.com/CMU-Perceptual-Computing-Lab/openpose/issues/1902#issuecomment-1024890817
            # https://stackoverflow.com/questions/53203644/caffe-is-conflicted-with-python-cv2/53386302#53386302
            from openpose import pyopenpose as op
    except ImportError as e:
        print('Error: OpenPose library could not be found. Did you enable `BUILD_PYTHON` in CMake and have this Python script in the right folder?')
        raise e


class Input:
    def __init__(self, debug=False):
        # from openpose import *
        params = dict()
        params["model_folder"] = openpose_modelfolder
        print(f"Using openpose model at {params['model_folder']}")
        params["net_resolution"] = "-1x320"
        if Constants.use_openpose:
            self.openpose = op.WrapperPython()
            self.openpose.configure(params)
            self.openpose.start()

        max_cosine_distance = Constants.max_cosine_distance
        nn_budget = Constants.nn_budget
        self.nms_max_overlap = Constants.nms_max_overlap
        max_age = Constants.max_age
        n_init = Constants.n_init

        model_filename = 'model_data/mars-small128.pb'
        self.encoder = gdet.create_box_encoder(model_filename, batch_size=1)
        metric = nn_matching.NearestNeighborDistanceMetric("cosine", max_cosine_distance, nn_budget)
        self.tracker = DeepTracker(metric, max_age=max_age, n_init=n_init)

        self.start_time = time.time()

        # For calculating angels:

        self.BODY_PARTS = {"Nose": 0, "Neck": 1, "RShoulder": 2, "RElbow": 3, "RWrist": 4,
                           "LShoulder": 5, "LElbow": 6, "LWrist": 7, "MHip": 8, "RHip": 9, "RKnee": 10,
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

    # def print_csv(self, track, csv_writer):
    #     s = str(time.time() - self.start_time) + ',' + str(track.track_id)
    #     for i in track.last_seen_detection.pose:
    #         for j in i:
    #             s += (',' + str(j))
    #     csv_writer.writerow([s])
    #     s = ""

    # def print_csvforVideo(self, track, csv_writer):
    #     s = str(self.capture0.get(self.cv2.CAP_PROP_POS_MSEC)) + ',' + str(track.track_id)
    #     for i in track.last_seen_detection.pose:
    #         for j in i:
    #             s += (',' + str(j))
    #     csv_writer.writerow([s])

    def update_trackers(self, frame):
        datum = op.Datum()
        datum.cvInputData = frame
        self.openpose.emplaceAndPop(op.VectorDatum([datum]))
        keypoints = np.array(datum.poseKeypoints)
        frame = datum.cvOutputData
        # print(keypoints)
        # Doesn't use keypoint confidence

        if keypoints.any():
            poses = keypoints[:, :, :2]
            # Get containing box for each seen body
            boxes = poses2boxes(poses)
            boxes_xywh = [[x1, y1, x2 - x1, y2 - y1] for [x1, y1, x2, y2] in boxes]
            features = self.encoder(frame, boxes_xywh)
            # print(features)

            nonempty = lambda xywh: xywh[2] != 0 and xywh[3] != 0
            detections = [Detection(bbox, 1.0, feature, pose) for bbox, feature, pose in
                          zip(boxes_xywh, features, poses) if nonempty(bbox)]
            # Run non-maxima suppression.
            boxes_det = np.array([d.tlwh for d in detections])
            scores = np.array([d.confidence for d in detections])
            indices = preprocessing.non_max_suppression(boxes_det, self.nms_max_overlap, scores)
            detections = [detections[i] for i in indices]
            # Call the tracker
            self.tracker.predict()
            self.tracker.update(frame, detections)

            hand_count = 0
            raise_count = 0
            return self.tracker.tracks, keypoints, frame
        return self.tracker.tracks, keypoints, None



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

        # joint angles
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
        # self.print_csvforVideo(track, csv_writer)
        # self.get_pose_key_angles(track)
        # self.movement_value = self.Average(self.KEY_ANGLES["RShoulder"]) + self.Average(self.KEY_ANGLES["LShoulder"]) - self.Average(self.KEY_ANGLES["RArm"]) - self.Average(self.KEY_ANGLES["LArm"]) + self.Average(self.KEY_ANGLES["RHip"]) + self.Average(self.KEY_ANGLES["LHip"]) - self.Average(self.KEY_ANGLES["RLeg"]) - self.Average(self.KEY_ANGLES["LLeg"])
        # print(self.movement_value)
        # self.movement_value = max(min(self.movement_value, 200), -300)
        # m = interp1d([-300, 200], [0, 29])
        # print(str(int(m(self.movement_value))))
        # csv_writer.writerow(str(int(m(self.movement_value))))

        # time.sleep(0.5)

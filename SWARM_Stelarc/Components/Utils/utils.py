import numpy as np
from numba import jit
import itertools
import oyaml as yaml
import os
import datetime

def is_in_working_hours(working_days, working_hours):
    now = datetime.datetime.now()
    day = now.strftime('%A').lower()
    if any([True if x in day else False for x in working_days]):
        start = now.replace(hour=working_hours[0].tm_hour, minute=working_hours[0].tm_min, second=0, microsecond=0)
        end = now.replace(hour=working_hours[1].tm_hour, minute=working_hours[1].tm_min, second=0, microsecond=0)
        return not (start <= now <= end)
    else:
       return True

def convert_data(obj, key="NONE"):
    obj_type = obj.__class__.__name__
    try:
        if "list" in obj_type:
            return [convert_data(el) for el in obj]
        if 'dict' in obj_type:
            res = {}
            for k, v in obj.items():
                res[k] = convert_data(obj[k], k)
            return res
        if 'datetime' in obj_type:
            # print(f"Serializing obj {key} - {obj_type}")
            return obj.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error serializing obj {key} - {obj_type}: {e}")
    return obj
def serialize_datetime(dict_obj):
    dict_obj = dict_obj.copy()
    dict_obj = convert_data(dict_obj)
    return dict_obj

def update_config_from_file(app_logger, tag, file_path, last_modified_time, callback):
    try:
        if last_modified_time < os.path.getmtime(file_path):
            with open(file_path) as file:
                app_logger.debug(f"Updating {tag} configuration {file_path}")
                callback(yaml.load(file, Loader=yaml.FullLoader), os.path.getmtime(file_path))
    except Exception as e:
        app_logger.error(f"Error opening {tag} behavior config file: {e}")

class Point:
    def __init__(self, x, y, z=None):
        self.id = id
        self.x = x
        self.y = y
        self.z = z
        if self.z is None:
            self.pos = np.array([self.x, self.y])
        else:
            self.pos = np.array([self.x, self.y, self.z])

    def is_2d(self):
        if self.z is None:
            return True
        return False

    def distance_from(self, point):
        if point.is_2d() != self.is_2d():
            print(f"Cannot calculate distance between 2D and 3D points")

        squared_dist = np.sum((self.pos-point.pos)**2, axis=0)
        return np.sqrt(squared_dist)

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return izip(a, b)

def poses2boxes(poses):
    global seen_bodyparts
    """
    Parameters
    ----------
    poses: ndarray of human 2D poses [People * BodyPart]
    Returns
    ----------
    boxes: ndarray of containing boxes [People * [x1,y1,x2,y2]]
    """
    boxes = []
    for person in poses:
        seen_bodyparts = person[np.where((person[:,0] != 0) | (person[:,1] != 0))]
        # box = [ int(min(seen_bodyparts[:,0])),int(min(seen_bodyparts[:,1])),
        #        int(max(seen_bodyparts[:,0])),int(max(seen_bodyparts[:,1]))]
        mean = np.mean(seen_bodyparts, axis=0)
        deviation = np.std(seen_bodyparts, axis = 0)
        box = [int(mean[0]-deviation[0]), int(mean[1]-deviation[1]), int(mean[0]+deviation[0]), int(mean[1]+deviation[1])]
        boxes.append(box)
    return np.array(boxes)

def distancia_midpoints(mid1, mid2):
    return np.linalg.norm(np.array(mid1)-np.array(mid2))

def pose2midpoint(pose):
    """
    Parameters
    ----------
    poses: ndarray of human 2D pose [BodyPart]
    Returns
    ----------
    boxes: pose midpint [x,y]
    """
    box = poses2boxes([pose])[0]
    midpoint = [np.mean([box[0],box[2]]), np.mean([box[1],box[3]])]
    return np.array(midpoint)

@jit
def iou(bb_test,bb_gt):
    """
    Computes IUO between two bboxes in the form [x1,y1,x2,y2]
    """
    xx1 = np.maximum(bb_test[0], bb_gt[0])
    yy1 = np.maximum(bb_test[1], bb_gt[1])
    xx2 = np.minimum(bb_test[2], bb_gt[2])
    yy2 = np.minimum(bb_test[3], bb_gt[3])
    w = np.maximum(0., xx2 - xx1)
    h = np.maximum(0., yy2 - yy1)
    wh = w * h
    o = wh / ((bb_test[2]-bb_test[0])*(bb_test[3]-bb_test[1])
        + (bb_gt[2]-bb_gt[0])*(bb_gt[3]-bb_gt[1]) - wh)
    return(o)

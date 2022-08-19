from ..SwarmComponentMeta import SwarmComponentMeta
import threading
import cv2

class ProcessedFrameData:
    def __init__(self, tracks=None, keypoints=None, frame=None):
        self.tracks = [] if tracks is None else tracks
        self.keypoints = [] if keypoints is None else keypoints
        self.frame = None if frame is None else frame
        
class OpenposeManager(SwarmComponentMeta):
        
    def __init__(self, logger, tasks_manager, camera_manager, enabled=True, multi_threaded=True, use_openpose=True):
        self.use_openpose = use_openpose
        if self.use_openpose:
            from . import Input
            self.input = Input.Input()
        super(OpenposeManager, self).__init__(logger, tasks_manager, "OpenposeManager")
        self.camera_manager = camera_manager
        self.processed_frame_data = ProcessedFrameData()
        self.processed_frame_data_mt = ProcessedFrameData()
        self.camera_frame = None
        self.multi_threaded = multi_threaded
        self.frame_read_lock = None
        if self.multi_threaded:
            self.background_task = self.tasks_manager.add_task("OP", None, self.process_frame_async, None)
            self.frame_read_lock = self.background_task.read_lock
            self.background_task.start()

    def update_config(self):
        pass

    def update_config_data(self, data, last_modified_time):
        pass

    def process_frame_async(self, task_manager):
        if self.camera_frame is not None:
            new_frame = self.process_frame(self.use_openpose, self.camera_frame)
            with self.frame_read_lock:
                self.processed_frame_data_mt = new_frame
        return True
                    
    def process_frame(self, use_openpose, frame):
        try:
            if use_openpose:
                tracks, keypoints, updated_frame = self.input.update_trackers(frame)
            else:
                imgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                ret, thresh = cv2.threshold(imgray, 127, 255, 0)
                contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(frame, contours, -1, (0,255,0), 1)
                updated_frame = frame
                # img_blur = cv2.GaussianBlur(frame, (21,21), sigmaX=1, borderType=cv2.BORDER_DEFAULT)
                # edges = cv2.Canny(image=img_blur, threshold1=100, threshold2=200)
                # updated_frame = cv2.resize(edges, (self.camera_manager.screen_w, self.camera_manager.screen_h))
                keypoints = None
                tracks = None
        except Exception as e:
            print(f"Error processing frame: {e}")
            return ProcessedFrameData()
        return ProcessedFrameData(tracks, keypoints, updated_frame)
        
    def get_updated_frame(self):
        if self.processed_frame_data.frame is None:
            print(f"Updated frame is None")
        return self.processed_frame_data.frame

    def update(self, frame, debug=False):
        if debug:
            print(f"Updating Openpose Manager")
        if frame is None:
            return
        if debug:
            print(f"Updating tracks")
        # tracks, keypoints, updated_frame
        self.camera_frame = frame
        if not self.multi_threaded:
            self.camera_frame = frame
            self.processed_frame_data = self.process_frame(self.use_openpose, self.camera_frame)
        else:
            with self.frame_read_lock:
                self.processed_frame_data = self.processed_frame_data_mt
        # Reset graphs to get new points
        for camera in self.camera_manager.cameras:
            camera.p_graph.init_graph()

        for track in self.processed_frame_data.tracks:
            color = (255, 255, 255)
            if not track.is_confirmed():
                color = (0, 0, 255)
            bbox = track.to_tlbr()
            p1 = Point(int(bbox[0]), int(bbox[1]))
            p2 = Point(int(bbox[2]), int(bbox[3]))
            min_p = Point(min(p1.x, p2.x), min(p1.y, p2.y))
            chest_offset = Point(0, 0)
            # ((x1+x2)/2, (y1+y2)/2).
            center_x, center_y = (min_p.x + ((p2.x-p1.x)/2) + chest_offset.x,min_p.y + ((p2.y-p1.y)/2) + chest_offset.y)
            center_p = Point(center_x, center_y)
            color = (0, 255, 0)
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
                            self.logger.draw_line(p1, p2, color, thickness)
            for camera in self.camera_manager.cameras:
                # camera.check_track([p1,p2], center_p)
                camera.check_track([center_p], center_p)
            if debug:
                print(f"Center: ({center_x:.2f}, {center_y:.2f})")

    def draw(self):
        pass

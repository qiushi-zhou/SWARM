from ..SwarmComponentMeta import SwarmComponentMeta
import threading
import cv2
import time
from collections import deque
from ..Utils.utils import Point
from ..Utils.FPSCounter import FPSCounter


class ProcessedFrameData:
    def __init__(self, tracks=None, keypoints=None, frame=None):
        self.tracks = [] if tracks is None else tracks
        self.keypoints = [] if keypoints is None else keypoints
        self.frame = None if frame is None else frame
        
class OpenposeManager(SwarmComponentMeta):
    def __init__(self, logger, tasks_manager, camera_manager, use_processing=False, use_openpose=False):
        self.use_processing = use_processing
        self.use_openpose = use_openpose
        self.input = None
        super(OpenposeManager, self).__init__(logger, tasks_manager, "OpenposeManager")
        self.camera_manager = camera_manager
        self.processed_frame_data = ProcessedFrameData()
        self.frame_buffer_size = 3
        self.frames_to_process = deque([])
        self.frames_processed = deque([])
        self.latest_frame_data = None
        self.multi_threaded = False
        self.background_task = None
        self.processing_lock = threading.Lock()
        self.processed_lock = threading.Lock()
        self.fps_counter = FPSCounter()
        self.latest_fps = 0

    def update_config(self, use_processing=False, use_openpose=False, use_multithread=False):
        if use_openpose and self.input is None:
            from . import Input
            self.input = Input.Input()

        self.use_processing = use_processing
        self.use_openpose = use_openpose
        self.set_enabled_mt(use_multithread)

    def set_enabled_mt(self, enabled):
        if enabled:
            if not self.multi_threaded:
                self.background_task = self.tasks_manager.add_task("OP", None, self.processing_loop, None)
                self.background_task.start()
        else:
            if self.multi_threaded:
                if self.background_task:
                    self.background_task.stop()
        self.multi_threaded = enabled

    def update_config_data(self, data, last_modified_time):
        pass

    def processing_loop(self, task_manager=None):
        if len(self.frames_to_process) <= 0:
            return True
        with self.processing_lock:
            to_process = self.frames_to_process.popleft()
        processed = self.process_frame(to_process)
        with self.processed_lock:
            self.frames_processed.append(processed)
        return True

    def process_frame(self, to_process):
        if to_process is None:
            return ProcessedFrameData()
        try:
            if self.use_openpose:
                tracks, keypoints, updated_frame = self.input.update_trackers(to_process)
            elif self.use_processing:
                tracks, keypoints, updated_frame = self.simple_processing(to_process)
            else:
                tracks = None
                keypoints = None
                updated_frame = to_process
            self.fps_counter.frame_count += 1
            self.fps_counter.update()
            self.latest_fps = self.fps_counter.fps
            return ProcessedFrameData(tracks, keypoints, updated_frame)
        except Exception as e:
            print(f"Error processing frame: {e}")
        return ProcessedFrameData()

    def simple_processing(self, frame):
        imgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ret, thresh = cv2.threshold(imgray, 127, 255, 0)
        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        frame = cv2.blur(frame, (51,51), borderType=cv2.BORDER_DEFAULT)
        frame = cv2.drawContours(frame, contours, -1, (0, 255, 0), 1)
        # edges = cv2.Canny(image=img_blur, threshold1=100, threshold2=200)
        # frame = cv2.resize(edges, (self.camera_manager.screen_w, self.camera_manager.screen_h))

        return None, None, frame
        
    def get_updated_frame(self):
        if self.multi_threaded:
            if len(self.frames_processed) > 1:
                with self.processed_lock:
                    self.latest_frame_data = self.frames_processed.popleft()
            return self.latest_frame_data.frame if self.latest_frame_data is not None else None
        else:
            return self.processed_frame_data.frame

    def update(self, camera_frame, debug=False):
        if debug:
            print(f"Updating Openpose Manager")
        if camera_frame is None:
            return
        if debug:
            print(f"Updating tracks")
        # tracks, keypoints, updated_frame
        if not self.multi_threaded:
            self.processed_frame_data = self.process_frame(camera_frame)
        else:
            with self.processing_lock:
                self.processed_frame_data = self.latest_frame_data
        # Reset graphs to get new points
        if self.processed_frame_data is None:
            return

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

    def draw(self, text_pos, debug=False):
        text_pos = self.logger.add_text_line(f"OP - FPS: {self.latest_fps} Frames to process: {len(self.frames_to_process)}, Processed: {len(self.frames_processed)}", (255, 255, 0), text_pos)
        pass

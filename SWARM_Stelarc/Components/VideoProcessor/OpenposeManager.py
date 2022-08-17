from . import Input
from ..SwarmComponentMeta import SwarmComponentMeta

class OpenposeManager(SwarmComponentMeta):
    def __init__(self, logger, camera_manager, enabled=True):
        self.input = Input()
        super(OpenposeManager, self).__init__(logger, "OpenposeManager")
        self.camera_manager = camera_manager
        self.frame = None

    def update_config(self):
        pass

    def update_config_data(self, data, last_modified_time):
        pass
    
    def get_updated_frame():
        return self.frame

    def update(self, frame, debug=True):
        if debug:
            print(f"Updating tracks")

        tracks, keypoints, updated_frame = self.input.update_trackers(frame)
        if updated_frame is None:
            self.frame = frame
            return self.frame
        self.frame = updated_frame
        # Reset graphs to get new points
        for camera in self.camera_manager.cameras:
            camera.p_graph.init_graph()

        for track in tracks:
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

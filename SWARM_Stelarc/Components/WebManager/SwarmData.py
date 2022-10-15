import datetime
import base64
import cv2

class SwarmData:
    def __init__(self, image_data=None, cameras_data=None, swarm_data=None):
        self.image_data = image_data
        self.cameras_data = cameras_data
        self.swarm_data = swarm_data
        self.time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    def get_swarm_json(self):
        return self.swarm_data
    def get_cameras_json(self):
        if self.cameras_data is not None:
            return self.cameras_data

    def get_image_string(self):
        if self.image_data is not None:
            retval, buffer = cv2.imencode('.jpg', self.image_data)
            img_str = base64.b64encode(buffer).decode()
            # img_str = base64.b64encode(self.image_data.getvalue()).decode()
            return "data:image/jpeg;base64," + img_str
        return ''

    def get_json(self):
        data = {}
        data['swarm_data'] = self.get_swarm_json()
        data['graph_data'] = self.get_cameras_json()
        data['frame_data'] = self.get_image_string()
        data['datetime'] = self.time
        return data
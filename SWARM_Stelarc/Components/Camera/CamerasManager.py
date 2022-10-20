from .Camera import Camera
from ..SwarmComponentMeta import SwarmComponentMeta

class CamerasManager(SwarmComponentMeta):
    def __init__(self, app_logger, ui_drawer, tasks_manager, screen_w=500, screen_h=500):
        self.app_logger = app_logger
        self.screen_w = screen_w
        self.screen_h = screen_h
        super(CamerasManager, self).__init__(ui_drawer, tasks_manager, "CamerasManager", r'./Config/CamerasConfig.yaml', self.update_config_data)
        self.cameras = []
    
    def update_config(self):
      super().update_config_from_file(self.app_logger, self.tag, self.config_filename, self.last_modified_time)
        
    def update_config_data(self, data, last_modified_time):
        self.config_data = data
        cameras_data = self.config_data.get("cameras", [])
        for i in range(0, len(cameras_data)):
            if len(self.cameras) <= i:
                self.cameras.append(Camera(self.app_logger, i, self.screen_w, self.screen_h, cameras_data[i]))
            else:
                self.cameras[i].update_config(self.screen_w, self.screen_h, cameras_data[i])
        self.last_modified_time = last_modified_time

    def get_cameras_data(self):
        data = {}
        data['cameras'] = []
        for camera in self.cameras:
            if camera.enabled:
                data['cameras'].append(camera.get_data())
        return data
    
    def update(self, *args, **kwargs):
        debug = kwargs.get('debug', True)
        if debug:
            print(f"Updating Cameras Manager")
        for camera in self.cameras:
            if camera.enabled:
                camera.update_graph()
                
    def draw(self, debug=False, draw_graph_data=True, surfaces=None):
        if debug:
            print(f"Draw Cameras Manager")
        for i in range(0, len(self.cameras)):
            camera = self.cameras[i]
            camera.draw_debug(self.ui_drawer, draw_graph_data=draw_graph_data, surfaces=surfaces)

import numpy as np
class SwarmMapManager(SwarmComponentMeta):
    def __init__(self, logger=None, drawer=None):
        super(SwarmMapManager, self).__init__(logger, drawer, "SwarmMapManager")
        self.cameras = []
    
    def update_config(self):
        pass  
    
    def update(self, *args, **kwargs):
        pass
    
    def draw(self, *args, **kwargs):
        debug = kwargs.get('debug', True)
        if debug: print(f"Updating map...")
        height = 500
        width = 500
        map_canvas = np.ones((height, width, 3), np.uint8)
        map_canvas *= 255
        self.cv2.circle(map_canvas, (int(height/2), int(width/2)), Constants.inner_radius, (0, 0, 0), 2)
        self.cv2.circle(map_canvas, (int(height/2), int(width/2)), Constants.outer_radius, (0, 0, 0), 2)
        self.cv2.imshow("SWARM map", map_canvas)
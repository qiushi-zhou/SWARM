from people_graph import *

class Camera:
    def __init__(self, start_x, start_y, end_x, end_y, q_row, q_col):
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.q_row = q_row
        self.q_col = q_col
        self.avg_distance = 0
        self.num_people = 0
        self.people_graph = PeopleGraph()

    def is_in_camera(self, x, y):
        return self.start_x <= x <= self.end_x and self.start_y <= y <= self.end_y
    
    def update_camera_data(self):
        self.people_graph.calculate_edges()
        self.avg_distance = self.people_graph.get_average_distance()
        self.num_people = len(self.people_graph.get_nodes())
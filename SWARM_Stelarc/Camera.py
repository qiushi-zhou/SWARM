from people_graph import *

class Camera:
    def __init__(self, start_x, start_y, end_x, end_y, q_row, q_col, machine_x=-1, machine_y=-1):
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.q_row = q_row
        self.q_col = q_col
        self.machine_x = machine_x
        self.machine_y = machine_y
        if self.machine_x < 0:
            self.machine_x = start_x+((end_x - start_x)/2)
            self.machine_y = end_y
        self.avg_distance = 0
        self.avg_distance_from_machine = 0
        self.num_people = 0
        self.people_graph = PeopleGraph()

    def is_in_camera(self, x, y):
        return self.start_x <= x <= self.end_x and self.start_y <= y <= self.end_y
    
    def update_camera_data(self):
        self.people_graph.calculate_edges()
        self.avg_distance = self.people_graph.get_average_distance()
        self.avg_distance_from_machine = self.people_graph.get_average_distance_from_machine(self.machine_x, self.machine_y)
        self.num_people = len(self.people_graph.get_nodes())
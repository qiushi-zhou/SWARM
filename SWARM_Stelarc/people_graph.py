import networkx as nx
import math
import numpy as np
import itertools
import matplotlib.pyplot as plt
import Constants
from utils import Point

class PeopleGraph:
    def __init__(self):
        self.nx_graph = nx.Graph()
        self.edges_calculated = False
        self.n_people = 0
        self.n_groups = 0
        self.clusters = []
        self.avg_people_distance = 0
        self.avg_machine_distance = 0
        self.max_weight = 0
        self.min_weight = 9999

    def init_graph(self):
        PeopleGraph.__init__(self)

    def add_node(self, x, y, z=None):
        node = Point(x,y,z)
        self.nx_graph.add_node(node, pos=node.pos)
        return node.pos

    def add_edge(self, from_node, to_node, max_dist=-1):
        dist = from_node.distance_from(to_node)
        if max_dist > 0:
            if dist <= max_dist:
                self.nx_graph.add_edge(from_node, to_node, weight=dist)
                return dist
        else:
            self.nx_graph.add_edge(from_node, to_node, weight=dist)
        return dist
    
    def update_graph(self, machine_pos=None):
        self.calculate_edges()
        self.update_avg_distance()
        self.update_avg_machine_distance(machine_pos=machine_pos)

    def calculate_edges(self):
        for i in self.nx_graph.nodes():
            for j in self.nx_graph.nodes():
                if i != j:
                    if not self.nx_graph.has_edge(i, j):
                        w = self.add_edge(i, j)
                        if w >= self.max_weight:
                            self.max_weight = w
                        if w <= self.min_weight:
                            self.min_weight = w
        self.edges_calculated = True

    def update_avg_distance(self):
        n_edges = self.nx_graph.number_of_edges()
        if self.edges_calculated and n_edges > 0:
            total_distance = 0
            for i, j, w in self.nx_graph.edges(data=True):
                total_distance += w['weight']
                self.avg_people_distance = total_distance/n_edges
            return self.avg_people_distance
        return 0

    def update_avg_machine_distance(self, machine_pos=None):
        m_pos = machine_pos
        n_nodes = self.nx_graph.number_of_nodes()
        if self.edges_calculated and n_nodes > 0:
            total_distance_from_machine = 0
            for node, node_data in self.nx_graph.nodes(data=True):
                total_distance_from_machine += node.distance_from(m_pos)
            self.avg_machine_distance = total_distance_from_machine/n_nodes
            return self.avg_machine_distance
        return 0

    def get_average_clustering(self):
        # if self.edges_calculated:
        #     return nx.average_clustering(self.nx_graph, weight='weight')
        return 0

    def draw_nx_graph(self):
        labels = nx.get_edge_attributes(self.nx_graph, 'weight')
        pos = nx.get_node_attributes(self.nx_graph, 'pos')
        nx.draw(self.nx_graph, pos)
        nx.draw_networkx_edge_labels(self.nx_graph, pos, edge_labels=labels)

    def normalize_weight(self, weight):
        normalized = (weight - self.min_weight) / (self.max_weight - self.min_weight)
        if normalized is None or math.isnan(normalized):
            normalized = 1
        return normalized

    def draw_nodes(self, drawer, canvas, draw_type='cv', debug=False):
        color = (255, 255, 255)
        for node, node_data in self.nx_graph.nodes(data=True):
            if draw_type.lower() == 'cv':
                drawer.circle(canvas, (int(node.pos[0]), int(node.pos[1])), 3, color, 3)
            else:
                drawer.draw.circle(canvas, color=color, center=(int(node.pos[0]), int(node.pos[1])), radius=3, width=3)

    def draw_edges(self, drawer, canvas, draw_type='cv', debug=False):
        if self.edges_calculated:
            color = (0, 0, 255)
            thickness = 1
                # thickness = int((self.normalize_weight(w['weight'])+1) * 2)
            for i, j, w in self.nx_graph.edges(data=True):
                if draw_type.lower() == 'cv':
                    drawer.line(canvas, (int(i.pos[0]), int(i.pos[1])), (int(j.pos[0]), int(j.pos[1])), color, thickness)
                else:
                    drawer.draw.line(canvas, color=color, start_pos=(int(i.pos[0]), int(i.pos[1])), end_pos=(int(j.pos[0]), int(j.pos[1])), width=thickness)
                if debug:
                    print(f"thickness (max: {self.min_weight}, min: {self.max_weight}, Original: {w['weight']} Normalized: {thickness}")

    def draw_dist_from_machine(self, drawer, canvas, mx, my, draw_type='cv', debug=True):
        if draw_type.lower() == 'cv':
            drawer.circle(canvas, (int(mx), int(my)), 3, (255, 255, 255), 3)
        else:
            drawer.draw.circle(canvas, color=(255, 255, 255), center=(int(mx), int(my)), radius=3, width=3)
        thickness = 1
        color = (255, 0, 0)
        for node, node_data in self.nx_graph.nodes(data=True):
            if draw_type.lower() == 'cv':
                drawer.line(canvas, (int(node.pos[0]), int(node.pos[1])), (int(mx), int(my)), color, thickness)
            else:
                drawer.draw.line(canvas, color=color, start_pos=(int(node.pos[0]), int(node.pos[1])), end_pos=(int(mx), int(my)), width=thickness)

    def draw_debug(self, drawer, canvas, text_x=0, text_y=0, offset_x=20, offset_y=100, draw_type='cv', debug=True, prefix=""):
        nodes_data = ""
        for node in self.nx_graph.nodes():
            nodes_data = f"{nodes_data}, ({node.pos[0]:.2f}, {node.pos[1]:.2f})"
        nodes_data = f"[{nodes_data}]"
        edges_data = ""
        for i, j, w in self.nx_graph.edges(data=True):
            # edges_data = f"{edges_data}, ({i.pos[0]:.2f}, {i.pos[1]:.2f}, weight: {w['weight']:.2f}\n)"
            edges_data = f"{edges_data},{w['weight']:.2f}"
        edges_data = f"[{edges_data}]"
        text_x = int(text_x+offset_x)
        text_y = int(text_y+offset_y)

        nodes_str = f"Nodes {self.nx_graph.number_of_nodes()}: {nodes_data}"
        edges_str = f"Edges {self.nx_graph.number_of_edges()}: {edges_data}"
        data_str = f"Avg dist: {self.avg_people_distance:.2f} Avg_m: {self.avg_machine_distance:.2f}"
        color = (255, 255, 0)
        if draw_type.lower() == 'cv':
            drawer.putText(canvas, nodes_str, (text_x, text_y), 0, 0.4, color, 2)
            drawer.putText(canvas, edges_str, (text_x, text_y+20), 0, 0.4, color, 2)
            drawer.putText(canvas, data_str, (text_x, text_y+40), 0, 0.4, color, 2)
        else:
            canvas.blit(drawer.render(nodes_str, True, color), (text_x, text_y))
            canvas.blit(drawer.render(edges_str, True, color), (text_x, text_y+20))
            canvas.blit(drawer.render(data_str, True, color), (text_x, text_y+40))
        if debug:
            print(f"Camera {prefix:<2} - Nodes: {self.nx_graph.number_of_nodes():<3} Edges: {self.nx_graph.number_of_edges():<3}")

    # from people_graph import *
    # g = PeopleGraph()
    # g.add_node(Person(10, 10))
    # g.add_node(Person(0, 10))
    # g.add_node(Person(10, 10))
    # g.add_node(Person(13, 5))
    # g.calculate_edges()
    # g.draw_nx_graph()
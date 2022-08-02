import networkx as nx
import math
import numpy as np
import itertools
import matplotlib.pyplot as plt
import Constants

class Person:
    def __init__(self, x=-1, y=-1, z=-1, id=-1):
        self.id = id
        if z >= 0:
            self.pos = np.array([x, y, z])
        else:
            self.pos = np.array([x, y])

    def get_pos(self):
        return tuple(self.pos)

    def get_distance(self, pos):
        if self.pos.size != pos.size:
            print(f"Cannot calculate distance between 2D and 3D points")
        squared_dist = np.sum((self.pos-pos)**2, axis=0)
        return np.sqrt(squared_dist)
        
    def update_location(self, tracks):
        pass

    def draw_debug_data(self, cv2, frame):
        pass

class PeopleGraph:
    def __init__(self):
        self.nx_graph = nx.Graph()
        self.max_weight = -1
        self.min_weight = 9999
        self.edges_calculated = False
        self.avg_distance = -1
        self.avg_distance_from_machine = -1

    def init_graph(self):
        self.nx_graph = nx.Graph()
        self.max_weight = -1
        self.min_weight = 9999
        self.edges_calculated = False
        self.avg_distance = -1
        self.avg_distance_from_machine = -1

    def get_nodes(self):
        return self.nx_graph.nodes()

    def get_edges(self):
        return self.nx_graph.edges()

    def add_node(self, x, y, z):
        node = Person(x,y,z)
        self.nx_graph.add_node(node, pos=node.get_pos())
        return node.get_pos()

    def add_edge(self, from_node, to_node):
        w = from_node.get_distance(to_node.pos)
        self.nx_graph.add_edge(from_node, to_node, weight=w)
        return w

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

    def get_average_distance(self):
        if self.edges_calculated and self.nx_graph.number_of_nodes() > 0:
            sum_of_edges = 0
            for i, j, w in self.nx_graph.edges(data=True):
                sum_of_edges += w['weight']
                self.avg_distance = sum_of_edges/self.nx_graph.number_of_nodes()
            return self.avg_distance
        return 0

    def get_average_distance_from_machine(self, mx, my):
        if self.edges_calculated and self.nx_graph.number_of_nodes() > 0:
            total_distance_from_machine = 0
            for node, node_data in self.nx_graph.nodes(data=True):
                total_distance_from_machine += node.get_distance(np.array([mx, my]))
            self.avg_distance_from_machine = total_distance_from_machine/self.nx_graph.number_of_nodes()
            return self.avg_distance_from_machine
        return 0

    def get_average_clustering(self):
        # if self.edges_calculated:
        #     return nx.average_clustering(self.nx_graph, weight='weight')
        return 0

    def get_nx_graph(self):
        return self.nx_graph

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

    def cv_draw_nodes(self, cv2, canvas):
        for node, node_data in self.nx_graph.nodes(data=True):
            cv2.circle(canvas, (int(node.pos[0]), int(node.pos[1])), 3, (255, 255, 255), 3)

    def cv_draw_edges(self, cv2, canvas, debug=True):
        if self.edges_calculated:
            for i, j, w in self.nx_graph.edges(data=True):
                # thickness = int((self.normalize_weight(w['weight'])+1) * 2)
                thickness = 1
                cv2.line(canvas, (int(i.pos[0]), int(i.pos[1])), (int(j.pos[0]), int(j.pos[1])), (0, 0, 255), thickness)
                if debug:
                    print(f"thickness (max: {self.min_weight}, min: {self.max_weight}, Original: {w['weight']} Normalized: {thickness}")

    def cv_draw_dist_from_machine(self, cv2, canvas, mx, my, debug=True):
        cv2.circle(canvas, (int(mx), int(my)), 3, (255, 255, 255), 3)
        for node, node_data in self.nx_graph.nodes(data=True):
            thickness = 1
            cv2.line(canvas, (int(node.pos[0]), int(node.pos[1])), (int(mx), int(my)), (255, 0, 0), thickness)

    def cv_draw_debug(self, cv2, canvas, text_x=0, text_y=0, offset_x=20, offset_y=100, debug=True, prefix=""):
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
        cv2.putText(canvas, f"Nodes {self.nx_graph.number_of_nodes()}: {nodes_data}", (text_x, text_y), 0, 0.4, (255, 255, 0), 2)
        cv2.putText(canvas, f"Edges {self.nx_graph.number_of_edges()}: {edges_data}", (text_x, text_y+20), 0, 0.4, (255, 255, 0), 2)
        cv2.putText(canvas, f"Avg dist: {self.avg_distance:.2f} Avg_m: {self.avg_distance_from_machine:.2f}", (text_x, text_y+40), 0, 0.4, (255, 255, 0), 2)
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
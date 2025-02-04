from ..SwarmComponentMeta import SwarmComponentMeta
from .FrameBufferData import FrameBuffer
from ..Utils.utils import *
import datetime

MAX_HISTORY_SIZE = 10000

class SwarmManager(SwarmComponentMeta):
    def __init__(self, app_logger, ui_drawer, tasks_manager, arduino_manager=None, websocket_manager=None):
        super(SwarmManager, self).__init__(ui_drawer, tasks_manager, "SwarmManager", r'BehaviourConfig.yaml', self.update_config_data)
        self.arduino = arduino_manager.arduino
        self.app_logger = app_logger
        self.behaviors = None
        self.frame_buffer = FrameBuffer(buffer_size=60)
        self.machine_mode = 'normal'
        self.current_behavior = None
        self.last_behavior = None
        self.last_remote_command = None
        self.curr_behavior_name = "NONE"
        self.last_behavior_name = "NONE"
        self.last_behavior_sent_name = "NONE"
        self.last_behavior_sent_time = 0
        self.debug_lines = []
        self.websocket_manager = websocket_manager
    def update_config(self):
      super().update_config_from_file(self.app_logger, self.tag, self.config_filename, self.last_modified_time)
        
    def update_config_data(self, data, last_modified_time):
        self.config_data = data
        self.behaviors = self.config_data.get("behaviors", [])
        for b in self.behaviors: b['remote'] = False
        self.frame_buffer.buffer_size = self.config_data.get('buffer_size', 60)            
        self.machine_mode = self.config_data.get("machine_mode", 'normal')
        self.last_modified_time = last_modified_time      
    
    def update(self, cameras, debug=False, surfaces=None):
        remote_command, ws_id = self.websocket_manager.get_last_remote_command()
        debug = True
        text_debug = False
        # right_text_pos_orig = Point(right_text_pos.x, right_text_pos.y)
        # right_text_pos.y += self.ui_drawer.line_height*2.4
        self.frame_buffer.add_frame_data(cameras)
        action_updated = False
        remote_action = False
        # if self.frame_buffer.empty_frames > 0:
        #     return left_text_pos, right_text_pos
        for behavior in self.behaviors:
            try:
                all_criteria_met = self.check_behavior(behavior, {}, debug=True, surfaces=surfaces)
            except Exception as e:
                print(f"Error checking behavior {behavior.get('name', 'NONE')}: {e}")
                all_criteria_met = False
            # Let's just update the parameters without changing the behaviour
            if action_updated:
                continue
            name = behavior.get("name", "unknown")
            command = behavior.get("arduino_command", "")
            if remote_command is not None:
                if name == remote_command:
                    action_updated = True
                    remote_action = True
            else:
                if all_criteria_met:
                    action_updated = True
                    remote_action = False

            if action_updated:
                if text_debug:
                    print(f"Action updated: {name} ({command}) [{'REMOTE' if remote_action else ''}]")
                    print(f"\r\nNew ACTION: Running command {command} [{'REMOTE' if remote_action else ''}] from behavior {name}\n\r")
                cmd_sent = False
                if not remote_action:
                    # Debugging lines
                    dbg_vals = f"p: {self.frame_buffer.people_data.avg:.2f}, g: {self.frame_buffer.groups_data.avg:.2f}, p_d: {self.frame_buffer.distance_data.avg:.2f}, p_dm: {self.frame_buffer.machine_distance_data.avg:.2f}"
                    cmd_sent = self.arduino.send_command(command, debug=text_debug, dbg_vals=dbg_vals)
                else:
                    cmd_sent = self.arduino.send_command(command, debug=text_debug)

                if cmd_sent:
                    self.app_logger.critical(f"Command {command} [{'REMOTE' if remote_action else ''}] SENT")
                    behavior["last_executed_time"] = datetime.datetime.now()
                    self.last_behavior = self.current_behavior if self.current_behavior is not None else behavior
                    self.current_behavior = behavior
                    if remote_action and remote_command is not None:
                        behavior['remote'] = remote_action
                        self.last_remote_command = behavior
                        self.websocket_manager.pop_last_remote_command(ws_id)

        if self.current_behavior is None:
            self.curr_behavior_name = "NONE"
        else:
            self.curr_behavior_name = self.current_behavior.get('name', 'NONE').upper()
            self.curr_behavior_name = self.curr_behavior_name if not self.current_behavior.get('remote', False) else f"{self.curr_behavior_name} (REMOTE)"
        if self.last_behavior is None:
            self.last_behavior_name = "NONE"
        else:
            self.last_behavior_name = self.last_behavior.get('name', 'NONE').upper()
            self.last_behavior_name = self.last_behavior_name if not self.last_behavior.get('remote', False) else f"{self.last_behavior_name} (REMOTE)"
        b_color = (150, 150, 150) if self.curr_behavior_name == "None" else (255, 255, 0)

        last_time = self.last_behavior.get('last_executed_time', 0) if self.last_behavior is not None else ''
        curr_time = self.current_behavior.get('last_executed_time', 0) if self.last_behavior is not None else ''
        self.debug_lines.insert(0, {'text': f"Last: {self.last_behavior_name} at {last_time}", 'color': (255,0,0), 'side': 'right', 'spaces_after': 0})
        self.debug_lines.insert(0, {'text': f"Current: {self.curr_behavior_name} at {curr_time}", 'color': (255,0,0), 'side': 'right', 'spaces_after': 1})
        # right_text_pos_orig = self.ui_drawer.add_text_line(f"Current Behaviour: {self.curr_behavior_name}", (255, 0, 0), right_text_pos_orig, s_names=surfaces)
        self.debug_lines.insert(0, {'text': f"Behaviour Type: {self.machine_mode}", 'color': (255,0,0), 'side': 'right'})
        # right_text_pos_orig = self.ui_drawer.add_text_line(f"Behaviour Type: {self.machine_mode}", (255, 0, 0), right_text_pos_orig, s_names=surfaces)

        # left_text_pos = self.ui_drawer.add_text_line(f"Running Action {self.curr_behavior_name}", b_color, left_text_pos, s_names=surfaces)

        self.debug_lines.append({'text': f"Running Action {self.curr_behavior_name}", 'color': (255,100,100), 'side': 'left', 'spaces_after': 0})
        self.add_param_debug_line('People', self.frame_buffer.people_data, b_color)
        self.add_param_debug_line('Groups', self.frame_buffer.groups_data, b_color)
        self.add_param_debug_line('Groups Ratio', self.frame_buffer.groups_data, b_color)
        self.add_param_debug_line('P_Distance', self.frame_buffer.distance_data, b_color)
        self.add_param_debug_line('M_Distance', self.frame_buffer.machine_distance_data, b_color)
        return

    def add_param_debug_line(self, name, data, color):
        # left_text_pos = self.ui_drawer.add_text_line(
        #     f"{name} - avg: {data.avg:.2f}, minmax: [{data.min:.2f}, {data.max:.2f}], n: {data.non_zeroes}/{self.frame_buffer.size()}",
        #     color, left_text_pos, s_names=surfaces)
        self.debug_lines.append({'text': f"{name} - avg: {data.avg:.2f}, minmax: [{data.min:.2f}, {data.max:.2f}], n: {data.non_zeroes}/{self.frame_buffer.size()}",
                                 'color': color, 'side': 'left'})

    def serialize_datetime(self, dict_obj):
        try:
            dict_obj = dict_obj.copy()
            for k, v in dict_obj.items():
                if 'datetime' in dict_obj[k].__class__.__name__:
                    try:
                        dict_obj[k] = dict_obj.get(k, None).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        dict_obj[k] = ""
        except Exception as e:
            pass
        return dict_obj

    def get_swarm_data(self):
        data = {}
        data['frames_stats'] = self.frame_buffer.get_json()
        data['behavior_mode'] = self.machine_mode
        data['prev_last_command'] = self.last_behavior_name
        if self.last_remote_command is not None:
            data['last_remote_command'] = self.last_remote_command['name']
        if self.current_behavior is not None:
            send_update = False
            if self.curr_behavior_name != self.last_behavior_sent_name:
                send_update = True
            else:
                if self.current_behavior.get('last_executed_time', 0) != self.last_behavior_sent_time:
                    send_update = True
                    self.app_logger.critical(f"Sending behaviour update time: {self.current_behavior.get('last_executed_time', 0)} != {self.last_behavior.get('last_executed_time', 0)}")

            if send_update:
                data['current_behavior'] = serialize_datetime(self.current_behavior)
                data['last_command'] = self.curr_behavior_name
                self.last_behavior_sent_name = self.curr_behavior_name
                self.last_behavior_sent_time = self.current_behavior.get('last_executed_time', 0)
                # self.app_logger.critical(f"Sending behaviour update {data}")
        behaviors_data = []
        for behavior in self.behaviors:
            copy = serialize_datetime(behavior)
            behaviors_data.append(copy)
        data['behaviors_data'] = behaviors_data
        return data

    def draw(self, left_text_pos, right_text_pos, debug=False, surfaces=None):
        for i in range(0, len(self.debug_lines)):
            line = self.debug_lines[i]
            text_pos = right_text_pos if line['side'] == 'right' else left_text_pos
            text_pos = self.ui_drawer.add_text_line(line['text'], line['color'], text_pos, s_names=surfaces)
            if i < len(self.debug_lines)-1:
                text_pos.y += self.ui_drawer.line_height * self.debug_lines[i+1].get('spaces_before', 0)
            text_pos.y += self.ui_drawer.line_height * line.get('spaces_after', 0)
        self.debug_lines.clear()

    def check_behavior(self, behavior, curr_behavior, debug=False, surfaces=None):
        # right_text_pos_orig = Point(right_text_pos.x, right_text_pos.y)
        # right_text_pos.y += self.ui_drawer.line_height
        behavior_type = behavior.get('type', 'normal')
        # print(f"Checking Behaviour: {behavior}")
        enabled = behavior.get("enabled", True)        
        if self.machine_mode != behavior_type:
            enabled = False
        total_enabled_criteria = 0
        criteria_met = 0
        name = behavior.get('name', 'unknown')
        curr_behavior_name = curr_behavior.get('name', 'None')
        is_running = (name == curr_behavior_name)
        inactive_color = (140, 0, 140)
        active_color = (255, 200, 0)
        if debug:
            color = active_color if is_running else inactive_color
            prefix = 'x'
            postfix = ''
            if enabled:
                prefix = '-'
            else:
                if self.machine_mode != behavior_type:
                    postfix = '(type disabled)'
                else:
                    postfix = '(disabled)'
            if name == curr_behavior_name:
                prefix = '>'
                postfix = '(running)'
        else:
            if not enabled:
                return False

        parameters = behavior.get("parameters", [])
        for param_name in parameters:
            try:
                criterium_met, is_enabled = self.check_parameter(parameters[param_name], param_name, behavior, is_running, self.frame_buffer, inactive_color, active_color, debug=debug, surfaces=surfaces)
                criteria_met += 1 if criterium_met else 0
                total_enabled_criteria += 1 if is_enabled else 0
            except Exception as e:
                print(f"Error checking parameter {param_name}: {e}")
                return False
        # right_text_pos.y += self.ui_drawer.line_height
        if debug:
            try:
                last_executed_string = behavior.get('last_executed_time', None).strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                last_executed_string = "Never"
            self.debug_lines.insert(len(self.debug_lines)-total_enabled_criteria, {'text': f"{prefix} {name.upper()} {postfix} {criteria_met}/{total_enabled_criteria} ({last_executed_string})", 'color': color, 'side': 'right', 'spaces_before': 1})
            # self.debug_lines[len(self.debug_lines)-1]['space_after'] = 1
            # self.debug_lines += param_debug_lines
            # self.ui_drawer.add_text_line(f"{prefix} {name.upper()} {postfix} {criteria_met}/{total_enabled_criteria}", color, right_text_pos_orig, s_names=surfaces)
        
        if not enabled:
            return False        
        return criteria_met == total_enabled_criteria
      
      
    def check_parameter(self, param, param_name, behavior, is_running, frame_buffer, inactive_color, active_color, debug=False, surfaces=None):
        param_debug_lines = []
        param_name = param_name.lower()
        enabled = param.get("enabled", True)
        if not enabled:
            return False, enabled
        value = -1
        if param_name == "time":
            timeout = param.get("timeout", 300)
            last_time = behavior.get("last_executed_time", None)
            if last_time is None:
                elapsed = 0
                self.app_logger.critical("Starting default behaviour")
                behavior["last_executed_time"] = datetime.datetime.now()
            else:
                elapsed = (datetime.datetime.now() - last_time).seconds

            if debug:
                color = active_color if is_running else inactive_color
                # text_pos = self.ui_drawer.add_text_line(f"{param_name}: {elapsed}/{timeout}", color, text_pos, surfaces)
                self.debug_lines.append({'text': f"{param_name}: {elapsed}/{timeout}", 'color': color, 'side': 'right'})
            if elapsed >= timeout:
                return True, enabled
            return False, enabled
        elif param_name == "people":
            value = frame_buffer.people_data.avg
        elif param_name == "groups":
            value = frame_buffer.groups_data.avg
        elif param_name == "people_in_groups_ratio":
            value = frame_buffer.group_ratio
        elif param_name == "avg_distance_between_people":
            value = frame_buffer.distance_data.avg
        elif param_name == "avg_distance_from_machine":
            value = frame_buffer.machine_distance_data.avg

        min_value = param.get('min', 0)
        max_value = param.get('max', 0)
        criteria_met = min_value <= value <= max_value
        if is_running:
            color = active_color
        else:
            if criteria_met:
                color = (inactive_color[0] * 1.5, inactive_color[1] * 1.5, inactive_color[2] * 1.5)
            else:
                color = inactive_color
        # text_pos = self.ui_drawer.add_text_line(f"  {param_name}: {min_value} < {value:.2f} < {max_value}", color, text_pos, s_names=surfaces)
        self.debug_lines.append({'text': f"  {param_name}: {min_value} < {value:.2f} < {max_value}", 'color': color, 'side': 'right'})
        # self.debug_lines += param_debug_lines
        return criteria_met, enabled

  
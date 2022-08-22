from ..SwarmComponentMeta import SwarmComponentMeta
from .FrameBufferData import FrameBuffer
from ..Utils.utils import Point
import datetime

class SwarmManager(SwarmComponentMeta):
    def __init__(self, logger, tasks_manager, arduino_manager=None):
        super(SwarmManager, self).__init__(logger, tasks_manager, "SwarmManager", r'./Config/BehaviourConfig.yaml', self.update_config_data)
        self.arduino = arduino_manager.arduino
        self.behaviors = None
        self.frame_buffer = FrameBuffer(buffer_size=60)
        self.machine_mode = 'normal'
        self.current_behavior = None
    
    def update_config(self):
      super().update_config_from_file(self.tag, self.config_filename, self.last_modified_time)
        
    def update_config_data(self, data, last_modified_time):
        self.config_data = data
        self.behaviors = self.config_data.get("behaviors", [])
        self.frame_buffer.buffer_size = self.config_data.get('buffer_size', 60)            
        self.machine_mode = self.config_data.get("machine_mode", 'normal')
        self.last_modified_time = last_modified_time      
    
    def update(self, cameras, left_text_pos, right_text_pos, debug=False, surfaces=None):
        if debug:
            print(f"Updating Swarm Manager")
        debug = True
        text_debug = False
        right_text_pos_orig = Point(right_text_pos.x, right_text_pos.y)
        right_text_pos.y += self.logger.line_height*1.5
        self.frame_buffer.add_frame_data(cameras)
        action_updated = False
        # if self.frame_buffer.empty_frames > 0:
        #     return left_text_pos, right_text_pos
        for behavior in self.behaviors:
            try:
                all_criteria_met = self.check_behavior(behavior, {}, right_text_pos, debug=True, surfaces=surfaces)
            except Exception as e:
                print(f"Error checking behavior {behavior.get('name', 'NONE')}: {e}")
                all_criteria_met = False
            if not action_updated:
                if all_criteria_met:
                    action_updated = True
                    self.current_behavior = behavior
                    name = self.current_behavior.get("name", "unknown")
                    command = self.current_behavior.get("arduino_command", "")
                    if text_debug:
                        print(f"Action updated: {name} ({command})")
                        print(f"\r\nNew ACTION: Running command {command} from behavior {name}\n\r")
                    # Debugging lines
                    dbg_vals = f"p: {self.frame_buffer.people_data.avg:.2f}, g: {self.frame_buffer.groups_data.avg:.2f}, p_d: {self.frame_buffer.distance_data.avg:.2f}, p_dm: {self.frame_buffer.machine_distance_data.avg:.2f}"
                    self.arduino.send_command(command, debug=text_debug, dbg_vals=dbg_vals)
                    behavior["last_executed_time"] = datetime.datetime.now()
                    # We found the command to execute so we can stop here
                    if not debug:
                        return
        curr_behavior_name = self.current_behavior.get('name', 'NONE').upper() if self.current_behavior is not None else '-'
        right_text_pos_orig = self.logger.add_text_line(f"Current Behaviour: {curr_behavior_name}", (255, 0, 0), right_text_pos_orig, s_names=surfaces)
        right_text_pos_orig = self.logger.add_text_line(f"Behaviour Type: {self.machine_mode}", (255, 0, 0), right_text_pos_orig, s_names=surfaces)
        b_color = (150, 150, 150) if curr_behavior_name == "None" else (255, 255, 0)
        left_text_pos = self.logger.add_text_line(f"Running Action {curr_behavior_name}", b_color, left_text_pos, s_names=surfaces)
        data = self.frame_buffer.people_data
        left_text_pos = self.logger.add_text_line(
            f"People - avg: {data.avg:.2f}, minmax: [{data.min:.2f}, {data.max:.2f}], n: {data.non_zeroes}/{self.frame_buffer.size()}",
            b_color, left_text_pos, s_names=surfaces)
        data = self.frame_buffer.groups_data
        left_text_pos = self.logger.add_text_line(
            f"Groups - avg: {data.avg:.2f}, minmax: [{data.min:.2f}, {data.max:.2f}], n: {data.non_zeroes}/{self.frame_buffer.size()}",
            b_color, left_text_pos, s_names=surfaces)
        left_text_pos = self.logger.add_text_line(
            f"Groups Ratio- avg: {self.frame_buffer.group_ratio:.2f}, minmax: [{data.min:.2f}, {data.max:.2f}], n: {data.non_zeroes}/{self.frame_buffer.size()}",
            b_color, left_text_pos, s_names=surfaces)
        data = self.frame_buffer.distance_data
        left_text_pos = self.logger.add_text_line(
            f"P_Distance - avg: {data.avg:.2f}, minmax: [{data.min:.2f}, {data.max:.2f}], n: {data.non_zeroes}/{self.frame_buffer.size()}",
            b_color, left_text_pos, s_names=surfaces)
        data = self.frame_buffer.machine_distance_data
        left_text_pos = self.logger.add_text_line(
            f"M_Distance - avg: {data.avg:.2f}, minmax: [{data.min:.2f}, {data.max:.2f}], n: {data.non_zeroes}/{self.frame_buffer.size()}",
            b_color, left_text_pos, s_names=surfaces)
        return
    
    
    def check_behavior(self, behavior, curr_behavior, right_text_pos, debug=False, surfaces=None):
        right_text_pos_orig = Point(right_text_pos.x, right_text_pos.y)
        right_text_pos.y += self.logger.line_height
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
                criterium_met, is_enabled = self.check_parameter(parameters[param_name], param_name, behavior, is_running, self.frame_buffer, right_text_pos, inactive_color, active_color, debug=debug, surfaces=surfaces)
                criteria_met += 1 if criterium_met else 0
                total_enabled_criteria += 1 if is_enabled else 0
            except Exception as e:
                print(f"Error checking parameter {param_name}: {e}")
                return False
        right_text_pos.y += self.logger.line_height
        if debug:
            self.logger.add_text_line(f"{prefix} {name.upper()} {postfix} {criteria_met}/{total_enabled_criteria}", color, right_text_pos_orig, s_names=surfaces)
        
        if not enabled:
            return False        
        return criteria_met == total_enabled_criteria
      
      
    def check_parameter(self, param, param_name, behavior, is_running, frame_buffer, text_pos, inactive_color, active_color, debug=False, surfaces=None):
        param_name = param_name.lower()
        enabled = param.get("enabled", True)
        if not enabled:
            return False, enabled
        value = -1
        if param_name == "time":
            last_time = behavior.get("last_executed_time", None)
            if last_time is None:
                return True, enabled
            timeout = param.get("timeout", 300)
            elapsed = (datetime.datetime.now() - last_time).seconds
            if debug:
                if is_running:
                    text_pos = self.logger.add_text_line(f"{param_name}: {elapsed}/{timeout}", active_color, text_pos, surfaces)
                else:
                    text_pos = self.logger.add_text_line(f"  {param_name}: {elapsed}/{timeout}", inactive_color, text_pos, surfaces)
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
        text_pos = self.logger.add_text_line(f"  {param_name}: {min_value} < {value:.2f} < {max_value}", color, text_pos, s_names=surfaces)
        return criteria_met, enabled
    
    def draw(self, *args, **kwargs):
      pass
  
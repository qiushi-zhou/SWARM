import os
import oyaml as yaml
class SwarmComponentMeta:
    def __init__(self, logger=None, tag="SwarmComponent", config_filename=None, update_config_data_callback=None):
        self.logger = logger
        self.tag = tag
        self.enabled = True
        self.config_filename = config_filename
        self.config_data = None
        self.last_modified_time = -1
        self.update_config_data_callback = update_config_data_callback if update_config_data_callback is not None else self.update_config_data
    
    def init():
      pass
    
    def update_config(self):
      pass
    
    def update_config_from_file(self, tag, file_path, last_modified_time):
      try:
        if last_modified_time < os.path.getmtime(file_path):
          with open(file_path) as file:
              self.update_config_data_callback(yaml.load(file, Loader=yaml.FullLoader), os.path.getmtime(file_path))
      except Exception as e:
          print(f"Error opening {tag} behavior config file: {e}")
    
    def update_config_data(self, config_data, last_modified_time):
      print(f"Warning! No update_config_data set for {self.tag}")
      pass
    
    def update(self):
      pass
    
    def draw(self):
      pass
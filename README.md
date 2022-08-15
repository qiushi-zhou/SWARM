# SWARM Management Instructions

## Overview
The program is made up of three main components with relative configuration files:
- Cameras. Config File: `CamerasConfig.yaml`
- People Graph and tracking. File: `BehaviourConfig.yaml`
- Arduino. Config File: `ArduinoConfig.yaml`

### How to run
- Main Program: From the top bar near the 'play' button, select 'main' and press play
- Movements testing program:  From the top bar near the 'play' button, select 'serial_testing' and press play

### How to stop
- Preferred: Press the "stop" button multiple times (to make sure all background activites are stopped)
- OR: Press CTRL+C on the keyboard while on the console


## Flows
## Main Program
1. When the program starts it immediately reads the configuration files and initializes the three main components:
    - Cameras initialization
    - Behavior initialization
    - Arduino initialization
    1a. If the Arduino cannot be found on the predefined COM port `COM4` the program will present the user with a list of available COM ports to try
        ```
        MACHINE NOT OPERATIONAL
        Initializing Arduino...
        
        Select Arduino port:
        -1: Leave Arduino disconnected (debug)
        0: COM3
        ```
    Just type the choice's number and press Enter
2. The program will then open a window to display the cameras with the openpose visualization overlayed. There is also some debugging information to easily diagnose any issue with the machine, with Arduino or with the behaviors management
3. The general loop works roughly this way:
    - Update the status of Arduino to make sure it's active and ready to receive commands
    - Track people's location and poses:
        - The center of a person is the centroid of the bounding box, it usually falls around the hips of each person
    - Update the graph representing people' locations and movements according to people's location on the screeb
        - Update the number of people in the scene
        - The distance between each pair of people
        - The number of detected groups according to an edge threshold
        - The distance of each person from the machine
        - Each camera has its own graph, edge threshold and machine's position - this is to ensure that the program works with an arbitrary number of cameras
    - Update the moving average values:
        - To avoid spikes in values due to the unreliable tracking, the data is smoothed across 60 frames (roughly 2-3 seconds of data). So it will take around that amount time for changes in the crowd to potentially trigger a movement
    - Update the current action according to each behavior's parameters:
        - A behavior has to meet ALL **enabled** parameters to be triggered
        - Even if all parameters' criteria are met, the behavior it will NOT run if `enabled` is set to `true` in the configuration file
        - Even if all criteria are met and the behavior is enabled, it will not run if the behavior `type` does not match the current machine's behavior type
    - 

### Movements testing program
1. When the program starts it will try to initialize the Arduino on the predefined COM port
    1a. If the Arduino cannot be found on the predefined COM port `COM4` the program will present the user with a list of available COM ports to try
    ```
    MACHINE NOT OPERATIONAL
    Initializing Arduino...
    
    Select Arduino port:
    -1: Leave Arduino disconnected (debug)
    0: COM3
    ```
    Just type the choice's number and press Enter
2. The user is then presented with a helper menu and a  list of options to choose from:
    ```
    Select a command to send:
    0 - breathe   :$run,breathe,0#
    1 - undulate  :$run,undulate,0#
    2 - glitch    :$run,glitch,0#
    3 - quiver    :$run,quiver,0#
    4 - default   :$run,default,0#
    5 - stop      :$stop#
    6 - runcomp   :$run,runcomp,0#
    
    a - all in a loop
    
    u - update arduino's status
    q - exit
    Update: AUTO
    ```
    Same as before: type the choice's number and press Enter
3. When the Arduino sends back the "movement completed" feedback, the program will prompt the user with the above menu
4. Run all the tests you need and either


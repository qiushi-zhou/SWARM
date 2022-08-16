#!/bin/bash
eval "$(conda shell.bash hook)"
conda activate openpose
# Stop all previous instances
for pid in $(ps -ef | grep "main.py" | awk '{print $2}'); do sudo kill -9 $pid; done
python3 main.py 

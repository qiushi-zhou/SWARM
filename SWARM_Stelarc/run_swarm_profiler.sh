#!/bin/bash
eval "$(conda shell.bash hook)"
conda activate openpose
python3 -m cProfile -o profile.prof -s time main.py 
python3 -m snakeviz ./profile.prof
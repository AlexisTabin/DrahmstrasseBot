#!/bin/bash

if [ -f "/home/pi/miniconda3/etc/profile.d/conda.sh" ]; then
    . "/home/pi/miniconda3/etc/profile.d/conda.sh"
    CONDA_CHANGEPS1=false conda activate py36
fi
. /home/pi/miniconda3/bin/activate py36
cd  ~/Documents/DrahmstrasseBot/
git pull
python3 drahmbot.py

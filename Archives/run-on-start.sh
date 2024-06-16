#!/bin/sh
if [ -f "/home/alexis/miniconda3/etc/profile.d/conda.sh" ]; then
    . "/home/alexis/miniconda3/etc/profile.d/conda.sh"
    CONDA_CHANGEPS1=false conda activate drahmstrassebot
fi
conda activate drahmstrassebot
cd  ~/Documents/DrahmstrasseBot/
python3 drahmbot.py

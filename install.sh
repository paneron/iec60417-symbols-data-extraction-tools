#!/bin/bash

# sudo apt-get update -y

project_dir=`pwd`

python3 -m venv ${project_dir}/venv

source ${project_dir}/venv/bin/activate

pip3 install --upgrade pip
pip3 install -r ${project_dir}/requirements.txt

cp ${project_dir}/config.py.sample ${project_dir}/config.py
cp ${project_dir}/run.sh.sample ${project_dir}/run.sh
chmod +x ${project_dir}/run.sh

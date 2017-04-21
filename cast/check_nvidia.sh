#!/bin/bash

statfile="/tmp/nvidiastat"

nvidia-smi dmon -c 1 >$statfile

titles=( $(head -n 1 $statfile) )
values=( $(tail -n 1 $statfile) )

status="${titles[2]}=${values[1]}|${titles[3]}=${values[2]}|${titles[4]}=${values[3]}|${titles[5]}=${values[4]}|${titles[6]}=${values[5]}|${titles[7]}=${values[6]}|${titles[8]}=${values[7]}|${titles[9]}=${values[8]}"
name=nvidia_gpu${values[0]}
echo "0 $name $status - OK $status"


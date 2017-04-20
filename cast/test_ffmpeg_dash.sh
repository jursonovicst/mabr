#!/bin/bash

name="ch02"
dst="./output/$name"


trap ctrl_c INT

function ctrl_c() {
    rm -rf $dst
}

mkdir -p $dst

ffmpeg -re -i big_buck_bunny_1080p_h264.mov -vcodec h264_nvenc -b:v 3.5M -f dash -min_seg_duration 1000 -use_template 1 -use_timeline 0 -init_seg_name $name-\$RepresentationID\$-init.mp4 -media_seg_name $name-\$RepresentationID\$-\$Number\$.mp4 $dst/$name.mpd




#fmpeg -i big_buck_bunny_1080p_h264.mov -vcodec nvenc -b:v 3.5M -acodec copy /tmp/test3.5.mp4 -vcodec nvenc -b:v 6M -acodec copy /tmp/test6.mp4 -vcodec nvenc -b:v 9M -acodec copy /tmp/test9.mp4


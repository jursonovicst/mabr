#!/bin/bash

cwd=$(pwd)
cd ~/ffmpeg
make clean
./configure \
  --enable-shared \
  --disable-debug \
  --enable-avresample \
  --enable-gpl \
  --enable-libass \
  --enable-libfdk-aac \
  --enable-libmp3lame \
  --enable-libfreetype \
  --enable-libtheora \
  --enable-libvorbis \
  --enable-libx264 \
  --enable-nvenc \
  --enable-cuda \
  --enable-cuvid \
  --enable-libnpp \
  --extra-cflags=-I../Video_Codec_SDK/Samples/common/inc \
  --extra-ldflags=-L../Video_Codec_SDK/Samples/common/lib \
  --extra-ldflags=-L/usr/lib/nvidia-375 \
  --enable-nonfree
make -j

read -p "Should I install it? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
  sudo make install
  hash -r
fi

cd $cwd


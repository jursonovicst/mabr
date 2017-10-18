# mabr/cast

## ffmpeg/

The default DASH muxer in ffmpeg does not allow to specify the minBufferTime value in the MPD. Because m2u does need some time, till all slices are received via multicast, the player must have some delay by fetching the fragments. This can be controlled by increasing the buffer time (or suggestedPresentationDelay).

Use the dashenc.patch to add this feature (tested with ffmpeg n3.3.2)


## ch02.service

Sample service file to allow simulating live streams by looping a file indefinetely. A wallclock timestamp is added to the video as an overlay text before encoding.


## check_nvidia.sh

Locak checkmk script to check the load on an nvidia GPU (for enc/dec acceleration).

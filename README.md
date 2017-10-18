# mabr

A proof of concept implementation of an mABR protocol for learning purposes.


## u2m.py and u2m/

A component, which receives an MPEG-DASH stream, encapsulates into RTP/multicast, and puts on the network.


## m2u.py and m2u/

A component, which provides an MPEG-DASH interface to a streamin player, and provides the live stream via HTTP passthrough or multicast delivery. 


## Architecture

![alt text](https://github.com/jursonovicst/mabr/raw/master/docs/arch.png "Architecture")


## Stream links

http://24x7dash-i.akamaihd.net/dash/live/900080/dash-demo/dash.mpd

http://irtdashreference-i.akamaihd.net/dash/live/901161/bfs/manifestARD.mpd


## For later consideration

[packet pacing](https://fasterdata.es.net/assets/Papers-and-Publications/100G-Tuning-TechEx2016.tierney.pdf)

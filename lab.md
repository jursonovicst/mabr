DNS records in dnsmasq
```
address=/generic-raspi/192.168.0.19
address=/dash-test01/192.168.0.13
address=/harmonic.dash-test02/192.168.0.20
address=/mabr-origin.dash-test02/192.168.0.20
address=/harmonic/192.168.0.11
```

**Client PCs should use DHCP to acquire IP address, but use the following DNS server: 192.168.0.13**

| Stream | via origin | via CDN | via m2u |
|---|---|---|---|
|4k |http://harmonic/Content/DASH/Live/Channel(4K)/manifest.mpd|http://harmonic.dash-test02/Content/DASH/Live/Channel(4K)/manifest.mpd|http://generic-raspi/Content/DASH/Live/Channel(4K)/manifest.mpd|

import m2u

import logging
import argparse
import time
import socket

import sys, traceback



parser = argparse.ArgumentParser(description='...')
parser.add_argument('--log', help='log file, use - for stdout [default: %(default)s]', default="-")
parser.add_argument('--severity', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Log severity [default: %(default)s]', default="INFO")
parser.add_argument('--proxy', help='HTTP proxy for stream ingest', default="")
parser.add_argument('--bind', help='bind HTTP server [default: %(default)s]', default="0.0.0.0")
parser.add_argument('--bindmulticast', help='bind multicast to an interface [default: %(default)s]', default=socket.gethostbyname_ex(socket.gethostname())[2][0])
parser.add_argument('--port', type=int, help='TCP port to listen on [default: %(default)s]', default="80")

parser.add_argument('CONFIG', type=argparse.FileType('r'), nargs='+', help='Configs to intercept')
args = parser.parse_args()

if args.log != "-":
  logging.basicConfig(filename=args.log)
logging.basicConfig(level=getattr(logging, args.severity.upper(), None))


if __name__ == '__main__':

    dashproxy = None
    try:
        logging.info("Starting...")
        dashproxy = m2u.DASHProxy(logging.getLogger("DASHProxy"), args.bind, args.port, args.CONFIG, args.proxy, args.bindmulticast)

        #this will block
        dashproxy.serve_requests()


    except KeyboardInterrupt:
        logging.info("received interrupt signal...")
    except Exception as e:
        logging.warning("oops: '%s', systemd should respawn me..." % e.message)
        logging.debug(traceback.format_exc())

    dashproxy.stop()


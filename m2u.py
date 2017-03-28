import m2u

import logging
import argparse
import time

parser = argparse.ArgumentParser(description='...')
parser.add_argument('--log', help='log file, use - for stdout [default: %(default)s]', default="-")
parser.add_argument('--severity', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Log severity [default: %(default)s]', default="INFO")
parser.add_argument('--m2u', help='m2u to use, use "" for no m2u [default: ""', default="")
parser.add_argument('--memcached', help='memcache to use, provide IP:PORT or UNIX socket path [default: %(default)s]', default="127.0.0.1:11211")
parser.add_argument('--proxy', help='HTTP proxy for stream ingest, use - for None [default: %(default)s]', default="")
parser.add_argument('--ip', help='IP address to listen on [default: ""', default="0.0.0.0")
parser.add_argument('--port', type=int, help='TCP port to listen on [default: ""', default="80")

parser.add_argument('CONFIG', type=argparse.FileType('r'), nargs='+', help='Configs to intercept')
args = parser.parse_args()

if args.log != "-":
  logging.basicConfig(filename=args.log)
logging.basicConfig(level=getattr(logging, args.severity.upper(), None))


if __name__ == '__main__':


    run = True
    p = None
    while run:
        try:
            p = m2u.DASHProxy(name="Test", args=(logging, args.ip, args.port, args.CONFIG, args.memcached, args.proxy))
            p.start()

            # This will block
            p.join()
        except KeyboardInterrupt:
            run = False
        except Exception as e:
            logging.warning("oops: '%s', respawn in 10 sec..." % e.message)
            time.sleep(10)

        finally:
            # Respawn...
            if p is not None:
                p.stop()

    logging.info("...exit")

import u2m

import logging
import argparse

parser = argparse.ArgumentParser(description='...')
parser.add_argument('--log', help='log file, use - for stdout [default: %(default)s]', default="-")
parser.add_argument('--severity', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Log severity [default: %(default)s]', default="INFO")
parser.add_argument('--proxy', help='proxy to use, use "" for no proxy [default: ""', default="")
parser.add_argument('mpd', help='mpd file to open')
args = parser.parse_args()

if args.log != "-":
  logging.basicConfig(filename=args.log)
logging.basicConfig(level=getattr(logging, args.severity.upper(), None))


if __name__ == '__main__':
    x=None
    try:
        x = u2m.U2M(args.mpd, args.proxy)

        logging.info("In progress...")
        x.run() #this will block till all threads finishes...
    except Exception as e:
        logging.error("oops: " + e.message)
    except KeyboardInterrupt:
        pass
    finally:
        x.cancel()
        logging.info("...exit")

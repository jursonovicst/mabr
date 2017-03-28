import u2m

import logging
import argparse
import time

parser = argparse.ArgumentParser(description='...')
parser.add_argument('--log', help='log file, use - for stdout [default: %(default)s]', default="-")
parser.add_argument('--proxy', help='HTTP proxy for stream ingest', default="")
parser.add_argument('--severity', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='log level [default: %(default)s]', default="INFO")
parser.add_argument('CONFIG', type=argparse.FileType('r'), help='config file')
args = parser.parse_args()

if args.log != "-":
  logging.basicConfig(filename=args.log)
logging.basicConfig(level=getattr(logging, args.severity.upper(), None))


if __name__ == '__main__':

    run = True
    mpd = u2m.MPDParser(args.proxy, logging, args.CONFIG)
    while run:
        try:
            mpd.fetch()

            # this will block
            mpd.join()
        except KeyboardInterrupt:
            run = False
        except Exception as e:
            logging.warning("Oops (" + e.message + "), respawn in 10 sec...")
            time.sleep(10)
        finally:
            mpd.stop()

    logging.info("...exit")

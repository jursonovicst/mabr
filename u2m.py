import u2m
import logging
import argparse
import traceback

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

    mpd = None
    try:
        mpd = u2m.MPDParser(args.proxy, logging.getLogger('MPDParser'), args.CONFIG)
        mpd.fetch()

        # this will block
        mpd.join()
    except KeyboardInterrupt:
        logging.info("received interrupt signal...")
    except Exception as e:
        logging.warning("Oops (%s), systemd should respawn me..." % str(e))
        logging.debug(traceback.format_exc())

    if mpd is not None:
        mpd.stop()

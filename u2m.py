import u2m

import logging
import argparse
import ConfigParser
import time

parser = argparse.ArgumentParser(description='...')
parser.add_argument('--log', help='log file, use - for stdout [default: %(default)s]', default="-")
parser.add_argument('--proxy', help='HTTP proxy for stream ingest, use - for None [default: %(default)s]', default="")
parser.add_argument('--severity', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Log severity [default: %(default)s]', default="INFO")
parser.add_argument('CONFIG', type=argparse.FileType('r'), help='Config to intercept')
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
            logging.warning("oops (" + e.message + "), respawn in 10 sec...")
            time.sleep(10)
        # except (ParseError, TypeError, urllib2.HTTPError) as err:
            # logging.error("oops: " + str(err))
        #except Exception as e:
        #    logging.error("oops ("+type(e).__name__+"):'" + e.args + "', respawn...")
        finally:
            mpd.stop()

    logging.info("...exit")

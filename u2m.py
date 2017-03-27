import u2m

import logging
import argparse
import ConfigParser

parser = argparse.ArgumentParser(description='...')
parser.add_argument('--log', help='log file, use - for stdout [default: %(default)s]', default="-")
parser.add_argument('--proxy', help='HTTP proxy for stream ingest, use - for None [default: %(default)s]', default="")
parser.add_argument('--severity', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Log severity [default: %(default)s]', default="INFO")
parser.add_argument('--config', type=argparse.FileType('r'), help='configfile to  [default:  %(default)', required=True)
parser.add_argument('mpd', help='mpd file to open')
args = parser.parse_args()

if args.log != "-":
  logging.basicConfig(filename=args.log)
logging.basicConfig(level=getattr(logging, args.severity.upper(), None))


if __name__ == '__main__':

    config = ConfigParser.RawConfigParser()
    config.readfp(args.config)

    run = True
    mpd = None
    while run:
        try:
            mpd = u2m.MPDParser(args.mpd, args.proxy, logging, config)
            mpd.fetch()

            #this will block
            mpd.join()
        except KeyboardInterrupt:
            run = False
#        except Exception as e:
#            logging.warning("oops: '%s', respawn..." % e.message)
        # except (ParseError, TypeError, urllib2.HTTPError) as err:
            # logging.error("oops: " + str(err))
        # except Exception as e:
            # logging.error("oops ("+type(e).__name__+"):'" + e.args + "'")
        finally:
            if mpd is not None:
                mpd.stop()

    logging.info("...exit")

import u2m

import logging
import argparse
from xml.etree.ElementTree import ParseError
import ConfigParser
import urllib2

parser = argparse.ArgumentParser(description='...')
parser.add_argument('--log', help='log file, use - for stdout [default: %(default)s]', default="-")
parser.add_argument('--severity', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Log severity [default: %(default)s]', default="INFO")
parser.add_argument('--proxy', help='proxy to use, use "" for no proxy [default: ""', default="")
parser.add_argument('--config', type=argparse.FileType('r'), help='configfile to  [default:  %(default)', required=True)
parser.add_argument('mpd', help='mpd file to open')
args = parser.parse_args()

if args.log != "-":
  logging.basicConfig(filename=args.log)
logging.basicConfig(level=getattr(logging, args.severity.upper(), None))



if __name__ == '__main__':

    x=None
    try:
        config = ConfigParser.RawConfigParser()
        config.readfp(args.config)

        x = u2m.MPDParser(args.mpd, args.proxy, logging, config)

        logging.info("In progress...")
        x.run() #this will block till all threads finishes...
#    except (ParseError, TypeError, urllib2.HTTPError) as err:
    #        logging.error("oops: " + str(err))
        #    except Exception as e:
    #        logging.error("oops ("+type(e).__name__+"):'" + e.args + "'")

    except KeyboardInterrupt:
        pass
    finally:
        x.cancel()
        logging.info("...exit")

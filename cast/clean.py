import argparse
import logging
import os
import time
from stat import S_ISREG, ST_CTIME, ST_MODE

parser = argparse.ArgumentParser(description='...')
parser.add_argument('--log', help='log file, use - for stdout [default: %(default)s]', default="-")
parser.add_argument('--severity', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='log level [default: %(default)s]', default="INFO")
parser.add_argument('--retention', type=int, help='Retention time in sec [default: %(default)s]', default=600)
parser.add_argument('DIRECTORY', nargs='+', help='directory in which old segments are removed')
args = parser.parse_args()

if args.log != "-":
    logging.basicConfig(filename=args.log)
logging.basicConfig(level=getattr(logging, args.severity.upper(), None))



if __name__ == '__main__':

    for dirpath in args.DIRECTORY:

        # check arguments
        if not os.path.isdir(dirpath):
            logging.warning("Argument '%s' is not a directory, skipping." % dirpath)
            continue

        # get all entries in the directory w/ stats
        entries = (os.path.join(dirpath, fn) for fn in os.listdir(dirpath))
        entries = ((os.stat(path), path) for path in entries)

        # leave only regular files, insert creation date
        entries = ((stat[ST_CTIME], path)
                   for stat, path in entries if S_ISREG(stat[ST_MODE]))

        now = time.time()
        for cdate, path in sorted(entries):
            if cdate < now - args.retention:
                logging.info("File '%s' is expired (age is %ds), removing." % (path, now - cdate))
                try:
                    os.remove(path)
                except Exception as e:
                    logging.error("Oops: %s, skipping." % str(e))

            else:
                logging.debug("File '%s' is not yet expired (age is %ds), skipping." % (path, now - cdate))


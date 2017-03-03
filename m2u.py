import proxy

import logging
import argparse

parser = argparse.ArgumentParser(description='...')
parser.add_argument('--log', help='log file, use - for stdout [default: %(default)s]', default="-")
parser.add_argument('--severity', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Log severity [default: %(default)s]', default="INFO")
parser.add_argument('--proxy', help='proxy to use, use "" for no proxy [default: ""', default="")
parser.add_argument('FQDN', nargs='+', help='FQDN to intercept')
args = parser.parse_args()

if args.log != "-":
  logging.basicConfig(filename=args.log)
logging.basicConfig(level=getattr(logging, args.severity.upper(), None))


if __name__ == '__main__':

    proxy = proxy.Proxy(args.proxy, logging, args.FQDN)

    run = True
    while run:
        try:
            # This will block
            proxy.start()
        except KeyboardInterrupt:
            run = False
            logging.info("...exit")
        except Exception as e:
            logging.warning("oops: '%s', respawn..." % e.message)
        finally:
            proxy.stop()

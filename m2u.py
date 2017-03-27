import m2u

import logging
import argparse

parser = argparse.ArgumentParser(description='...')
parser.add_argument('--log', help='log file, use - for stdout [default: %(default)s]', default="-")
parser.add_argument('--severity', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    help='Log severity [default: %(default)s]', default="INFO")
parser.add_argument('--m2u', help='m2u to use, use "" for no m2u [default: ""', default="")
parser.add_argument('--memcached', help='memcache to use, provide IP:PORT or UNIX socket path [default: %(default)s]', default="127.0.0.1:11211")

parser.add_argument('FQDN', nargs='+', help='FQDN to intercept')
args = parser.parse_args()

if args.log != "-":
  logging.basicConfig(filename=args.log)
logging.basicConfig(level=getattr(logging, args.severity.upper(), None))


if __name__ == '__main__':

    proxy = m2u.Proxy(args.proxy, logging, args.FQDN, args.memcached)

    run = True
    p = None
    while run:
        try:
            p = HTTPProxy(name="Test", args=(logging, '', 80, args.FQDN, args.memcached))
            p.start()

            # This will block
            p.join()
        except KeyboardInterrupt:
            run = False
        except Exception as e:
            logging.warning("oops: '%s', respawn..." % e.message)
        finally:
            # Respawn...
            if p is not None:
                p.stop()

    logging.info("...exit")

#! /usr/bin/env python3
import argparse
import subprocess
import logging
import os
import smtplib
import sys
from logging import handlers

logger = logging.getLogger('le-renew')
logger.setLevel(logging.INFO)

try:
    import config
except ImportError as e:
    logger.critical('Failed to import config. Did you copy the '
                    'config.py.example file into config.py, and change its '
                    'values?')
    sys.exit(1)


class BufferingSMTPHandler(handlers.BufferingHandler):
    """
    Logging handler that sends a single mail (hopefully) with all logger
    messages. Adapted from https://gist.github.com/anonymous/1379446
    """

    def __init__(self, mailhost, fromaddr, toaddrs, subject, capacity):
        super().__init__(capacity)
        self.mailhost = mailhost
        self.mailport = None
        self.fromaddr = fromaddr
        self.toaddrs = toaddrs
        self.subject = subject
        self.setFormatter(logging.Formatter('%(asctime)s %(levelname)-5s '
                                            '%(message)s'))

    def flush(self):
        if len(self.buffer) > 0:
            try:
                port = self.mailport
                if not port:
                    port = smtplib.SMTP_PORT
                smtp = smtplib.SMTP(self.mailhost, port)
                msg = 'From: {}\r\nTo: {}\r\nSubject: {}\r\n\r\n'\
                    .format(self.fromaddr, ','.join(self.toaddrs),
                            self.subject)
                for record in self.buffer:
                    s = self.format(record)
                    msg = msg + s + '\r\n'
                smtp.sendmail(self.fromaddr, self.toaddrs, msg)
                smtp.quit()
            except:
                self.handleError(None)  # no particular record
            self.buffer = []


def cert_need_renew(cert_file, max_ttl):
    process = subprocess.Popen(['openssl', 'x509',
                                '-checkend', str(max_ttl),
                                '-noout', '-in', cert_file],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    out, err = process.communicate(timeout=15)
    if len(err) > 0:
        cert_filename = cert_file.split('/')[-1]
        logger.warning('openssl process stderr while parsing {}:\n{}'
                       .format(cert_filename, err.decode()))
    return process.returncode != 0


def gen_crt(csr, cert_path, acme_tiny_path, acme_account_key, acme_challenge,
            le_root_cert):
    process = subprocess.Popen(['python', acme_tiny_path,
                                '--account-key', acme_account_key,
                                '--csr', csr,
                                '--acme-dir', acme_challenge],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    cert, err = process.communicate(timeout=60)
    bundled_cert = '{}{}'.format(cert.decode(), le_root_cert)
    if len(err) > 0:
        domain = csr.split('/')[-1].replace('.csr', '')
        logger.warning('acme-tiny process stderr while generating {}:\n{}'
                       .format(domain, err.decode()))
    return bundled_cert


def main():
    parser = argparse.ArgumentParser(
        description='Check Let\'s Encrypt certificates and renew those which '
        'are about to expire')
    parser.add_argument('--cert_path', help='Certificate directory',
                        required=True)
    parser.add_argument('--acme_tiny_path', help='Path to acme-tiny script',
                        required=True)
    parser.add_argument('--acme_account_key', help='Path to acme-tiny account '
                        'key', required=True)
    parser.add_argument('--csr_path', help='Path to csr files directory',
                        required=True)
    parser.add_argument('--acme_challenge',
                        help='Path to ACME challenge directory', required=True)
    parser.add_argument('--le_root_cert', help='Path to Let\'s Encrypt root X3'
                        ' certificate', required=True)
    parser.add_argument('--max_ttl', type=int, help='Max expiration time (in '
                        'seconds) to renew', default=86400)
    args = parser.parse_args()

    if not os.path.isdir(args.cert_path):
        parser.error('cert path does not exist')
    if not os.path.isdir(args.csr_path):
        parser.error('csr path does not exist')
    if not os.path.isfile(args.acme_tiny_path):
        parser.error('acme-tiny is not found')
    if not os.path.isfile(args.acme_account_key):
        parser.error('acme account key is not found')

    with open(args.le_root_cert) as fd:
        le_root_cert = fd.read()

    for cert in os.listdir(args.cert_path):
        cert_file = os.path.join(args.cert_path, cert)
        if cert_need_renew(cert_file, args.max_ttl):
            try:
                domain = cert.replace('.crt', '')
                logger.info('Certificate for {} needs renewal'.format(domain))
                if not os.path.isfile(os.path.join(args.csr_path,
                                                   '{}.csr'.format(domain))):
                    logger.warn('CSR file not found for {}'.format(domain))
                else:
                    csr_file = os.path.join(args.csr_path,
                                            '{}.csr'.format(domain))
                    cert_content = gen_crt(csr_file, args.cert_path,
                                           args.acme_tiny_path,
                                           args.acme_account_key,
                                           args.acme_challenge, le_root_cert)
                    with open(cert_file, 'w') as fd:
                        fd.write(cert_content)
                    logger.info('Successfully renewed certificate for '
                                '{}'.format(domain))
            except Exception as e:
                logger.error('Failed to generate CRT {}: {}'
                             .format(cert, e))


if __name__ == '__main__':
    try:
        logger.addHandler(BufferingSMTPHandler(config.MAILHOST,
                                               config.FROM,
                                               config.TO,
                                               config.SUBJECT,
                                               100))
        main()
    finally:
        logging.shutdown()

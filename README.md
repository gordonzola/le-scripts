# Acme-tiny automation scripts

This is a bunch of scripts designed to complete the task of
[acme-tiny](https://github.com/diafygi/acme-tiny): make TLS certificates
generation simple and automated.

Here are the currently existing scripts:

- `le-renew.py`: checks all certificates from a directory, and starts renewal
  process if necessary. You probably want to use a cron task for this

## Requirements

Python3. Tested on python3.4. I aim to avoid third dependencies.

## Installation

Not required. Just execute the script you want.

## le-renew.py

This script will fetch all files from a given repository, make an `openssl`
expiration test on each one, and, if necessary, call `acme-tiny` to regenerate
this certificate.

Its arguments are basically the same as needed by `acme-tiny`: challenge dir,
Let's Encrypt account key… but there are some differences:

- Instead of passing a single CSR file and a target directory for CRT files,
  you must pass a directory containing CRT files to scan, and the CSR directory
  will be fetched to find the matching CSR. The CSR and CRT files **must have
  the same names** (except for their extension). For examble, a certificate for
  `test.localhost` could be `test.localhost.crt`, and the matching CSR would be
  `test.localhost.csr`.
- You must also pass the path to Let's Encrypt root CA file, in order to create
  a bundled certificate. You can download it
  [here](https://letsencrypt.org/certificates/) (I believe the X3 certificate
  is enough, and
  [there is its direct link](https://letsencrypt.org/certs/lets-encrypt-x3-cross-signed.pem).
- You can optionnally pass a certificate expiration limit (*max_TTL*), in
  seconds. Certificates which will expire within this value will be renewed.
  Value by default: 86400 (a full day). Be sure to set a value inferior to your
  cron periodicity.

### Example usage

**You don’t have to (and should not) run this script as root! Create a
`letsencrypt` dedicated user with limited rights!**

    ./le-renew.py  --cert_path /home/letsencrypt/certs/ --acme_tiny_path /home/letsencrypt/acme-tiny/acme_tiny.py --acme_account_key /home/letsencrypt/user.key --csr_path /home/letsencrypt/csr --acme_challenge /home/letsencrypt/docroot/ --le_root_cert /home/letsencrypt/files/lets-encrypt-x3-cross-signed.pem

### Logging

This script produces no output, given that it should be run by `cron`. Instead,
it sends an email with all logging information. Don't worry, if there is no
certificate to renew, there will be no mail.

To configure mail logger, you must copy `config.py.example` script into
`config.py`. Then edit it, and change the values as you wish.

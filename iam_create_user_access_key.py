#!/usr/bin/env python3

import argparse
import boto3
import logging


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--verbose', '-v', action='count')
    p.add_argument('user_name')
    args = p.parse_args()
    setup_logging(args.verbose)
    iam = boto3.resource('iam')
    user = iam.User(args.user_name)
    user.load()
    akp = user.create_access_key_pair()
    print()
    attrs = 'user_name access_key_id secret_access_key status create_date'.split()
    for attr in attrs:
        print('{}: {}'.format(attr, getattr(akp, attr)))


def setup_logging(verbose):
    if not verbose:
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        format='> [%(process)d] %(name)-26s %(levelname)s: %(message)s',
        level=level)


if __name__ == '__main__':
    main()

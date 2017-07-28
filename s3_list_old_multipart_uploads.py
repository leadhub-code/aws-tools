#!/usr/bin/env python3

import argparse
import boto3
from datetime import datetime, timedelta
import logging
import reprlib


smart_repr = reprlib.Repr().repr


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--verbose', '-v', action='store_true')
    p.add_argument('--remove', '-r', action='store_true')
    args = p.parse_args()
    setup_logging(args.verbose)

    s3 = boto3.resource('s3')
    s3c = boto3.client('s3')

    all_buckets = list(s3.buckets.all())
    for bucket in all_buckets:
        r = s3c.get_bucket_location(Bucket=bucket.name)
        location = r['LocationConstraint']
        print('Bucket: {name:35} {date} {location}'.format(
            name=bucket.name, date=bucket.creation_date, location=location))
        s3 = boto3.resource('s3', region_name=location)
        bucket = s3.Bucket(name=bucket.name)
        for up in list(bucket.multipart_uploads.all()):
            assert up.upload_id == up.id
            print('  Multipart upload: {date} {key} {id} {itor}'.format(
                date=up.initiated, key=up.object_key, id=smart_repr(up.id), itor=up.initiator['DisplayName']))

            current_object = s3.Object(bucket.name, up.object_key)
            try:
                current_object.load()
            except Exception as e:
                if '404' in str(e):
                    current_object = None
                else:
                    raise e
            if current_object:
                print('  Current object:', current_object.content_length)

            for part in up.parts.all():
                print('    Part: {:3} {:6} {}'.format(part.part_number, part.size, part.last_modified))

            assert isinstance(bucket.creation_date, datetime)
            if args.remove and bucket.creation_date.replace(tzinfo=None) < datetime.utcnow() - timedelta(days=30):
                print('ABORTING multipart upload {}'.format(up))
                r = up.abort()
                print(r)
                #print('  Parts after abort:', list(up.parts.all()))




def setup_logging(verbose):
    logging.basicConfig(
        format='> [%(process)d] %(name)-26s %(levelname)s: %(message)s',
        level=logging.DEBUG if verbose else logging.WARNING)


if __name__ == '__main__':
    main()

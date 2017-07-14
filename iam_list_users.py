#!/usr/bin/env python3

import argparse
import boto3
import logging
import multiprocessing
from pprint import pprint
import sys
import yaml


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--verbose', '-v', action='store_true')
    args = p.parse_args()
    setup_logging(args.verbose)
    iam = boto3.resource('iam')
    all_users = list(iam.users.all())
    with multiprocessing.Pool(32) as pool:
        users_data = to_dict(pool.map(dump_user, [u.name for u in all_users]))
    data = {
        'account_id': get_account_id(),
        'iam_users': users_data,
    }
    yaml.dump(data, sys.stdout, indent=4, default_flow_style=False)


def to_dict(items):
    items = list(items)
    assert len(set(k for k, v in items)) == len(items)
    return dict(items)


def get_account_id():
    return boto3.client('sts').get_caller_identity()['Account']


def dump_user(user_name):
    iam = boto3.resource('iam')
    user = iam.User(user_name)
    assert user.user_name == user.name
    return user.name, {
        'user_id': user.user_id,
        'create_date': user.create_date,
        'arn': user.arn,
        'path': user.path,
        'access_keys': to_dict(dump_access_key(ak) for ak in user.access_keys.all()),
        'attached_policies': to_dict(dump_policy(ap) for ap in user.attached_policies.all()),
        'groups': to_dict(dump_group(g) for g in user.groups.all()),
        'mfa_devices': [repr(d) for d in user.mfa_devices.all()],
        'policies': to_dict(dump_user_policy(p) for p in user.policies.all()),
        'signing_certificates': [repr(sc) for sc in user.signing_certificates.all()],
    }


def dump_access_key(ak):
    assert ak.id == ak.access_key_id
    return ak.access_key_id, {
        'crate_date': ak.create_date,
        'status': ak.status,
    }


def dump_group(g):
    assert g.group_name == g.name
    return g.name, {
        'group_id': g.group_id,
        'arn': g.arn,
    }


def dump_policy(p):
    assert p.__class__.__name__ == 'iam.Policy', repr(p.__class__.__name__)
    return p.arn, {
        'create_date': p.create_date,
        'path': p.path,
        'policy_id': p.policy_id,
        'policy_name': p.policy_name,
        'update_date': p.update_date,
        'default_version': dump_policy_version(p.default_version),
    }


def dump_policy_version(pv):
    if pv is None:
        return None
    return {
        'arn': pv.arn,
        'version_id': pv.version_id,
        'create_date': pv.create_date,
        'document': pv.document,
    }


def dump_user_policy(p):
    assert p.__class__.__name__ == 'iam.UserPolicy', repr(p.__class__.__name__)
    assert p.policy_name == p.name
    return p.policy_name, {
        'policy_document': p.policy_document,
    }


def setup_logging(verbose):
    logging.basicConfig(
        format='> [%(process)d] %(name)-26s %(levelname)s: %(message)s',
        level=logging.INFO if verbose else logging.WARNING)


if __name__ == '__main__':
    main()

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
    args = p.parse_args()
    setup_logging()
    iam = boto3.resource('iam')
    all_users = list(iam.users.all())
    with multiprocessing.Pool(32) as pool:
        users_data = pool.map(dump_user, [u.name for u in all_users])
    data = {'account_id': get_account_id(), 'users': users_data}
    yaml.dump(data, sys.stdout, indent=4, default_flow_style=False)


def get_account_id():
    return boto3.client('sts').get_caller_identity()['Account']


def dump_user(user_name):
    iam = boto3.resource('iam')
    user = iam.User(user_name)
    assert user.user_name == user.name
    return {
        'user_id': user.user_id,
        'name': user.name,
        'create_date': user.create_date,
        'arn': user.arn,
        'path': user.path,
        'access_keys': [dump_access_key(ak) for ak in user.access_keys.all()],
        'attached_policies': [dump_policy(ap) for ap in user.attached_policies.all()],
        'groups': [dump_group(g) for g in user.groups.all()],
        'mfa_devices': [repr(d) for d in user.mfa_devices.all()],
        'policies': [dump_user_policy(p) for p in user.policies.all()],
        'signing_certificates': [repr(sc) for sc in user.signing_certificates.all()],
    }


def dump_access_key(ak):
    assert ak.id == ak.access_key_id
    return {
        'access_key_id': ak.access_key_id,
        'crate_date': ak.create_date,
        'status': ak.status,
    }


def dump_group(g):
    return {
        'group_name': g.group_name,
        'group_id': g.group_id,
        'arn': g.arn,
    }


def dump_policy(p):
    assert p.__class__.__name__ == 'iam.Policy', repr(p.__class__.__name__)
    return {
        'arn': p.arn,
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
    return {
        'policy_name': p.policy_name,
        'policy_document': p.policy_document,
    }


def setup_logging():
    logging.basicConfig(
        format='> [%(process)d] %(name)-30s %(levelname)5s: %(message)s',
        level=logging.INFO)


if __name__ == '__main__':
    main()

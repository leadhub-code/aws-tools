#!/usr/bin/env python3

import argparse
import boto3
import json
import logging
import multiprocessing
from pathlib import Path
from pprint import pprint
import sys
import yaml


default_target_state_path = 'state.yaml'


logger = logging.getLogger(__name__)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--state', '-s', metavar='FILE', help='path to target state file')
    p.add_argument('--verbose', '-v', action='count')
    p.add_argument('--dry-run', '-n', action='store_true', help='just print the planned actions')
    p.add_argument('--execute', '-x', action='store_true')
    args = p.parse_args()
    setup_logging(args.verbose)

    try:
        target_state_path = Path(args.state or default_target_state_path).resolve()
        target_state_data = yaml.load(target_state_path.read_text())
    except FileNotFoundError as e:
        raise Exception('Failed to load target state file: {}'.format(e)) from None

    target_state = target_state_data['target_state']
    logger.info('Loaded target state from %s', target_state_path)

    check_account_id(target_state)

    with multiprocessing.Pool(32) as pool:
        plan_futures = []
        if not target_state.get('iam_users'):
            logger.info('No iam_users in target state')
        else:
            for user_name, user_state in target_state['iam_users'].items():
                if not isinstance(user_name, str):
                    raise Exception('User name must be str: {!r}'.format(user_name))
                if not isinstance(user_state, dict):
                    raise Exception('iam_users[{!r}] must be dict, not {!r}'.format(user_name, user_state))
                plan_futures.append(pool.apply_async(analyze_user, args=(user_name, user_state)))

        logger.debug('Waiting for results')
        plan = []
        for fut in plan_futures:
            try:
                actions = fut.get()
            except Exception as e:
                raise Exception('Worker failed: {}'.format(e)) from None
            assert isinstance(actions, list)
            plan.extend(actions)

    logger.debug('plan: %r', plan)


    print()
    print('Action plan:')
    print()

    if not plan:
        print('No actions needed, target state is already achieved.')
        return

    for n, action in enumerate(plan, start=1):
        name, params = action
        print('{:3d}. {:<15} {}'.format(n, name, params))
    print()

    if args.dry_run:
        return

    if not args.execute:
        r = input('Execute? [y/N] ')
        r = r.strip()
        if not r or r.lower() in ['n', 'no']:
            print('Not doing anything.')
            return
        if r.lower() not in ['y', 'yes']:
            raise Exception('You must enter "y" or "n".')
        print()

    for n, action in enumerate(plan, start=1):
        name, params = action
        print('Executing {:3d}. {:<15} {}'.format(n, name, params))
        execute_action(name, params)


def execute_action(name, params):
    '''
    Send commands to AWS API
    '''
    iam = boto3.resource('iam')
    if name == 'create_iam_user':
        iam.User(params['name']).create()
    elif name == 'put_iam_user_policy':
        up = iam.UserPolicy(user_name=params['user_name'], name=params['name'])
        to_json = lambda x: x if isinstance(x, str) else json.dumps(x, sort_keys=True, indent=4)
        # I don't know why somewhere else policy_document is already parsed and here it must be string
        up.put(PolicyDocument=to_json(params['policy_document']))
    else:
        raise Exception('Unknown action name {!r}'.format(name))


def analyze_user(user_name, user_state):
    try:
        logger.info('analyze_user %r', user_name)
        user_info = dump_user(user_name)
        logger.debug('user_info: %r', user_info)
        plan_actions = derive_user_actions(user_name, user_info, user_state)
        logger.info('analyze_user %r -> plan_actions: %r', user_name, plan_actions)
        return plan_actions
    except Exception as e:
        logger.exception('analyze_user {!r} failed: {}', user_name, e)
        # transform exceptions to str because some may fail to pickle
        raise Exception('analyze_user {!r} failed: {!r}'.format(user_name, e)) from None


def derive_user_actions(user_name, current_state, target_state):
    logger.debug('derive_user_actions %r', user_name)
    logger.debug('params:\n%s', yaml.dump({'current_state': current_state, 'target_state': target_state}, width=250))
    actions = []
    if not current_state:
        # user does not exist
        actions.append(('create_iam_user', {'name': user_name}))
    else:
        if target_state.get('policies'):
            for p_name, p_target in sorted(target_state['policies'].items()):
                p_current = current_state['policies'].get(p_name)
                if not p_target:
                    if p_current:
                        actions.append(('remove_iam_user_policy', {'user_name': user_name, 'name': p_name}))
                else:
                    if not p_current or p_current['policy_document'] != p_target['policy_document']:
                        actions.append(('put_iam_user_policy', {
                            'user_name': user_name,
                            'name': p_name,
                            'policy_document': p_target['policy_document'],
                        }))
    return actions


def dump_user(user_name):
    iam = boto3.resource('iam')
    user = iam.User(user_name)
    try:
        user.load()
    except Exception as e:
        if 'NoSuchEntity' in str(e):
            return None
        else:
            raise e
    assert user.user_name == user.name
    data = {
        'user_id': user.user_id,
        'create_date': user.create_date,
        'arn': user.arn,
        'path': user.path,
        'access_keys': {},
        'attached_policies': [],
        'groups': [],
        'policies': {}, # user_policies would be better name maybe
    }

    for ak in user.access_keys.all():
        data['access_keys'][ak.id] = {
            'status': ak.status,
        }

    for ap in user.attached_policies.all():
        assert ap.__class__.__name__ == 'iam.Policy', repr(ap.__class__.__name__)
        data['attached_policies'].append(ap.arn)

    for g in user.groups.all():
        data['groups'].append(g.name)

    for p in user.policies.all():
        assert p.__class__.__name__ == 'iam.UserPolicy', repr(p.__class__.__name__)
        data['policies'][p.name] = {
            'policy_document': p.policy_document,
        }

    return data


def check_account_id(target_state):
    if not target_state.get('account_id'):
        raise Exception('account_id is missing in target state file')
    account_id = get_account_id()
    if str(account_id) != str(target_state['account_id']):
        raise Exception(
            'Account id mismatch: target state account_id {!r} != AWS account id {!r}'.format(
                str(target_state['account_id']), str(account_id)))


def get_account_id():
    return boto3.client('sts').get_caller_identity()['Account']


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

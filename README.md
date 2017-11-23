AWS tools
=========

Here are some scripts I use to make management of the AWS account and resources easier.

This repository is just a playground. No intentions to replace [Terraform](https://www.terraform.io/) :)


iam_create_user_access_key.py
-----------------------------

Create access key for a given user.

Example:

```shell
$ ./iam_create_user_access_key.py sample_user

user_name: sample_user
access_key_id: AKIAIW...OTTGEA
secret_access_key: D6WtfL...LhwrI31
status: Active
create_date: 2017-07-15 21:40:16.769000+00:00
```


iam_list_users.py
-----------------

List all IAM users in your AWS account, including their groups, policies and other attributes.

I recommend to save the output to a file in a git repository (or some kind of monitoring).
This way you can observe all IAM changes in your account in time.

Example:

```shell
$ ./iam_list_users.py
account_id: '12345'
iam_users:
    john:
        access_keys: {}
        arn: arn:aws:iam::12345:user/john
        attached_policies: {}
        create_date: 2016-07-15 09:50:45+00:00
        groups:
            Developers:
                arn: arn:aws:iam::12345:group/Developers
                group_id: AGPAJ...KVONG
        mfa_devices: []
        path: /
        policies:
            custompolicy20170627:
                policy_document:
                    Statement:
                    -   Action:
                        - s3:*
                        Effect: Allow
                        Resource:
                        - arn:aws:s3:::*
        signing_certificates: []
        user_id: AIDAI...VRPE
```


iam_sync_users.py
-----------------

This is the same concept as in configuration management tools like Ansible, Puppet or Salt - you manage some
description of the "ideal state" (target state) and the program/script does all its best to turn it into reality.

I recommend to store the state file in git repository.

Example:

```shell
$ ./iam_sync_users.py -s target-state.yaml

Action plan:

  1. put_iam_user_policy {'policy_document': {'Statement': [{'Sid': 'Stmt1497973407000', 'Effect': 'Allow', 'Resource': ['arn:aws:s3:::*'], 'Action': ['s3:ListAllMyBuckets']}, {'Sid': 'Stmt1497973436000', 'Effect': 'Allow', 'Resource': ['arn:aws:s3:::sample-bucket'], 'Action': ['s3:ListBucket', 's3:ListBucketMultipartUploads', 's3:ListBucketVersions', 's3:ListObjects', 's3:ListMultipartUploadParts']}, {'Sid': 'Stmt1497973357000', 'Effect': 'Allow', 'Resource': ['arn:aws:s3:::sample-bucket/*'], 'Action': ['s3:GetObject', 's3:PutObject']}], 'Version': '2012-10-17'}, 'name': 'sample_custom_policy', 'user_name': 'sample_user'}

Execute? [y/N] y

Executing   1. put_iam_user_policy {'policy_document': {'Statement': [{'Sid': 'Stmt1497973407000', 'Effect': 'Allow', 'Resource': ['arn:aws:s3:::*'], 'Action': ['s3:ListAllMyBuckets']}, {'Sid': 'Stmt1497973436000', 'Effect': 'Allow', 'Resource': ['arn:aws:s3:::sample-bucket'], 'Action': ['s3:ListBucket', 's3:ListBucketMultipartUploads', 's3:ListBucketVersions', 's3:ListObjects', 's3:ListMultipartUploadParts']}, {'Sid': 'Stmt1497973357000', 'Effect': 'Allow', 'Resource': ['arn:aws:s3:::sample-bucket/*'], 'Action': ['s3:GetObject', 's3:PutObject']}], 'Version': '2012-10-17'}, 'name': 'sample_custom_policy', 'user_name': 'sample_user'}

$ ./iam_sync_users.py -s target-state.yaml

Action plan:

No actions needed, target state is already achieved.
```

"""Interface with AWS"""

import boto3

from aws_ssh.errors import NoInstanceFoundError, TooManyInstancesError

def get_session(profile_name):
    """Get the boto session

    :param profile_name: The profile name associated with the AWS creds
    :returns: The Boto3 session object

    """
    return boto3.session.Session(profile_name=profile_name)

def get_instance_info(profile_name, prefix, name):
    """Get the API info for an EC2 instance

    :param profile_name: The profile name associated with the AWS creds
    :param prefix: The name prefix shared by all EC2 instances
    :param name: The prefix-less instance name
    :returns: The corresponding instance, otherwise an exception

    """
    session = get_session(profile_name)
    client = session.client('ec2')
    response = client.describe_instances(Filters=[
        {'Name': 'tag:Name', 'Values': ['{}{}'.format(prefix, name)]}
        ])
    if len(response['Reservations']) == 0:
        raise NoInstanceFoundError()
    instances = response['Reservations'][0]['Instances']
    if len(instances) > 1:
        raise TooManyInstancesError()
    return instances[0]

"""Test the AWS module"""
# pylint: disable=redefined-outer-name,no-self-use,unused-argument,protected-access,missing-docstring,invalid-name,line-too-long
from collections import namedtuple
import json
from unittest.mock import patch

import pytest

from aws_ssh import aws, errors

SessionVars = namedtuple('SessionVars', 'session instance client describe_instances')

@pytest.fixture
def session_vars():
    with patch('boto3.session.Session') as session_mock:
        instance = session_mock.return_value
        client = instance.client
        describe_instances = client.return_value.describe_instances
        yield SessionVars(session_mock, instance, client, describe_instances)

def test_get_session():
    with patch('boto3.session.Session') as session_mock:
        aws.get_session('foobar')
        session_mock.assert_called_with(profile_name='foobar')

def test_get_instance_info(session_vars):
    session_vars.describe_instances.return_value = get_sample_response()
    info = aws.get_instance_info('foobar', 'test-', 'name')

    session_vars.session.assert_called_with(profile_name='foobar')
    session_vars.client.assert_called_with('ec2')
    assert session_vars.describe_instances.called
    assert info['PublicIpAddress'] == '52.90.39.59'

def test_get_instance_info_empty(session_vars):
    session_vars.describe_instances.return_value = get_sample_response(0)
    with pytest.raises(errors.NoInstanceFoundError):
        aws.get_instance_info('foobar', 'test-', 'name')

def test_get_instance_info_multiple(session_vars):
    session_vars.describe_instances.return_value = get_sample_response(2)
    with pytest.raises(errors.TooManyInstancesError):
        aws.get_instance_info('foobar', 'test-', 'name')

def get_sample_response(instance_count=1):
    response = {'Reservations': [{'Instances': []}]}
    if instance_count == 0:
        response['Reservations'] = []
        return response
    response['Reservations'][0]['Instances'] = [json.loads(SAMPLE_INSTANCE_BODY) for _ in range(instance_count)]
    return response

SAMPLE_INSTANCE_BODY = """
{"InstanceId": "i-0958008e", "ImageId": "ami-d05e75b8", "State": {"Code": 16, "Name": "running"}, "PrivateDnsName": "ip-10-0-0-186.ec2.internal", "PublicDnsName": "ec2-52.90.39.59.compute-1.amazonaws.com", "StateTransitionReason": "", "KeyName": "project", "AmiLaunchIndex": 0, "ProductCodes": [], "InstanceType": "m3.large", "LaunchTime": "2016-05-12T19:38:00.000Z", "Placement": {"AvailabilityZone": "us-east-1a", "GroupName": "", "Tenancy": "default"}, "Monitoring": {"State": "disabled"}, "SubnetId": "subnet-8dadbffa", "VpcId": "vpc-e821f18c", "PrivateIpAddress": "10.0.0.186", "PublicIpAddress": "52.90.39.59", "Architecture": "x86_64", "RootDeviceType": "ebs", "RootDeviceName": "/dev/sda1", "BlockDeviceMappings": [{"DeviceName": "/dev/sda1", "Ebs": {"VolumeId": "vol-3f4df594", "Status": "attached", "AttachTime": "2016-05-12T19:38:01.000Z", "DeleteOnTermination": true}}], "VirtualizationType": "hvm", "ClientToken": "project-Comput-1HKOY7086GV2G", "Tags": [{"Key": "POC", "Value": "Aru Sahni"}, {"Key": "Name", "Value": "project-compute"}, {"Key": "aws:cloudformation:logical-id", "Value": "ComputeInstance"}, {"Key": "Class", "Value": "project-compute"}, {"Key": "Project", "Value": "project"}, {"Key": "Stack", "Value": "project-cloudformation"}, {"Key": "aws:cloudformation:stack-id", "Value": "arn:aws:cloudformation:us-east-1:577354146450:stack/project/7ab2d640-66e6-11e5-955a-500150b34c7c"}, {"Key": "aws:cloudformation:stack-name", "Value": "project"}], "SecurityGroups": [{"GroupName": "project-SecurityGroupComputeWeb-W8OZK5PH7KRN", "GroupId": "sg-5457982f"}, {"GroupName": "project-SecurityGroupHGHQ-G86ETFB3FG4O", "GroupId": "sg-de9476b8"}], "SourceDestCheck": true, "Hypervisor": "xen", "NetworkInterfaces": [{"NetworkInterfaceId": "eni-800518c0", "SubnetId": "subnet-8dadbffa", "VpcId": "vpc-e821f18c", "Description": "Primary network interface", "OwnerId": "577354146450", "Status": "in-use", "MacAddress": "0a:1e:c9:33:d8:15", "PrivateIpAddress": "10.0.0.186", "PrivateDnsName": "ip-10-0-0-186.ec2.internal", "SourceDestCheck": true, "Groups": [{"GroupName": "project-SecurityGroupComputeWeb-W8OZK5PH7KRN", "GroupId": "sg-5457982f"}, {"GroupName": "project-SecurityGroupHGHQ-G86ETFB3FG4O", "GroupId": "sg-de9476b8"}], "Attachment": {"AttachmentId": "eni-attach-f61a4b0b", "DeviceIndex": 0, "Status": "attached", "AttachTime": "2016-05-12T19:38:00.000Z", "DeleteOnTermination": true}, "Association": {"PublicIp": "52.90.39.59", "PublicDnsName": "ec2-52.90.39.59.compute-1.amazonaws.com", "IpOwnerId": "amazon"}, "PrivateIpAddresses": [{"PrivateIpAddress": "10.0.0.186", "PrivateDnsName": "ip-10-0-0-186.ec2.internal", "Primary": true, "Association": {"PublicIp": "52.90.39.59", "PublicDnsName": "ec2-52.90.39.59.compute-1.amazonaws.com", "IpOwnerId": "amazon"}}], "Ipv6Addresses": []}], "IamInstanceProfile": {"Arn": "arn:aws:iam::577354146450:instance-profile/project-ComputeInstanceProfile-J4Q37C5EEWSI", "Id": "AIPAIGVRQT3L5JVKDWKCS"}, "EbsOptimized": false}
"""

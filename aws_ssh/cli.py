"""The command line interface"""
from __future__ import print_function

import argparse
from collections import namedtuple
import logging
import os
import sys

import six
from six.moves import input

from aws_ssh import APP_NAME
from aws_ssh.errors import ProjectConfigNotFoundError
from aws_ssh.interfaces import Environment

Argument = namedtuple('Argument', 'switch metavar description prompt')

logger = logging.getLogger(__name__)

ARGUMENTS = {
    'project_name': Argument('name', 'NAME', 'The name of the initialized project',
                             'a name for this project'),
    'profile':      Argument('profile', 'PROFILE', 'The AWS profile to use', 'the AWS profile to use'),
    'key':          Argument('key', 'KEY', 'The name of the private key used for to authentication',
                             'the name of the private key used for authentication (including extension)'),
    'prefix':       Argument('prefix', 'PREFIX', 'The shared prefix for all EC2 instance names',
                             'the prefix for EC2 names'),
    'root':         Argument('root', 'ROOT', 'The root directory for the project',
                             'the root directory for the project'),
}

class AwsshHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """Customize the CLI help functionality"""
    def _format_usage(self, usage, actions, groups, prefix):
        prefix = 'usage: '
        init_actions = [action for action in actions if action.dest != 'instance']
        host_actions = [action for action in actions if action.dest in ('instance', 'help', 'debug')]
        init_usage = super(AwsshHelpFormatter, self)._format_usage(usage, init_actions, groups, prefix)
        host_usage = super(AwsshHelpFormatter, self)._format_usage(usage, host_actions, groups, prefix)
        init_usage = init_usage.replace(prefix, len(prefix) * ' ') # Replace the usage prefix with whitespace
        return host_usage.replace('[HOST]', 'HOST')[:-1] + init_usage # Strip trailing newline and concat


def prompt_for_arg(argument, out=sys.stderr):
    """Prompt the user for a value"""
    out.write('Please provide {}: '.format(argument.prompt))
    return input()

def get_project_properties(args):
    """Get the required properties for a project, starting with the CLI args and prompting for the rest.

    :param args: The argparse arguments
    :returns: a dict of populated properties

    """
    properties = {}
    for argname, argument in six.iteritems(ARGUMENTS):
        properties[argname] = args.get(argname) or prompt_for_arg(argument)
    return properties

def init_environment(environment):
    """Initialize the user configuration"""
    key_root = prompt_for_arg(Argument('key_root', 'PATH', '',
                                       'the full path to the directory containing all private keys'))
    environment.set_key_root(key_root)
    environment.save()

def get_ssh_args(args):
    """Get the arguments for SSH on the CLI"""
    parser = get_parser()
    args = parser.parse_args(args)
    if args.debug:
        logging.getLogger('aws_ssh').setLevel(logging.DEBUG)
    environment = Environment()
    if not environment.is_initialized():
        logger.debug('User config not initialized.')
        init_environment(environment)
    if args.initialize:
        properties = get_project_properties(vars(args))
        environment.create_project(properties['project_name'], properties['prefix'], properties['profile'],
                                   properties['root'], properties['key'])
        sys.stderr.write('Initialized!\n')
        sys.exit(-1)
    try:
        project = environment.find_project(os.getcwd())
    except ProjectConfigNotFoundError:
        parser.error('No project configuration found. Run `{} --init` to initialize.'.format(APP_NAME))
    if not args.instance:
        parser.error('Instance name required')
    logger.debug('Project loaded: %s', project)
    instance = project.get_instance(args.instance)
    return project.key_path, instance.get_user_name(), instance.ip

def print_ssh_args(out=sys.stdout):
    """Print the arguments for SSH to stdout and exit with a success error code."""
    key, user, addr = get_ssh_args(sys.argv[1:])
    sys.stderr.write('Connecting to {}\n'.format(addr))
    out.write("-i {} {}@{}\n".format(key, user, addr))
    sys.exit(170)

def get_parser():
    """Get the command line argument parser"""
    parser = argparse.ArgumentParser(prog=APP_NAME, formatter_class=AwsshHelpFormatter)
    parser.add_argument('--debug', action='store_true', help='Enable debugging output')
    parser.add_argument("--init", dest="initialize", action="store_true", help="Initialize the project.")
    # TODO: Add hook to register project (like init, but sourced from existing .awssshrc file)
    for argname, argument in six.iteritems(ARGUMENTS):
        parser.add_argument("--{}".format(argument.switch), dest=argname, metavar=argument.metavar,
                            default=None, help=argument.description)
    parser.add_argument("instance", nargs="?", default=None, type=str, metavar="HOST",
                        help="The name of the instance to connect to.")
    return parser

if __name__ == "__main__":
    print_ssh_args()

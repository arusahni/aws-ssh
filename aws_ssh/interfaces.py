"""Projects"""

# pylint: disable=protected-access

import logging
import os
import os.path

from pexpect import pxssh
import six
import configparser
from tqdm import tqdm

from aws_ssh import aws
from aws_ssh.errors import NoConfigError, ProjectConfigNotFoundError, SSHError, UsernameNotFoundError

logger = logging.getLogger(__name__)

DEFAULT_AWSSH_CONFIG = '~/.aws-ssh/config.ini'
DEFAULT_PROJECT_CONFIG = '.awssshconfig'

class Environment(object):
    """User-level configuration"""

    @property
    def key_dir(self):
        """The base directory for all private keys"""
        return self._config['DEFAULT'].get('key_dir')

    def __init__(self, path=DEFAULT_AWSSH_CONFIG):
        self.path = os.path.expanduser(path)
        self._config = configparser.ConfigParser()
        if os.path.exists(self.path):
            logger.info("Loading user config file: %s", self.path)
            self._config.read(self.path)

    def is_initialized(self):
        """Determine if the user has configured aws-ssh before."""
        return os.path.exists(self.path) and self._config['DEFAULT'].get('key_dir')

    def set_key_root(self, path):
        """Set the root path for all private keys

        :param path: The full path to the root directory containing keys

        """
        self._config['DEFAULT']['key_dir'] = os.path.expanduser(path)

    def add_project(self, project):
        """Add a project to the system"""
        self._config["project_{}".format(project.name)] = {'root': project.root}

    def create_project(self, name, prefix, profile_name, root_dir, key_file):
        """Create a project with the given parameters

        :param name: The name of the project
        :param prefix: The prefix for all project instances
        :param profile_name: The name of the AWS/Boto config to use
        :param root_dir: The project's root directory
        :param key_file: The name (including extension) of the key used for instance authentication
        :returns: The created project

        """
        project = Project(root_dir, self, name=name, prefix=prefix, profile=profile_name, key=key_file)
        project.save()
        self.add_project(project)
        self.save()
        return project

    def save(self):
        """Save the configuration to disk"""
        if not os.path.exists(os.path.dirname(self.path)):
            os.makedirs(os.path.dirname(self.path))
        with open(self.path, 'w') as configfile:
            self._config.write(configfile)

    def find_project(self, path):
        """Find the project configuration in the filesystem hierarchy

        :param path: The root directory for the project
        :returns: The project in the directory

        """
        project = Project.load(path, self)
        if 'project_{}'.format(project.name) not in self._config:
            logger.info('Project "%s" is not registered. Registering...', project.name)
            self.add_project(project)
            self.save()
        return project

    def __repr__(self):
        return "Environment[{}]".format(self.path)

class Project(object):
    """A project"""

    _usernames = ['ubuntu', 'ec2-user', 'centos', 'root']

    @property
    def name(self):
        """The project name"""
        return self._config['DEFAULT']['name']

    @name.setter
    def name(self, value):
        self._config['DEFAULT']['name'] = value

    @property
    def key(self):
        """The project key filename"""
        return self._config['DEFAULT']['key']

    @key.setter
    def key(self, value):
        self._config['DEFAULT']['key'] = value

    @property
    def prefix(self):
        """The prefix for all instances in the project"""
        return self._config['DEFAULT']['prefix']

    @prefix.setter
    def prefix(self, value):
        self._config['DEFAULT']['prefix'] = value

    @property
    def profile(self):
        """The AWS profile to use for project API access"""
        return self._config['DEFAULT']['profile']

    @profile.setter
    def profile(self, value):
        self._config['DEFAULT']['profile'] = value

    @property
    def key_path(self):
        """Get the full path to the project's auth key"""
        return os.path.join(self._environment.key_dir, self.key)

    # pylint: disable=unused-argument,too-many-arguments
    def __init__(self, root, environment, name=None, prefix=None, profile=None, key=None, config=None):
        """Initialize a project.

        :param name: The name of the project
        :param prefix: The prefix shared by all project instances
        :param profile: The name of the AWS/Boto profile for the project
        :param root: The root directory of the project
        :param key: The file name of the certificate used for instance authentication
        :param environment: The environment to which the project is registered
        :param config: The project configuration

        """
        self._config = config or configparser.ConfigParser()
        if config is None:
            logger.debug('No project config passed in, using initialized params')
            for field in ('name', 'prefix', 'profile', 'key'):
                if locals()[field] is None:
                    raise AttributeError(field)
                setattr(self, field, locals()[field])
        self.root = os.path.expanduser(root)
        self._environment = environment

    @staticmethod
    def find_config(directory):
        """Find the first project config in the ancestral path.

        :param directory: The directory whose ancestors should be searched

        :returns: The absolute path to the project config file
        """
        for fil in os.listdir(directory):
            if fil == DEFAULT_PROJECT_CONFIG and os.path.isfile(os.path.join(directory, fil)):
                return os.path.join(directory, fil)
        parent_dir = os.path.abspath(os.path.join(directory, os.pardir))
        if parent_dir == directory: # We've hit a filesystem root. No further to traverse.
            raise ProjectConfigNotFoundError()
        return Project.find_config(parent_dir)

    @classmethod
    def load(cls, current_dir, environment):
        """Find and load the config file in the given directory's hierachy

        :param current_dir: The directory in which the search for a project config should start
        :param environment: The environment to which projects are registered
        :returns: The project associated with the given path

        """
        config_path = Project.find_config(current_dir)
        logger.info('Loading project config file: %s', config_path)
        config = configparser.ConfigParser()
        config.read(config_path)
        return cls(root=os.path.dirname(config_path), environment=environment, config=config)

    def set_instance_config(self, instance_name, **kwargs):
        """Set the configuration of an instance

        :param instance_name: The name of the instance
        :param kwargs: The various instance properties to write out

        """
        self._config['instance_{}'.format(instance_name)] = kwargs
        self.save()

    def get_instance_config(self, instance_name):
        """Get the configuration for an instance

        :param instance_name: The name of the instance
        :returns: The configuration for the corresponding instance

        """
        try:
            return self._config['instance_{}'.format(instance_name)]
        except KeyError:
            raise NoConfigError(instance_name)

    def save(self):
        """Save the project settings"""
        with open(os.path.join(self.root, DEFAULT_PROJECT_CONFIG), 'w') as configfile:
            self._config.write(configfile)

    def get_instance(self, instance_name):
        """Get the instance info for the project

        :returns: The instance info

        """
        return Instance("{}{}".format(self.prefix, instance_name),
                        aws.get_instance_info(self.profile, self.prefix, instance_name), self)

    def ssh(self, instance_name):
        """SSH into the given instance"""
        # Don't use this for now
        instance = self.get_instance(instance_name)
        logger.debug(instance)
        try:
            session = pxssh.pxssh()
            session.login(instance.ip, instance.get_user_name(), ssh_key=self.key_path, login_timeout=30,
                          quiet=False, auto_prompt_reset=False)
            print('Connected!')
            print(session.before.decode('utf-8'))
            session.interact()
        except pxssh.ExceptionPxssh as ssh_exc:
            six.raise_from(SSHError, ssh_exc)

    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        return '{cname}<{name}>'.format(cname=self.__class__.__name__, name=self.name)

class Instance(object):
    """A computer to which one can connect"""

    @property
    def ip(self):
        """Get the canonical IP address for the instance.

        In the future, this can be affected by user configuration to return the private IP.

        """
        return self.public_ip

    @property
    def username(self):
        """The instances username"""
        try:
            return self._project.get_instance_config(self.name)['username']
        except NoConfigError:
            return None

    @username.setter
    def username(self, value):
        self._project.set_instance_config(self.name, username=value)

    def __init__(self, name, aws_resource, project):
        """Initialize the instance

        :param name: The name of the instance
        :param aws_resource: The AWS API response
        :param project: The owning project

        """
        self._aws_resource = aws_resource
        self._project = project
        self.name = name
        self.public_ip = aws_resource['PublicIpAddress']

    def get_user_name(self):
        """Determine the username of for the instance

        :returns: The username, raises `UsernameNotFoundError` otherwise.

        """
        if self.username:
            return self.username
        logger.debug('Searching for username within: %s', self._project._usernames)
        with tqdm(self._project._usernames) as usernames:
            for username in usernames:
                logger.debug('Trying username: %s', username)
                usernames.set_description('Trying {0}@{1}'.format(username, self.ip))
                try:
                    session = pxssh.pxssh(env={'SSH_ASKPASS': ''})
                    session.login(self.ip, username, ssh_key=self._project.key_path, login_timeout=10,
                                  quiet=True, auto_prompt_reset=False)
                    session.logout()
                    self.username = username
                    return username
                except pxssh.ExceptionPxssh:
                    logger.debug('Auth failed for username: %s', username)
        raise UsernameNotFoundError()

    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        return '{cname}<{name}, {ip}>'.format(cname=self.__class__.__name__, name=self.name, ip=self.ip)

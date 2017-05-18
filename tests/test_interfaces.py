# pylint: disable=redefined-outer-name,no-self-use,unused-argument,protected-access,missing-docstring,invalid-name,line-too-long
import json
import os.path
from collections import namedtuple
try:
    from unittest.mock import call, MagicMock, patch, mock_open, PropertyMock
except ImportError:
    from mock import call, MagicMock, patch, mock_open, PropertyMock

import pytest
from pexpect import pxssh
from configparser import ConfigParser  # pylint: disable=import-error

from aws_ssh import errors
from aws_ssh.interfaces import DEFAULT_AWSSH_CONFIG, DEFAULT_PROJECT_CONFIG, Environment, Instance, Project
from fixtures import * # pylint: disable=import-error,wildcard-import
from test_aws import SAMPLE_INSTANCE_BODY # pylint: disable=import-error

EnvironmentVars = namedtuple('EnvironmentVars', 'env config, config_values')

@pytest.fixture
def new_environment(parser_mock):
    with patch('os.path.exists') as path_exists:
        path_exists.return_value = False
        config = parser_mock.return_value
        config_values = MagicMock()
        config.__getitem__.side_effect = lambda key: {'DEFAULT': config_values}[key]
        config_values.get.side_effect = lambda x: None
        yield EnvironmentVars(Environment(), config, config_values)

@pytest.fixture
def existing_environment(parser_mock):
    with patch('os.path.exists') as path_exists:
        path_exists.return_value = True
        env = Environment()
        old_config = env._config
        env._config = ConfigParser()
        env._config.read_dict({
            'DEFAULT': {
                'key_dir': '/path/to/key'
            }
        })
        yield EnvironmentVars(env, old_config, env._config['DEFAULT'])

@pytest.fixture
def project_mock():
    with patch('aws_ssh.interfaces.Project') as project_mock:
        yield project_mock

@pytest.fixture
def existing_project(parser_mock, existing_environment):
    config = ConfigParser()
    config.read_dict({
        'DEFAULT': {
            'key': 'foo.pem',
            'prefix': 'foo-',
            'profile': 'testing',
            'name': 'foo',
        }
    })
    project = Project('/path/to/foo', existing_environment.env, config=config)
    yield project

@pytest.fixture
def open_mock():
    with patch('aws_ssh.interfaces.open', mock_open(), create=True) as opens:
        yield opens

@pytest.fixture
def aws_resource():
    return json.loads(SAMPLE_INSTANCE_BODY)

@pytest.fixture
def new_instance(existing_project):
    return Instance('fooinst', json.loads(SAMPLE_INSTANCE_BODY), existing_project)

@pytest.fixture
def existing_instance(existing_project):
    existing_project._config['instance_fooinst'] = {'username': 'ec2-user'}
    return Instance('fooinst', json.loads(SAMPLE_INSTANCE_BODY), existing_project)

class TestEnvironment(object):
    """Test the environment"""

    def test_path_expansion(self, path_exists):
        path_exists.return_value = False # Defensive, don't load something we don't own
        environment = Environment('~/foo')
        assert len(path_exists.call_args_list) == 1
        assert environment.path == os.path.expanduser('~/foo')

    def test_no_config(self, new_environment):
        assert not new_environment.config.read.called

    def test_config(self, existing_environment):
        assert len(existing_environment.config.read.call_args_list) == 1

    def test_keydir_empty(self, new_environment):
        keydir = new_environment.env.key_dir
        new_environment.config.__getitem__.assert_called_with('DEFAULT')
        new_environment.config_values.get.assert_called_with('key_dir')
        assert keydir is None

    def test_keydir_defined(self, existing_environment):
        keydir = existing_environment.env.key_dir
        assert keydir == '/path/to/key'

    def test_is_initialized_not_ok(self, new_environment):
        assert not new_environment.env.is_initialized()

    def test_is_initialized_ok(self, existing_environment):
        assert existing_environment.env.is_initialized()

    def test_set_key_root(self, existing_environment):
        existing_environment.env.set_key_root('/new/path/to/key')
        assert existing_environment.env.key_dir == '/new/path/to/key'

    def test_add_project(self, existing_environment):
        project_mock = namedtuple('MockProject', 'name root')('foo', '/path/too/foo')
        existing_environment.env.add_project(project_mock)
        assert 'project_{}'.format(project_mock.name) in existing_environment.env._config
        assert existing_environment.env._config['project_{}'.format(project_mock.name)]['root'] == '/path/too/foo'

    def test_create_project(self, existing_environment, project_mock):
        existing_environment.env.add_project = MagicMock()
        existing_environment.env.save = MagicMock()
        project = existing_environment.env.create_project('foo', 'foo-', 'test', '/path/to/foo', 'test.pem')
        project_mock.assert_called_with('/path/to/foo', existing_environment.env, name='foo', prefix='foo-', profile='test', key='test.pem')
        project.save.assert_called_with()
        existing_environment.env.add_project.assert_called_with(project)
        existing_environment.env.save.assert_called_with()

    def test_save_existing(self, existing_environment, open_mock):
        existing_environment.env.save()
        open_mock.assert_called_with(os.path.expanduser(DEFAULT_AWSSH_CONFIG), 'w')
        assert len(open_mock().write.mock_calls) > 0

    def test_save_new(self, new_environment, mkdirs_mock, open_mock):
        new_environment.env.save()
        mkdirs_mock.assert_called_with(os.path.dirname(os.path.expanduser(DEFAULT_AWSSH_CONFIG)))
        open_mock.assert_called_with(os.path.expanduser(DEFAULT_AWSSH_CONFIG), 'w')
        new_environment.config.write.assert_called_with(open_mock())

    def test_find_project_exists_registered(self, project_mock, existing_environment):
        project = MagicMock()
        type(project).name = PropertyMock(return_value='foo')
        project_mock.load.return_value = project
        existing_environment.env._config['project_foo'] = {}
        existing_environment.env.add_project = MagicMock()
        existing_environment.env.save = MagicMock()
        found_project = existing_environment.env.find_project('/path/to/foo')
        assert project_mock.load.mock_calls[0][1][0] == '/path/to/foo'
        assert project_mock.load.mock_calls[0][1][1] == existing_environment.env
        assert len(existing_environment.env.add_project.mock_calls) == 0
        assert len(existing_environment.env.save.mock_calls) == 0
        assert project == found_project

    def test_find_project_exists_unregistered(self, project_mock, existing_environment):
        project = MagicMock()
        type(project).name = PropertyMock(return_value='foo')
        project_mock.load.return_value = project
        existing_environment.env.add_project = MagicMock()
        existing_environment.env.save = MagicMock()
        found_project = existing_environment.env.find_project('/path/to/foo')
        assert project_mock.load.mock_calls[0][1][0] == '/path/to/foo'
        assert project_mock.load.mock_calls[0][1][1] == existing_environment.env
        existing_environment.env.add_project.assert_called_with(project)
        existing_environment.env.save.assert_called_with()
        assert project == found_project

    def test_find_project_nonexistant(self, project_mock, existing_environment):
        project_mock.load.side_effect = errors.ProjectConfigNotFoundError()
        with pytest.raises(errors.ProjectConfigNotFoundError):
            existing_environment.env.find_project('/path/to/foo')
        assert project_mock.load.mock_calls[0][1][0] == '/path/to/foo'
        assert project_mock.load.mock_calls[0][1][1] == existing_environment.env


class TestProjectConfig(object):
    def test_find_config_empty_dirs(self, listdir_mock):
        listdir_mock.return_value = []
        with pytest.raises(errors.ProjectConfigNotFoundError):
            Project.find_config('/path/to/foo')
        listdir_mock.assert_has_calls([call('/path/to/foo'),
                                       call('/path/to'),
                                       call('/path'),
                                       call('/')])

    def test_find_config_current_dir(self, listdir_mock, isfile_mock):
        listdir_mock.return_value = [DEFAULT_PROJECT_CONFIG]
        isfile_mock.return_value = True
        config_path = Project.find_config('/path/to/foo')
        assert config_path == '/path/to/foo/' + DEFAULT_PROJECT_CONFIG

    def test_find_config_current_dir_notfile(self, listdir_mock, isfile_mock):
        listdir_mock.return_value = [DEFAULT_PROJECT_CONFIG]
        isfile_mock.return_value = False
        with pytest.raises(errors.ProjectConfigNotFoundError):
            Project.find_config('/path/to/foo')

    def test_find_config_parent_dir(self, listdir_mock, isfile_mock):
        listdir_mock.side_effect = lambda x: [DEFAULT_PROJECT_CONFIG] if x == '/path/to' else []
        isfile_mock.return_value = True
        config_path = Project.find_config('/path/to/foo')
        assert config_path == '/path/to/' + DEFAULT_PROJECT_CONFIG

    def test_load(self, new_environment):
        Project.find_config = MagicMock(return_value='/path/to/foo/' + DEFAULT_PROJECT_CONFIG)
        project = Project.load('/path/to/foo', new_environment.env)
        Project.find_config.assert_called_with('/path/to/foo')
        new_environment.config.read.assert_called_with('/path/to/foo/' + DEFAULT_PROJECT_CONFIG)
        assert project._config == new_environment.config
        assert project.root == '/path/to/foo'
        assert project._environment == new_environment.env

    @pytest.mark.parametrize('field_name', ['name', 'key', 'prefix', 'profile'])
    def test_config_params(self, existing_project, field_name):
        setattr(existing_project, field_name, field_name)
        assert existing_project._config['DEFAULT'][field_name] == field_name

    def test_key_path(self, existing_project):
        assert existing_project.key_path == existing_project._environment.key_dir + '/foo.pem'

    def test_get_instance_config_exists(self, existing_project):
        existing_project._config['instance_foo'] = {'bar': 'baz'}
        instance_config = existing_project.get_instance_config('foo')
        assert 'bar' in instance_config
        assert instance_config['bar'] == 'baz'

    def test_get_instance_config_nonexistent(self, existing_project):
        with pytest.raises(errors.NoConfigError):
            existing_project.get_instance_config('foo')

    def test_set_instance_config(self, existing_project):
        existing_project.save = MagicMock()
        existing_project.set_instance_config('foo', bar='baz', answer=42)
        existing_project.save.assert_called_with()
        assert 'instance_foo' in existing_project._config
        assert 'bar' in existing_project._config['instance_foo']
        assert existing_project._config['instance_foo']['bar'] == 'baz'
        assert 'answer' in existing_project._config['instance_foo']
        assert existing_project._config['instance_foo']['answer'] == '42'

    def test_save(self, existing_project, open_mock):
        existing_project._config.write = MagicMock()
        existing_project.save()
        open_mock.assert_called_with('/path/to/foo/' + DEFAULT_PROJECT_CONFIG, 'w')
        existing_project._config.write.assert_called_with(open_mock())

class TestInstance(object):

    def test_init_valid_resource(self, aws_resource, existing_project):
        instance = Instance('fooinst', aws_resource, existing_project)
        assert instance.public_ip == aws_resource['PublicIpAddress']

    def test_init_invalid_resource(self, existing_project):
        with pytest.raises(KeyError):
            Instance('fooinst', {}, existing_project)

    def test_get_user_name_uncached(self, aws_resource, new_instance):
        new_instance._project._usernames = ['ubuntu']
        with patch('pexpect.pxssh.pxssh') as pxssh_mock:
            session_mock = pxssh_mock.return_value
            new_instance._project.set_instance_config = MagicMock()
            username = new_instance.get_user_name()
            session_mock.login.assert_called_with(aws_resource['PublicIpAddress'], 'ubuntu', ssh_key=new_instance._project.key_path, login_timeout=10, quiet=True, auto_prompt_reset=False)
            session_mock.logout.assert_called_with()
            assert username == 'ubuntu'
            new_instance._project.set_instance_config.assert_called_with('fooinst', username='ubuntu')

    def test_get_user_name_cached(self, existing_instance):
        username = existing_instance.get_user_name()
        with patch('pexpect.pxssh.pxssh') as pxssh_mock:
            assert len(pxssh_mock.mock_calls) == 0
            assert username == 'ec2-user'

    def test_get_user_name_multiple_first(self, aws_resource, new_instance):
        new_instance._project._usernames = ['ubuntu', 'ec2-user']
        with patch('pexpect.pxssh.pxssh') as pxssh_mock:
            session_mock = pxssh_mock.return_value
            new_instance._project.set_instance_config = MagicMock()
            username = new_instance.get_user_name()
            assert username == 'ubuntu'
            assert session_mock.login.call_count == 1
            session_mock.login.assert_called_with(aws_resource['PublicIpAddress'], 'ubuntu', ssh_key=new_instance._project.key_path, login_timeout=10, quiet=True, auto_prompt_reset=False)
            session_mock.logout.assert_called_with()
            new_instance._project.set_instance_config.assert_called_with('fooinst', username='ubuntu')

    def test_get_user_name_multiple_second(self, aws_resource, new_instance):
        new_instance._project._usernames = ['ubuntu', 'ec2-user']
        def usernaame_checks(ip, username, **kwargs):
            if username == 'ubuntu':
                raise pxssh.ExceptionPxssh('ubuntu')
            return None
        with patch('pexpect.pxssh.pxssh') as pxssh_mock:
            session_mock = pxssh_mock.return_value
            new_instance._project.set_instance_config = MagicMock()
            session_mock.login.side_effect = usernaame_checks
            username = new_instance.get_user_name()
            assert username == 'ec2-user'
            assert session_mock.login.call_count == 2
            session_mock.login.assert_called_with(aws_resource['PublicIpAddress'], 'ec2-user', ssh_key=new_instance._project.key_path, login_timeout=10, quiet=True, auto_prompt_reset=False)
            session_mock.logout.assert_called_with()
            new_instance._project.set_instance_config.assert_called_with('fooinst', username='ec2-user')

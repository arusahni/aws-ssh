# pylint: disable=redefined-outer-name,no-self-use,unused-argument,protected-access,missing-docstring,invalid-name,line-too-long
from io import StringIO
from collections import namedtuple
from unittest.mock import MagicMock, PropertyMock, patch, mock_open

import pytest
import six
from six.moves.configparser import ConfigParser  # pylint: disable=import-error

from aws_ssh import cli
from aws_ssh.interfaces import Environment
from fixtures import * # pylint: disable=import-error,wildcard-import

EnvironmentVars = namedtuple('EnvironmentVars', 'env config, config_values')

@pytest.fixture
def env_mock():
    with patch('aws_ssh.cli.Environment') as env_mock:
        yield env_mock

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
def open_mock():
    with patch('aws_ssh.cli.open', mock_open(), create=True) as opens:
        yield opens

@pytest.fixture
def prompt_mock():
    with patch('aws_ssh.cli.prompt_for_arg') as prompt_mock:
        yield prompt_mock

def test_print_ssh_args(exit_mock):
    with patch('aws_ssh.cli.get_ssh_args') as get_args:
        get_args.return_value = ('/path/to/test_key', 'test_user', '0.0.0.0')
        outstream = StringIO()
        cli.print_ssh_args(out=outstream)
        assert isinstance(get_args.call_args[0][0], list)
        output = outstream.getvalue().strip()
        assert output == '-i /path/to/test_key test_user@0.0.0.0'
        exit_mock.assert_called_with(170)

def test_init_environment():
    with patch('aws_ssh.cli.prompt_for_arg') as prompt_mock:
        environment = Environment()
        environment.set_key_root = MagicMock()
        environment.save = MagicMock()
        prompt_mock.return_value = '/path/to/key/root'
        cli.init_environment(environment)
        assert prompt_mock.call_count == 1
        call = prompt_mock.call_args[0]
        assert isinstance(call[0], cli.Argument)
        environment.set_key_root.assert_called_with('/path/to/key/root')

def test_prompt_for_arg():
    arg = cli.Argument('switch', 'metavar', 'description', 'prompt')
    outstream = StringIO()
    with patch('aws_ssh.cli.input') as input_mock:
        input_mock.return_value = 'foo'
        value = cli.prompt_for_arg(arg, out=outstream)
        output = outstream.getvalue().strip()
        assert arg.prompt in output
        assert value == 'foo'

def test_get_project_properties_all_specified():
    with patch('aws_ssh.cli.prompt_for_arg') as prompt_mock:
        args = {argname: 'foo' for argname, _ in six.iteritems(cli.ARGUMENTS)}
        props = cli.get_project_properties(args)
        assert prompt_mock.call_count == 0
        for prop in props.items():
            assert prop[0] in cli.ARGUMENTS
            assert prop[1] == 'foo'

def test_get_project_properties_one_specified(prompt_mock):
    args = {argname: 'foo' for argname, _ in six.iteritems(cli.ARGUMENTS)}
    removed = args.popitem()
    prompt_mock.return_value = 'bar'
    props = cli.get_project_properties(args)
    assert prompt_mock.call_count == 1
    prompt_mock.assert_called_with(cli.ARGUMENTS[removed[0]])
    for prop in props.items():
        if prop[0] == removed[0]:
            assert prop[1] == 'bar'
        else:
            assert prop[1] == 'foo'

def test_get_ssh_args_init_with_args(env_mock, exit_mock):
    env_create_args = ('project_name', 'prefix', 'profile', 'root', 'key')
    with patch('aws_ssh.cli.get_project_properties') as prop_mock:
        prop_mock.return_value.__getitem__.side_effect = lambda x: {key: key for key in env_create_args}[x]
        with pytest.raises(SystemExit):
            exit_mock.side_effect = SystemExit(-1)
            env_mock.is_initialized.return_value = True
            cli.get_ssh_args(['--init'])
        assert prop_mock.call_args[0][0]['initialize'] is True
        env_mock.return_value.create_project.assert_called_with(*env_create_args)
        exit_mock.assert_called_with(-1)

def test_get_ssh_args_no_instance_name(env_mock):
    with patch('os.getcwd') as cwd_mock:
        cwd_mock.return_value = '/path/to/cwd'
        project = MagicMock()
        env_mock.is_initialized.return_value = True
        env_mock.return_value.find_project.return_value = project
        with pytest.raises(SystemExit):
            cli.get_ssh_args([])
        env_mock.return_value.find_project.assert_called_with('/path/to/cwd')
        project.get_instance.assert_not_called()

def test_get_ssh_args_instance_name(env_mock, exit_mock):
    with patch('os.getcwd') as cwd_mock:
        cwd_mock.return_value = '/path/to/cwd'
        project = MagicMock()
        key_path_mock = PropertyMock(return_value='/path/to/key.pem')
        type(project).key_path = key_path_mock
        env_mock.is_initialized.return_value = True
        env_mock.return_value.find_project.return_value = project
        instance = MagicMock()
        ip_mock = PropertyMock(return_value='0.0.0.0')
        type(instance).ip = ip_mock
        instance.get_user_name.return_value = 'test_user'
        project.get_instance.return_value = instance
        args = cli.get_ssh_args(['fooinst'])
        env_mock.return_value.find_project.assert_called_with('/path/to/cwd')
        project.get_instance.assert_called_with('fooinst')
        key_path_mock.assert_called_with()
        instance.get_user_name.assert_called_with()
        ip_mock.assert_called_with()
        assert len(args) == 3
        assert args[0] == '/path/to/key.pem'
        assert args[1] == 'test_user'
        assert args[2] == '0.0.0.0'

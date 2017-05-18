"""Shared test fixtures."""
# pylint: disable=redefined-outer-name,no-self-use,unused-argument,protected-access,missing-docstring

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

import pytest

@pytest.fixture
def path_exists():
    with patch('os.path.exists') as path_exists:
        yield path_exists

@pytest.fixture
def mkdirs_mock():
    with patch('os.makedirs') as mkdirs_patch:
        yield mkdirs_patch

@pytest.fixture
def listdir_mock():
    with patch('os.listdir') as listdir_patch:
        yield listdir_patch

@pytest.fixture
def isfile_mock():
    with patch('os.path.isfile') as isfile_patch:
        yield isfile_patch

@pytest.fixture
def parser_mock():
    with patch('aws_ssh.interfaces.configparser.ConfigParser') as parser_mock:
        yield parser_mock

@pytest.fixture
def exit_mock():
    with patch('sys.exit') as exit_mock:
        yield exit_mock

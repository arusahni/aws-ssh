# AWS-SSH

SSH into your project-specific AWS EC2 instances by name, without having to
remember IP addresses & private keys, or a curating a SSH config.

Turn this: `ssh -i ~/.ssh/project-key.pem ubuntu@198.51.100.13`

Into this: `aws-ssh compute`

## Getting Started

### Prerequisites

AWS-SSH requires Python 2.7 or greater on a POSIX system. You will also need to
have [the AWS CLI](https://aws.amazon.com/cli/) installed and configured.

### Installing

Pip is the recommended method:

```console
$ pip install aws-ssh
```

I recommend installing this into a virtualenv, and then symlinking the binaries
to your PATH.  For example:

```console
$ mkvirtualenv -p $(which python3) aws-ssh # Python 3 recommended
$ pip install aws-ssh
# Assuming ~/bin/ is in your $PATH...
$ ln -s ~/.virtualenvs/aws-ssh/bin/{aws-ssh,awssh,ssh-ec2} ~/bin/
$ deactivate
```

You should now be able to use AWS-SSH outside of your virtualenv!

### Usage

Once installed, you need to create a project.  Projects are collections of EC2
instances that share a common set of parameters.  For example, I may be working
on the `squanch` project, with the following instances in my AWS account:

* squanch-compute - 198.51.100.13
* squanch-web - 198.51.100.14
* squanch-data - 198.51.100.15

Assuming I keep my `squanch`-related code in `~/code/squanch`, I will first
need to initialize an AWS-SSH project within that directory:

```console
$ cd ~/code/squanch
$ aws-ssh --init
Please provide the full path ot the directory containing all private keys: ~/.ssh/
Please provide a name for this project: squanch
Please provide the AWS profile to use: default
Please provide the name of the private key used for authentication (including extension): squanch.pem
Please provide the prefix for EC2 names: squanch-
Please provide the root directory for the project: ~/code/squanch
```

This will create an `.awssshconfig` file in the project root directory.  You
can manage it under version control to get the team on the same page :-)

Now that AWS-SSH has been configured, time to connect to an instance!

```console
$ cd ~/code/squanch
$ aws-ssh web
# Successful SSH connection to 198.51.100.14
```

Boom.

## Notes

* AWS-SSH attempts to guess the username for an instance by testing various
  usernames.  Right now, the sequence of user names is fixed (and based off
  common AMI usernames).  In a future release, this will be configurable.
* If your access is dependent on custom routing (e.g., behind a lazy VPN), you
  may need to abort the connection attempt (via `^C`) and manually add a route
  for the instance.

## Contributing

Contributions welcome! Be sure to use the development package, available under the `dev` extra.

```console
$ git clone git@github.com:arusahni/aws-ssh
$ cd aws-ssh
$ pip install -e .[dev]
```

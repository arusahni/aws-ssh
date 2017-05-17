## Datafiles

In project dir (or subdir): `aws-ssh instance-name`
Anywhere else: `aws-ssh project:instance-name`

When a project is registered:
`.awssshconfig` is added to the project rooot

Entry is written to `.awsssh/config`:

```ini
[project]
basedir = /path/to/project/dir
```

when a colon is detected in the instance name, AWS-SSH first tests for a global
config file, and then reads the config file at `basedir/.awssshconfig` to get
various settings.

### Overrides

`.awssshconfig` settings can be locally overridden: `aws-ssh --override propname propvalue`. Overrides are stored in `.awsssh/config`

```ini
[project]
basedir = /path/to/project/dir
propname = propvalue
```


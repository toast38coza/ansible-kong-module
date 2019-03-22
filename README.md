# Ansible Kong Module

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A collection of Ansible modules to configure the [Kong](http://getkong.com) API gateway.
Based on the original work of Cristo Crampton.

For an introduction to Kong + Ansible, take a look at [Kong Up and Running](http://blog.toast38coza.me/kong-up-and-running).


# Description

This package aims to provide a stable, idempotent Ansible module for the Kong API gateway.

# Requirements

- Ansible >=2.4
- ansible-dotdiff

# Usage

See [the example playbook](./example/playbook.yml).

# Limitations

* There's no backward compatibility with old Kong API objects.
  If you're still using them, consider a migration to Services and Routes.
* Idempotency for `basic-auth` is worked around, cause it's impossible to
  predict an execution result without comparing the new password to the old
  hash without updating it in Kong. Applying basic-auth credentials will cause
  a PATCH request to Kong on every execution.

# License

[MIT](https://github.com/Klarrio/ansible-kong-module/blob/master/LICENSE).

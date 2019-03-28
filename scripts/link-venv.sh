#!/bin/sh

# Run this script from the root of the repository to symlink module_utils/kong
# and modules/kong directories into the given virtualenv. This is useful for
# developing against a stable version of Ansible, without requiring a checkout
# of the Ansible git repository.

if [ ! -d "ansible/module_utils" ] || [ ! -d "ansible/modules" ]; then
  echo "E: ansible/module_utils or ansible/modules not found, run script from the root of the repository."
  exit 1
fi

if [ -z "$1" ]; then
  echo "E: Need exactly one parameter, the dir of the virtualenv."
  exit 1
fi

venv="$1"

if [ ! -d "$venv/bin" ] || [ ! -d "$venv/lib" ]; then
  echo "E: No bin/ or lib/ folders found in $venv, is this a venv?"
  exit 1
fi

echo "I: Linking modules/kong and module_utils/kong into all ${venv}'s interpreters"

find "$venv/lib" -maxdepth 1 -type d ! -path "$venv/lib" \
  -exec ln -vsf `pwd`/ansible/module_utils/kong {}/site-packages/ansible/module_utils \; \
  -exec ln -vsf `pwd`/ansible/modules/kong {}/site-packages/ansible/modules \;

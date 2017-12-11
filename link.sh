#!/bin/sh

if [ -z "$VIRTUAL_ENV" ]; then
  echo "E: Not running in a virtualenv, aborting."
  exit 1
fi

DEST=${VIRTUAL_ENV}/lib/python2.7/site-packages/ansible/

# Clean up links in module_utils
rm -f $DEST/module_utils/kong*.py

# Link all module_utils files into venv Ansible's module_utils
ln -sf $PWD/module_utils/*.py $DEST/module_utils/

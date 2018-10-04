import requests
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.kong_helpers import *
from ansible.module_utils.kong_plugin import KongPlugin

from ansible.module_utils.dotdiff import dotdiff

DOCUMENTATION = '''
---
module: kong_plugin
short_description: Configure a Kong Plugin object.
'''

EXAMPLES = '''
- name: Configure key-auth on mockbin
  kong_plugin:
    kong_admin_uri: http://localhost:8001
    name: key-auth
    api_name: mockbin
'''

MIN_VERSION = '0.14.0'


def main():
    ansible_module = AnsibleModule(
        argument_spec=dict(
            kong_admin_uri=dict(required=True, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            name=dict(required=True, type='str'),
            api_name=dict(required=False, type='str'),
            consumer_name=dict(required=False, type='str', default=False),
            config=dict(required=False, type='dict', default=dict()),
            state=dict(required=False, default="present", choices=['present', 'absent'], type='str'),
        ),
        supports_check_mode=True
    )

    # Initialize output dictionary
    result = {}

    # Admin endpoint & auth
    url = ansible_module.params['kong_admin_uri']
    auth_user = ansible_module.params['kong_admin_username']
    auth_pass = ansible_module.params['kong_admin_password']

    # Extract arguments
    state = ansible_module.params['state']
    name = ansible_module.params['name']
    api_name = ansible_module.params['api_name']
    consumer_name = ansible_module.params['consumer_name']
    config = ansible_module.params['config']

    # Convert consumer_name to bool if bool conversion evals to False
    if consumer_name == 'False':
        consumer_name = False

    # Create KongAPI client instance
    k = KongPlugin(url, auth_user=auth_user, auth_pass=auth_pass)

    # Contact Kong status endpoint
    kong_status_check(k, ansible_module)

    # Kong API version compatibility check
    kong_version_check(k, ansible_module, MIN_VERSION)

    # Default return values
    changed = False
    resp = ''

    # Check if the Plugin is already present
    pq = k.plugin_query(name, api_name=api_name, consumer_name=consumer_name)

    # ansible_module.fail_json(msg=pq)

    if len(pq) > 1:
        ansible_module.fail_json(
            msg='Got multiple results for Plugin query name: {}, api_name: {}, consumer_name: {}'.
                format(name, api_name, consumer_name))

    # Ensure the Plugin is installed on Kong
    if state == "present":
        if pq:
            # Extract the remote Plugin object into orig
            orig = pq[0]

            # Diff the remote Plugin object against the target data if it already exists
            plugindiff = dotdiff(orig.get('config'), config)

            # Set changed flag if there's a diff
            if plugindiff:
                # Log modified state and diff result
                changed = True
                result['state'] = 'modified'
                result['diff'] = [dict(prepared=render_list(plugindiff))]

        else:
            # We're inserting a new Plugin, set changed
            changed = True
            result['state'] = 'created'
            result['diff'] = dict(
                before_header='<undefined>', before='<undefined>\n',
                after_header=name, after={
                    'name': name,
                    'consumer_name': consumer_name,
                    'api_name': api_name,
                    'state': 'created',
                    'config': config
                }
            )

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and changed:
            try:
                resp = k.plugin_apply(name=name, config=config, api_name=api_name, consumer_name=consumer_name)
            except requests.HTTPError as e:
                ansible_module.fail_json(msg='Plugin configuration rejected by Kong.', name=name, config=config,
                                         api_name=api_name, consumer_name=consumer_name, response=e.response._content)

    # Delete the Plugin if it exists
    if state == "absent" and pq:

        # Check if the API exists
        orig = pq[0]

        # Predict a change if the Plugin exists
        changed = True
        result['state'] = 'deleted'
        result['diff'] = dict(
            before_header=name, before=orig,
            after_header='<deleted>', after='\n'
        )

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and orig:
            # Issue delete call to the Kong API
            try:
                resp = k.plugin_delete(name, api_name=api_name, consumer_name=consumer_name)
            except requests.HTTPError as e:
                app_err = "Error deleting Plugin."
                ansible_module.fail_json(msg=app_err, response=e.response._content)

    # Pass through the API response if non-empty
    if resp:
        result['response'] = resp

    # Prepare module output
    result.update(
        dict(
            changed=changed,
        )
    )

    ansible_module.exit_json(**result)


if __name__ == '__main__':
    main()

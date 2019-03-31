"""
ansible.modules.kong.kong_plugin performs Plugin operations on the Kong Admin API.

:authors: Timo Beckers
:license: MIT
"""
import requests
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dotdiff import dotdiff
from ansible.module_utils.kong.helpers import (kong_status_check,
                                               kong_version_check, render_list)
from ansible.module_utils.kong.plugin import KongPlugin

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
    service: mockbin
'''


def main():
    """Execute the Kong Plugin module."""
    ansible_module = AnsibleModule(
        argument_spec=dict(
            kong_admin_uri=dict(required=True, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            name=dict(required=True, type='str'),
            service=dict(required=False, type='str'),
            route=dict(required=False, type='str'),
            consumer=dict(required=False, type='str'),
            config=dict(required=False, type='dict', default=dict()),
            state=dict(required=False, default="present",
                       choices=['present', 'absent'], type='str'),
        ),
        supports_check_mode=True
    )

    # Admin endpoint & auth
    url = ansible_module.params['kong_admin_uri']
    auth_user = ansible_module.params['kong_admin_username']
    auth_pass = ansible_module.params['kong_admin_password']

    # Extract arguments
    state = ansible_module.params['state']
    name = ansible_module.params['name']
    service = ansible_module.params['service']
    route = ansible_module.params['route']
    consumer = ansible_module.params['consumer']
    config = ansible_module.params['config']

    # Create KongAPI client instance
    k = KongPlugin(url, auth_user=auth_user, auth_pass=auth_pass)
    kong_status_check(k, ansible_module)
    kong_version_check(k, ansible_module)

    # Default return values
    changed = False
    resp = ''
    diff = {}
    result = {}

    try:
        pq = k.plugin_query(name=name, service_name=service,
                            route_name=route, consumer_name=consumer)
    except Exception as e:
        ansible_module.fail_json(
            msg="Error querying plugin: '{}'.".format(e))

    if len(pq) > 1:
        ansible_module.fail_json(msg='Multiple results for Plugin query',
                                 results=pq, name=name, service=service, route=route, consumer=consumer)

    # Ensure the Plugin is configured.
    if state == "present":
        if pq:
            # Extract the remote Plugin object into orig
            orig = pq[0]

            # Diff the existing Plugin against the target data if it already exists.
            plugin_diff = dotdiff(orig.get('config'), config)
            if plugin_diff:
                # Log modified state and diff result.
                changed = True
                result['state'] = 'modified'
                diff = dict(prepared=render_list(plugin_diff))

        else:
            # Configure a new Plugin.
            changed = True
            result['state'] = 'created'
            diff = dict(
                before_header='<undefined>', before='<undefined>\n',
                after_header=name, after={
                    'name': name,
                    'service': service,
                    'route': route,
                    'consumer': consumer,
                    'config': config,
                    'state': 'created',
                }
            )

        if not ansible_module.check_mode and changed:
            try:
                resp = k.plugin_apply(name=name, config=config, service_name=service,
                                      route_name=route, consumer_name=consumer)
            except requests.HTTPError as e:
                ansible_module.fail_json(msg=str(e))

    # Ensure the Plugin is deleted.
    if state == "absent" and pq:

        # Check if the API exists
        orig = pq[0]

        # Predict a change if the Plugin exists
        changed = True
        result['state'] = 'deleted'
        diff = dict(
            before_header=name, before=orig,
            after_header='<deleted>', after='\n'
        )

        if not ansible_module.check_mode and orig:
            try:
                resp = k.plugin_delete(name, service_name=service, route_name=route,
                                       consumer_name=consumer)
            except requests.HTTPError as e:
                err_msg = "Error deleting Plugin."
                ansible_module.fail_json(
                    msg=err_msg, response=e.response._content)

    # Prepare module output.
    result.update(changed=changed)

    if resp:
        result['response'] = resp

    if diff:
        result['diff'] = diff

    ansible_module.exit_json(**result)


if __name__ == '__main__':
    main()

import requests
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dotdiff import dotdiff
from ansible.module_utils.kong.helpers import *
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

MIN_VERSION = '0.14.0'


def main():
    ansible_module = AnsibleModule(
        argument_spec=dict(
            kong_admin_uri=dict(required=True, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            name=dict(required=True, type='str'),
            service=dict(required=False, type='str'),
            route=dict(required=False, type='dict'),
            consumer=dict(required=False, type='str'),
            config=dict(required=False, type='dict', default=dict()),
            state=dict(required=False, default="present",
                       choices=['present', 'absent'], type='str'),
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
    service = ansible_module.params['service']
    route = ansible_module.params['route']
    consumer = ansible_module.params['consumer']
    config = ansible_module.params['config']

    # Convert consumer_name to bool if bool conversion evals to False
    # if consumer_name == 'False':
    # consumer_name = False

    # Create KongAPI client instance
    k = KongPlugin(url, auth_user=auth_user, auth_pass=auth_pass)

    # Contact Kong status endpoint
    kong_status_check(k, ansible_module)

    # Kong API version compatibility check
    kong_version_check(k, ansible_module, MIN_VERSION)

    # Default return values
    changed = False
    resp = ''

    try:
        # Check if the Plugin is already present
        pq = k.plugin_query(name=name, service_name=service,
                            route_attrs=route, consumer_name=consumer)
    except Exception as e:
        ansible_module.fail_json(
            msg="Error querying plugin: '{}'.".format(e))

    if len(pq) > 1:
        ansible_module.fail_json(
            msg='Got multiple results for Plugin query name: {}, service: {}, route: {}, consumer: {}'.
            format(name, service, route, consumer))

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
                    'service': service,
                    'route': route,
                    'consumer': consumer,
                    'state': 'created',
                    'config': config
                }
            )

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and changed:
            try:
                resp = k.plugin_apply(name=name, config=config, service_name=service,
                                      route_attrs=route, consumer_name=consumer)
            except requests.HTTPError as e:
                ansible_module.fail_json(msg='Plugin configuration rejected by Kong.', name=name, config=config,
                                         service=service, route=route, consumer=consumer, response=e.response._content)

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
                resp = k.plugin_delete(name, service_name=service, route_attrs=route,
                                       consumer_name=consumer)
            except requests.HTTPError as e:
                err_msg = "Error deleting Plugin."
                ansible_module.fail_json(
                    msg=err_msg, response=e.response._content)

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

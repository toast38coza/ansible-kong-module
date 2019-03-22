from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dotdiff import dotdiff
from ansible.module_utils.kong.helpers import *
from ansible.module_utils.kong.route import KongRoute

DOCUMENTATION = '''
---
module: kong_route
short_description: Configure a Kong Route object.
'''

EXAMPLES = '''
- name: configure a Route
  kong_route:
    kong_admin_uri: http://localhost:8001
    service: mockbin
    hosts:
      - mockbin.com
    state: present

- name: delete an Route
  kong_route:
    kong_admin_uri: http://localhost:8001
    service: mockbin
    hosts:
      - localhost
    paths:
      - /mockbin
    state: absent
'''

MIN_VERSION = '0.14.0'


def main():
    ansible_module = AnsibleModule(
        argument_spec=dict(
            kong_admin_uri=dict(required=True, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            service=dict(required=True, type='str'),
            protocols=dict(required=False, default=[
                           'http', 'https'], type='list'),
            hosts=dict(required=False, type='list'),
            paths=dict(required=False, default=[], type='list'),
            methods=dict(required=False, default=[], type='list'),
            strip_path=dict(required=False, default=True, type='bool'),
            preserve_host=dict(required=False, default=False, type='bool'),
            state=dict(required=False, default="present",
                       choices=['present', 'absent'], type='str'),
        ),
        required_if=[
            ('state', 'present', ['service']),
            ('state', 'absent', ['service']),
        ],
        required_one_of=[
            ('protocols', 'hosts', 'paths', 'methods')
        ],
        supports_check_mode=True
    )

    # Initialize output dictionary
    result = {}

    # Emulates 'required_one_of' argument spec, as it cannot be made conditional
    if ansible_module.params['state'] == 'present' and \
            ansible_module.params['protocols'] is None and \
            ansible_module.params['methods'] is None and \
            ansible_module.params['hosts'] is None and \
            ansible_module.params['paths'] is None:
        ansible_module.fail_json(
            msg="At least one of protocols, methods, hosts or paths is required when state is 'present'")

    # Kong 0.14.x
    api_fields = [
        'protocols',
        'methods',
        'hosts',
        'paths',
        'strip_path',
        'preserve_host'
    ]

    # Extract api_fields from module parameters into separate dictionary
    data = params_fields_lookup(ansible_module, api_fields)

    # Admin endpoint & auth
    url = ansible_module.params['kong_admin_uri']
    auth_user = ansible_module.params['kong_admin_username']
    auth_pass = ansible_module.params['kong_admin_password']

    # Extract other arguments
    service = ansible_module.params['service']
    state = ansible_module.params['state']

    # Create KongRoute client instance
    k = KongRoute(url, auth_user=auth_user, auth_pass=auth_pass)

    # Contact Kong status endpoint
    kong_status_check(k, ansible_module)

    # Kong API version compatibility check
    kong_version_check(k, ansible_module, MIN_VERSION)

    # Default return values
    changed = False
    resp = ''

    # Ensure the Route is registered in Kong
    if state == "present":

        # Check if the Route with same set of hosts, paths, methods and protocols exists
        orig = k.route_query(service, hosts=data['hosts'], paths=data['paths'],
                             methods=data['methods'], protocols=data['protocols'])

        if orig is not None:

            # Diff the remote Route object against the target data if it already exists
            routediff = dotdiff(orig, data)

            # Set changed flag if there's a diff
            if routediff:
                data['route_id'] = orig['id']
                # Log modified state and diff result
                changed = True
                result['state'] = 'modified'
                result['diff'] = [dict(prepared=render_list(routediff))]

        else:
            # We're inserting a new Route, set changed
            data['route_id'] = None
            changed = True
            result['state'] = 'created'
            result['diff'] = dict(
                before_header='<undefined>', before='<undefined>\n',
                after_header=service, after=data
            )

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and changed:
            try:
                resp = k.route_apply(service, **data)
            except Exception as e:
                err_msg = "Route configuration rejected by Kong: '{}'. " \
                          "Please check configuration of the API you are trying to configure."
                ansible_module.fail_json(msg=err_msg.format(e))

    # Ensure the Route is deleted
    if state == "absent":

        # Check if the Route exists
        orig = k.route_query(service, hosts=data['hosts'], paths=data['paths'],
                             methods=data['methods'], protocols=data['protocols'])

        # Predict a change if the API exists
        if orig:
            changed = True
            result['state'] = 'deleted'
            result['diff'] = dict(
                before_header=service, before=orig,
                after_header='<deleted>', after='\n'
            )

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and orig:
            # Issue delete call to the Kong API
            try:
                resp = k.route_delete(orig['id'])
            except Exception as e:
                ansible_module.fail_json(
                    msg='Error deleting Route: {}'.format(e))

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

"""
ansible.modules.kong.kong_route performs Route operations on the Kong Admin API.

:authors: Timo Beckers, Roman Komkov
:license: MIT
"""
import requests
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dotdiff import dotdiff
from ansible.module_utils.kong.helpers import (kong_status_check,
                                               params_fields_lookup,
                                               render_list)
from ansible.module_utils.kong.route import KongRoute

DOCUMENTATION = '''
---
module: kong_route
short_description: Configure a Kong Route object on a Service.
'''

EXAMPLES = '''
- name: create a named Route
  kong_route:
    kong_admin_uri: http://localhost:8001
    service: mockbin
    name: mockbin_com
    hosts:
      - mockbin.com

- name: delete a named Route
  kong_route:
    kong_admin_uri: http://localhost:8001
    service: mockbin
    name: mockbin_com
    state: absent
'''


def main():
    """Execute the Kong Route module."""
    ansible_module = AnsibleModule(
        argument_spec=dict(
            kong_admin_uri=dict(required=True, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            service=dict(required=True, type='str'),
            name=dict(required=False, type='str'),
            protocols=dict(required=False, default=['http', 'https'],
                           choices=['http', 'https', 'tcp', 'tls'], type='list'),
            methods=dict(required=False, default=[], type='list'),
            hosts=dict(required=False, default=[], type='list'),
            paths=dict(required=False, default=[], type='list'),
            snis=dict(required=False, default=[], type='list'),
            sources=dict(required=False, default=[], type='list'),
            destinations=dict(required=False, default=[], type='list'),
            strip_path=dict(required=False, default=True, type='bool'),
            preserve_host=dict(required=False, default=False, type='bool'),
            state=dict(required=False, default="present",
                       choices=['present', 'absent'], type='str'),
        ),
        supports_check_mode=True
    )

    # Initialize output dictionary
    result = {}

    # Emulates 'required_one_of' argument spec, as it cannot be made conditional
    if ansible_module.params['state'] == 'present' and \
            not ansible_module.params['protocols'] and \
            not ansible_module.params['methods'] and \
            not ansible_module.params['hosts'] and \
            not ansible_module.params['paths'] and \
            not ansible_module.params['snis'] and \
            not ansible_module.params['sources'] and \
            not ansible_module.params['destinations']:
        ansible_module.fail_json(
            msg="At least one of protocols, methods, hosts, paths, snis, " +
                "sources or destinations is required when state is 'present'")

    api_fields = [
        'protocols',
        'hosts',
        'paths',
        'methods',
        'snis',
        'sources',
        'destinations',
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
    name = ansible_module.params['name']
    state = ansible_module.params['state']

    # Create Kong client instance.
    k = KongRoute(url, auth_user=auth_user, auth_pass=auth_pass)
    kong_status_check(k, ansible_module)

    # Default return values
    changed = False
    resp = ''

    orig = None
    if name:
        # Route name is given, only manage a named object.
        orig = k.route_get(name)

        # Pass 'name' parameter to route_apply data.
        data['name'] = name
    else:
        try:
            # Check if a Route with these parameters already exists
            # without including the route name.
            rq = k.route_query(service, protocols=data['protocols'],
                               hosts=data['hosts'], paths=data['paths'], methods=data['methods'],
                               snis=data['snis'], sources=data['sources'], destinations=data['destinations'])
        except requests.HTTPError as e:
            ansible_module.fail_json(
                msg="Error querying Route: '{}'".format(e))

        if len(rq) > 1:
            ansible_module.fail_json(
                msg='Multiple results for Route query', results=rq)

        if rq:
            orig = rq[0]

    # Ensure the Route is configured.
    if state == "present":
        if orig:
            # Diff existing Route object against the target data if it already exists.
            routediff = dotdiff(orig, data)
            if routediff:
                changed = True
                result['state'] = 'modified'
                result['diff'] = [dict(prepared=render_list(routediff))]

        else:
            # Insert a new Route, set changed.
            changed = True
            result['state'] = 'created'
            result['diff'] = dict(
                before_header='<undefined>', before='<undefined>\n',
                after_header=service, after=data
            )

        if not ansible_module.check_mode and changed:
            try:
                resp = k.route_apply(service, **data)
            except requests.HTTPError as e:
                ansible_module.fail_json(
                    msg='Error applying Route: {}'.format(e))

    # Ensure the Route is deleted.
    if state == "absent":
        # Predict a change if the API exists.
        if orig:
            changed = True
            result['state'] = 'deleted'
            result['diff'] = dict(
                before_header=service, before=orig,
                after_header='<deleted>', after='\n'
            )

            if not ansible_module.check_mode:
                try:
                    resp = k.route_delete(orig['id'])
                except requests.HTTPError as e:
                    ansible_module.fail_json(
                        msg='Error deleting Route: {}'.format(e))

    # Prepare module output
    result.update(changed=changed)

    # Pass through the API response if non-empty
    if resp:
        result['response'] = resp

    ansible_module.exit_json(**result)


if __name__ == '__main__':
    main()

"""
ansible.modules.kong.kong_consumer performs Consumer operations on the Kong Admin API.

:authors: Timo Beckers
:license: MIT
"""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dotdiff import dotdiff
from ansible.module_utils.kong.consumer import KongConsumer
from ansible.module_utils.kong.helpers import (kong_status_check,
                                               kong_version_check, render_list)

DOCUMENTATION = '''
---
module: kong_consumer
short_description: Configure a Kong Consumer object.
'''

EXAMPLES = '''
- name: Configure a Consumer
  kong_consumer:
    kong_admin_uri: http://localhost:8001
    username: apiconsumer
    state: present

- name: Configure a list of Consumers
  kong_consumer:
    kong_admin_uri: http://localhost:8001
    username:
      - one
      - two
      - three
      - apiconsumers
    state: present

- name: Delete a Consumer
  kong_consumer:
    kong_admin_uri: http://localhost:8001
    username: apiconsumer
    state: absent
'''


def main():
    """Execute the Kong Consumer module."""
    ansible_module = AnsibleModule(
        argument_spec=dict(
            kong_admin_uri=dict(required=True, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            username=dict(required=True, type='list'),
            custom_id=dict(required=False, type='str'),
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

    # Extract other arguments
    state = ansible_module.params['state']
    users = ansible_module.params['username']
    custom_id = ansible_module.params['custom_id']

    if len(users) > 1 and custom_id:
        ansible_module.fail_json(
            msg="custom_id can only be given when managing a single Consumer")

    # Create Kong client instance
    k = KongConsumer(url, auth_user=auth_user, auth_pass=auth_pass)
    kong_status_check(k, ansible_module)
    kong_version_check(k, ansible_module)

    # Default return values
    changed = False
    resp = ''
    diff = []

    if state == 'present':

        # Ensure the list of Consumers is created.
        for username in users:
            data = {'username': username}
            if custom_id:
                # Will only be present with a single user.
                data['custom_id'] = custom_id

            # Check if the Consumer exists.
            orig = k.consumer_get(username)
            if orig is None:
                # Insert a new Consumer.
                changed = True
                diff.append(dict(
                    before_header='<undefined>', before='<undefined>\n',
                    after_header=username, after=data
                ))

            else:
                # Patch an existing Consumer.
                consumer_diff = dotdiff(orig, data)
                if consumer_diff:
                    # Log modified state and diff result.
                    changed = True
                    diff.append(dict(prepared=render_list(consumer_diff)))

            if not ansible_module.check_mode:
                try:
                    resp = k.consumer_apply(**data)
                except requests.HTTPError as e:
                    ansible_module.fail_json(msg=str(e))

    if state == 'absent':

        # Ensure the list of Consumers is deleted.
        for username in users:
            orig = k.consumer_get(username)
            if orig:
                # Delete the Consumer.
                changed = True
                diff.append(dict(
                    before_header=username, before=orig,
                    after_header='<deleted>', after='\n'
                ))

            if not ansible_module.check_mode and orig:
                try:
                    resp = k.consumer_delete(username)
                except requests.HTTPError as e:
                    ansible_module.fail_json(
                        msg='Error deleting Consumer: {}'.format(e))

    # Pass through the API response if non-empty
    if resp:
        result['response'] = resp

    # Pass through the diff result
    if diff:
        result['diff'] = diff

    # Prepare module output
    result.update(changed=changed)

    ansible_module.exit_json(**result)


if __name__ == '__main__':
    main()

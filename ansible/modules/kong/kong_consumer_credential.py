"""
ansible.modules.kong.kong_consumer_credential performs Consumer Credential operations on the Kong Admin API.

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
module: kong_consumer_credential
short_description: Configure an auth plugin for a Kong consumer.
'''

EXAMPLES = '''
- name: Configure a Consumer's API key
  kong_consumer_credential:
    kong_admin_uri: http://localhost:8001
    username: apiconsumer
    type: key-auth
    config:
      key: the-api-key
    state: present

The auth plugin configuration can be revoked by setting `state: absent`
on the resource. Since there can be an arbitrary amount of plugin
configurations for a Consumer, the `config` section needs to be identical.
Some plugins like basic-auth and hmac-auth have primary keys (eg. username)
and can be deleted by matching only the primary key.
'''

MIN_VERSION = '1.0.0'


def main():
    """Execute the Kong Consumer Credential module."""
    ansible_module = AnsibleModule(
        argument_spec=dict(
            kong_admin_uri=dict(required=True, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            username=dict(required=True, type='str'),
            type=dict(required=True, type='str',
                      choices=['acls', 'basic-auth', 'hmac-auth', 'key-auth', 'jwt', 'oauth2']),
            config=dict(required=False, type='dict', default=dict()),
            state=dict(required=False, type='str',
                       choices=['present', 'absent'], default='present'),
        ),
        supports_check_mode=True
    )

    # Initialize output dictionary
    result = {}

    # Admin endpoint & auth
    url = ansible_module.params['kong_admin_uri']
    auth_user = ansible_module.params['kong_admin_username']
    auth_pass = ansible_module.params['kong_admin_password']

    # Extract  arguments
    state = ansible_module.params['state']
    username = ansible_module.params['username']
    auth_type = ansible_module.params['type']
    config = ansible_module.params['config']

    # Create Kong client instance.
    k = KongConsumer(url, auth_user=auth_user, auth_pass=auth_pass)
    kong_status_check(k, ansible_module)
    kong_version_check(k, ansible_module, MIN_VERSION)

    # Default return values
    changed = False
    resp = ''
    diff = []

    try:
        # Check if the credential for the Consumer exists.
        cq = k.credential_query(username, auth_type, config=config)
    except ValueError as e:
        # Missing Consumer is not an error when state is 'absent'.
        if state == 'absent':
            ansible_module.exit_json(msg=str(e))

        ansible_module.fail_json(msg=str(e))
    except Exception as e:
        ansible_module.fail_json(
            msg="Error querying credential: '{}'.".format(e))

    if len(cq) > 1:
        ansible_module.fail_json(
            msg='Multiple results for credential query', results=cq)

    # Ensure the credential is configured.
    if state == 'present':
        if cq:
            if not ansible_module.check_mode:
                try:
                    resp = k.credential_apply(
                        username, auth_type, config=config)
                except Exception as e:
                    ansible_module.fail_json(msg=str(e))

                orig = cq[0]

                # Diff the remote API object against the target data if it already exists.
                cred_diff = dotdiff(orig, resp)

                # Set changed flag if there's a diff
                if cred_diff:
                    # Log modified state and diff result
                    changed = True
                    result['state'] = 'modified'
                    result['diff'] = [dict(prepared=render_list(cred_diff))]

        # Credential does not exist, create it.
        else:
            changed = True
            result['state'] = 'created'

            # Append diff entry
            diff.append(dict(
                before_header='<undefined>', before='<undefined>\n',
                after_header='{}/{}'.format(username, auth_type), after=config
            ))

            # Only make changes when Ansible is not run in check mode
            if not ansible_module.check_mode:
                try:
                    resp = k.credential_apply(
                        username, auth_type, config=config)

                except Exception as e:
                    ansible_module.fail_json(msg=str(e))

    # Ensure the Consumer is deleted
    if state == 'absent' and cq:

        # Get the first (and only) element of the query
        orig = cq[0]

        # Predict a successful delete if the Consumer Plugin is present
        changed = True
        result['state'] = 'deleted'

        diff.append(dict(
            before_header='{}/{}'.format(username, auth_type), before=orig,
            after_header='<deleted>', after='\n'
        ))

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode:
            # Issue delete call
            try:
                resp = k.credential_delete(
                    consumer_idname=username, auth_type=auth_type, config=config)
            except Exception as e:
                ansible_module.fail_json(msg=str(e))

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

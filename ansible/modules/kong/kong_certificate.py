from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dotdiff import dotdiff
from ansible.module_utils.kong.certificate import KongCertificate
from ansible.module_utils.kong.helpers import *

DOCUMENTATION = '''
---
module: kong_certificate
short_description: Configure a Kong Certificate object.
'''

EXAMPLES = '''
- name: Add a certificate to Kong
  kong_certificate:
    kong_admin_uri: http://localhost:8001
    sni: example.com
    cert: "{{ lookup('file', 'cert.pem') }}"
    key: "{{ lookup('file', 'key.pem') }}"
    state: present

- name: Delete a certificate
  kong_certificate:
    kong_admin_uri: http://localhost:8001
    sni: example.com
    state: absent
'''

MIN_VERSION = '0.14.0'


def main():
    ansible_module = AnsibleModule(
        argument_spec=dict(
            kong_admin_uri=dict(required=True, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            sni=dict(required=True, type='str'),
            cert=dict(required=False, type='str'),
            key=dict(required=False, type='str', no_log=True),
            state=dict(required=False, default="present",
                       choices=['present', 'absent'], type='str'),
        ),
        required_if=[
            ('state', 'present', ['sni', 'cert', 'key'])
        ],
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
    sni = ansible_module.params['sni']
    cert = ansible_module.params['cert']
    key = ansible_module.params['key']

    data = {
        'snis': [sni],
        'cert': cert.strip(),
        'key': key.strip()
    }

    # Create KongCertificate client instance
    k = KongCertificate(url, auth_user=auth_user, auth_pass=auth_pass)

    # Contact Kong status endpoint
    kong_status_check(k, ansible_module)

    # Kong API version compatibility check
    kong_version_check(k, ansible_module, MIN_VERSION)

    # Default return values
    changed = False
    resp = ''

    # Ensure the service is registered in Kong
    if state == "present":

        # Check if the service exists
        orig = k.certificate_get(sni)
        if orig is not None:

            # Diff the remote API object against the target data if it already exists
            certdiff = dotdiff(orig, data)

            # Set changed flag if there's a diff
            if certdiff:
                # Log modified state and diff result
                changed = True
                result['state'] = 'modified'
                result['diff'] = [dict(prepared=render_list(certdiff))]

        else:
            # We're inserting a new service, set changed
            changed = True
            result['state'] = 'created'
            result['diff'] = dict(
                before_header='<undefined>', before='<undefined>\n',
                after_header=sni, after='<hidden>'
            )

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and changed:
            try:
                resp = k.certificate_apply(**data)
            except Exception as e:
                app_err = "Certfificate configuration rejected by Kong: '{}'. " \
                          "Please check configuration of the certificate you are trying to configure."
                ansible_module.fail_json(msg=app_err.format(e))

    # Ensure the certificate is deleted
    if state == "absent":

        # Check if the certificate exists
        orig = k.certificate_get(sni)

        # Predict a change if the certfificate exists
        if orig:
            changed = True
            result['state'] = 'deleted'
            result['diff'] = dict(
                before_header=sni, before='<hidden>',
                after_header='<deleted>', after='\n'
            )

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and orig:
            # Issue delete call to the Kong service
            try:
                resp = k.certificate_delete(name)
            except Exception as e:
                ansible_module.fail_json(
                    msg='Error deleting certificate: {}'.format(e))

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

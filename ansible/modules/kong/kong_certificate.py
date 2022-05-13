"""
ansible.modules.kong.kong_certificate performs Certificate operations on the Kong Admin API.

:authors: Timo Beckers, Roman Komkov
:license: MIT
"""
import requests
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dotdiff import dotdiff
from ansible.module_utils.kong.certificate import KongCertificate
from ansible.module_utils.kong.helpers import (kong_status_check)

DOCUMENTATION = '''
---
module: kong_certificate
short_description: Configure a Kong Certificate object.
'''

EXAMPLES = '''
- name: Add a certificate to Kong
  kong_certificate:
    kong_admin_uri: http://localhost:8001
    snis:
      - example.com
      - example2.com
    cert: "{{ lookup('file', 'cert.pem') }}"
    key: "{{ lookup('file', 'key.pem') }}"

- name: Delete a certificate
  kong_certificate:
    kong_admin_uri: http://localhost:8001
    snis: example.com
    state: absent
'''


def main():
    """Execute the Kong Certificate module."""
    ansible_module = AnsibleModule(
        argument_spec=dict(
            kong_admin_uri=dict(required=True, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            snis=dict(required=True, type='list'),
            cert=dict(required=False, type='str'),
            key=dict(required=False, type='str', no_log=True),
            state=dict(required=False, default="present",
                       choices=['present', 'absent'], type='str'),
        ),
        required_if=[
            ('state', 'present', ['snis', 'cert', 'key'])
        ],
        supports_check_mode=True
    )

    # Admin endpoint & auth
    url = ansible_module.params['kong_admin_uri']
    auth_user = ansible_module.params['kong_admin_username']
    auth_pass = ansible_module.params['kong_admin_password']

    # Extract arguments
    state = ansible_module.params['state']
    snis = ansible_module.params['snis']
    cert = ansible_module.params['cert']
    key = ansible_module.params['key']

    if not snis:
        ansible_module.fail_json(msg="'snis' cannot be empty")

    # First SNI in the list to use in queries.
    sni = snis[0]

    data = {
        'snis': snis,
        'cert': cert.strip(),
        'key': key.strip()
    }

    # Create Kong client instance.
    k = KongCertificate(url, auth_user=auth_user, auth_pass=auth_pass)
    kong_status_check(k, ansible_module)

    # Default return values.
    result = {}
    changed = False
    resp = ''

    # Ensure the Certificate is configured.
    if state == "present":

        # Look up the first SNI in the list.
        orig = k.certificate_get(sni)
        if orig is not None:
            # Determine whether to report 'modified' or 'created'.
            certdiff = dotdiff(orig, data)
            if certdiff:
                changed = True
                result['state'] = 'modified'
        else:
            # Insert a new Certificate, set changed.
            changed = True
            result['state'] = 'created'

        if not ansible_module.check_mode and changed:
            try:
                resp = k.certificate_apply(**data)
            except requests.HTTPError as e:
                ansible_module.fail_json(
                    msg='Error applying Certificate: {}'.format(e))

    # Ensure the certificate is deleted
    if state == "absent":

        orig = k.certificate_get(sni)
        if orig:
            changed = True
            result['state'] = 'deleted'

        if not ansible_module.check_mode and orig:
            try:
                resp = k.certificate_delete(sni)
            except requests.HTTPError as e:
                ansible_module.fail_json(
                    msg='Error deleting Certificate: {}'.format(e))

    result.update(changed=changed)

    # Pass through the API response if non-empty.
    if resp:
        result['response'] = resp

    ansible_module.exit_json(**result)


if __name__ == '__main__':
    main()

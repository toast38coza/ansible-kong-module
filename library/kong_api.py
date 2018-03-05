#!/usr/bin/python

DOCUMENTATION = '''
---
module: kong
short_description: Configure a Kong API Gateway

'''

EXAMPLES = '''
- name: Register a site
  kong: 
    kong_admin_uri: http://127.0.0.1:8001/apis/
    name: "Mockbin"
    taget_url: "http://mockbin.com"
    request_host: "mockbin.com"    
    state: present

- name: Delete a site
  kong: 
    kong_admin_uri: http://127.0.0.1:8001/apis/
    name: "Mockbin"
    state: absent

'''

import json, requests, os


class KongAPI:
    def __init__(self, base_url, auth_username=None, auth_password=None):
        self.base_url = base_url
        if auth_username is not None and auth_password is not None:
            self.auth = (auth_username, auth_password)
        else:
            self.auth = None

    def __url(self, path):
        return "{}{}".format(self.base_url, path)

    def _api_exists(self, name, api_list):
        for api in api_list:
            if name == api.get("name", None):
                return True
        return False

    def add_or_update(self, name, upstream_url, hosts=None, uris=None, methods=None, strip_uri=False,
                      preserve_host=False, retries=5, upstream_connect_timeout=60000, upstream_send_timeout=60000,
                      upstream_read_timeout=60000, https_only=False, http_if_terminated=True):

        method = "post"
        url = self.__url("/apis/")
        api_list = self.list().json().get("data", [])
        api_exists = self._api_exists(name, api_list)

        if api_exists:
            method = "patch"
            url = "{}{}".format(url, name)

        data = {
            "name": name,
            "upstream_url": upstream_url,
            "strip_uri": strip_uri,
            "preserve_host": preserve_host,
            "retries": retries,
            "upstream_connect_timeout": upstream_connect_timeout,
            "upstream_send_timeout": upstream_send_timeout,
            "upstream_read_timeout": upstream_read_timeout,
            "https_only": https_only,
            "http_if_terminated": http_if_terminated
        }

        if hosts is not None:
            data['hosts'] = hosts
        if methods is not None:
            data['methods'] = methods
        if uris is not None:
            data['uris'] = uris

        return getattr(requests, method)(url, data, auth=self.auth)

    def list(self):
        url = self.__url("/apis")
        return requests.get(url, auth=self.auth)

    def info(self, id):
        url = self.__url("/apis/{}".format(id))
        return requests.get(url, auth=self.auth)

    def delete_by_name(self, name):
        info = self.info(name)
        id = info.json().get("id")
        return self.delete(id)

    def delete(self, id):
        path = "/apis/{}".format(id)
        url = self.__url(path)
        return requests.delete(url, auth=self.auth)


class ModuleHelper:
    def __init__(self, fields):
        self.fields = fields

    def get_module(self):

        args = dict(
            kong_admin_uri=dict(required=False, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            name=dict(required=False, type='str'),
            hosts=dict(required=False, type='str'),
            uris=dict(required=False, type='str'),
            methods=dict(required=False, type='str'),
            upstream_url=dict(required=False, type='str'),
            strip_uri=dict(required=False, default=False, type='bool'),
            preserve_host=dict(required=False, default=False, type='bool'),
            retries=dict(required=False, type='int', default=5),
            upstream_connect_timeout=dict(required=False, type='int', default=60000),
            upstream_send_timeout=dict(required=False, type='int', default=60000),
            upstream_read_timeout=dict(required=False, type='int', default=60000),
            https_only=dict(required=False, default=False, type='bool'),
            http_if_terminated=dict(required=False, default=True, type='bool'),
            state=dict(required=False, default="present", choices=['present', 'absent', 'latest', 'list', 'info'],
                       type='str'),
        )
        return AnsibleModule(argument_spec=args, supports_check_mode=False)

    def prepare_inputs(self, module):
        url = module.params['kong_admin_uri']
        auth_user = module.params['kong_admin_username']
        auth_password = module.params['kong_admin_password']
        state = module.params['state']
        data = {}

        for field in self.fields:
            value = module.params.get(field, None)
            if value is not None:
                data[field] = value

        return url, data, state, auth_user, auth_password

    def get_response(self, response, state):

        has_changed = False
        meta = dict()

        if state == "present":
            meta = response.json()
            has_changed = response.status_code in [201, 200]

        if state == "absent":
            has_changed = response.status_code == 204

        if state == "list":
            meta = response.json()

        return has_changed, meta


def main():
    fields = [
        'name',
        'hosts',
        'uris',
        'methods',
        'upstream_url',
        'strip_uri',
        'preserve_host',
        'retries',
        'upstream_connect_timeout',
        'upstream_send_timeout',
        'upstream_read_timeout',
        'https_only',
        'http_if_terminated'
    ]

    helper = ModuleHelper(fields)

    global module  # might not need this
    module = helper.get_module()
    base_url, data, state, auth_user, auth_password = helper.prepare_inputs(module)

    api = KongAPI(base_url, auth_user, auth_password)
    if state == "present":
        response = api.add_or_update(**data)
    if state == "absent":
        response = api.delete_by_name(data.get("name"))
    if state == "list":
        response = api.list()

    if response.status_code == 401:
        module.fail_json(msg="Please specify kong_admin_username and kong_admin_password", meta=response.json())
    elif response.status_code == 403:
        module.fail_json(msg="Please check kong_admin_username and kong_admin_password", meta=response.json())
    else:
        has_changed, meta = helper.get_response(response, state)
        module.exit_json(changed=has_changed, meta=meta)


from ansible.module_utils.basic import *
from ansible.module_utils.urls import *

if __name__ == '__main__':
    main()

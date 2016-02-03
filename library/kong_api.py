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

    def __init__(self, base_url):
        self.base_url = base_url

    def __url(self, path):
        return "{}{}" . format (self.base_url, path)

    def _api_exists(self, name, api_list):
        for api in api_list:
            if name == api.get("name", None):
                return True 
        return False

    def add_or_update(self, name, upstream_url, request_host=None, request_path=None, strip_request_path=False, preserve_host=False):

        method = "post"        
        url = self.__url("/apis/")
        api_list = self.list().json().get("data", [])
        api_exists = self._api_exists(name, api_list)

        if api_exists:
            method = "patch"
            url = "{}{}" . format (url, name)

        data = {
            "name": name,
            "upstream_url": upstream_url,
            "strip_request_path": strip_request_path,
            "preserve_host": preserve_host
        }
        if request_host is not None:
            data['request_host'] = request_host
        if request_path is not None:
            data['request_path'] = request_path

        return getattr(requests, method)(url, data)
        

    def list(self):
        url = self.__url("/apis")
        return requests.get(url)

    def info(self, id):
        url = self.__url("/apis/{}" . format (id))
        return requests.get(url)

    def delete_by_name(self, name):
        info = self.info(name)
        id = info.json().get("id")
        return self.delete(id)

    def delete(self, id):
        path = "/apis/{}" . format (id)
        url = self.__url(path)
        return requests.delete(url)

class ModuleHelper:

    def __init__(self, fields):
        self.fields = fields
    
    def get_module(self):

        args = dict(
            kong_admin_uri = dict(required=False, type='str'),
            name = dict(required=False, type='str'),
            upstream_url = dict(required=False, type='str'),
            request_host = dict(required=False, type='str'),    
            request_path = dict(required=False, type='str'),  
            strip_request_path = dict(required=False, default=False, type='bool'), 
            preserve_host = dict(required=False, default=False, type='bool'),         
            state = dict(required=False, default="present", choices=['present', 'absent', 'latest', 'list', 'info'], type='str'),    
        )
        return AnsibleModule(argument_spec=args,supports_check_mode=False)

    def prepare_inputs(self, module):
        url = module.params['kong_admin_uri']
        state = module.params['state']    
        data = {}

        for field in self.fields:
            value = module.params.get(field, None)
            if value is not None:
                data[field] = value

        return (url, data, state)

    def get_response(self, response, state):

        if state == "present":
            meta = response.json()
            has_changed = response.status_code in [201, 200]
            
        if state == "absent":
            meta = {}
            has_changed = response.status_code == 204

        if state == "list":
            meta = response.json()
            has_changed = False

        return (has_changed, meta)

def main():

    fields = [
        'name', 
        'upstream_url', 
        'request_host',
        'request_path',
        'strip_request_path',
        'preserve_host'
    ]

    helper = ModuleHelper(fields)

    global module # might not need this
    module = helper.get_module()  
    base_url, data, state = helper.prepare_inputs(module)

    api = KongAPI(base_url)
    if state == "present":
        response = api.add_or_update(**data)
    if state == "absent":
        response = api.delete_by_name(data.get("name"))
    if state == "list":
        response = api.list()
    
    has_changed, meta = helper.get_response(response, state)
    module.exit_json(changed=has_changed, meta=meta)


from ansible.module_utils.basic import *
from ansible.module_utils.urls import *

if __name__ == '__main__':
    main()


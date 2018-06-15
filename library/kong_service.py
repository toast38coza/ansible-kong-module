#!/usr/bin/python

DOCUMENTATION = '''
---
module: kong_service
short_description: Configure a Kong Service

'''

EXAMPLES = '''
- name: Register a service
  kong_service: 
    kong_admin_uri: http://127.0.0.1:8001/myservice/
    name: "myservice"
    retries: 5
    connect_timeout: 60000
    write_timeout: 60000
    read_timeout: 60000
    url: "http://172.23.0.21/myservice"
    state: present

- name: Delete a service
  kong_service: 
    kong_admin_uri: http://127.0.0.1:8001/myservice/
    name: "myservice"
    state: absent

'''

import json, requests, os

class KongService:

    def __init__(self, base_url, auth_username=None, auth_password=None):
        self.base_url = base_url
        if auth_username is not None and auth_password is not None:
            self.auth = (auth_username, auth_password)
        else:
            self.auth = None

    def __url(self, path):
        return "{}{}" . format (self.base_url, path)

    def _service_exists(self, name, service_list):
        for service in service_list:
            if name == service.get("name", None):
                return True 
        return False

    def add_or_update(self, name, url, retries=5, connect_timeout=60000, write_timeout=60000, read_timeout=60000):

        method = "post"        
        kong_url = self.__url("/services/")
        service_list = self.list().json().get("data", [])
        service_exists = self._service_exists(name, service_list)

        if service_exists:
            method = "patch"
            kong_url = "{}{}" . format (kong_url, name)

        data = {
            "name": name,
            "url": url,
            "retries": retries,
            "connect_timeout": connect_timeout,
            "write_timeout": write_timeout,
            "read_timeout": read_timeout
        }

        return getattr(requests, method)(kong_url, data, auth=self.auth)
        

    def list(self):
        url = self.__url("/services")
        return requests.get(url, auth=self.auth)

    def info(self, id):
        url = self.__url("/services/{}" . format (id))
        return requests.get(url, auth=self.auth)

    def delete_by_name(self, name):
        info = self.info(name)
        id = info.json().get("id")
        return self.delete(id)

    def delete(self, id):
        path = "/services/{}" . format (id)
        url = self.__url(path)
        return requests.delete(url, auth=self.auth)

class ModuleHelper:

    def __init__(self, fields):
        self.fields = fields
    
    def get_module(self):

        args = dict(
            kong_admin_uri = dict(required=False, type='str'),
            kong_admin_username = dict(required=False, type='str'),
            kong_admin_password = dict(required=False, type='str'),
            name = dict(required=False, type='str'),
            url = dict(required=False, type='str'),
            retries = dict(required=False, type='int'),    
            connect_timeout = dict(required=False, type='int'),    
            write_timeout = dict(required=False, type='int'),    
            read_timeout = dict(required=False, type='int'),    
            serviceid = dict(required=False, type='str'),
            state = dict(required=False, default="present", choices=['present', 'absent', 'latest', 'list', 'info'], type='str'),    
        )
        return AnsibleModule(argument_spec=args,supports_check_mode=False)

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

        return (url, data, state, auth_user, auth_password)

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
        'url', 
        'retries',
        'connect_timeout',
        'write_timeout',
        'serviceid',
        'read_timeout'
    ]

    helper = ModuleHelper(fields)

    global module # might not need this
    module = helper.get_module()  
    base_url, data, state, auth_user, auth_password = helper.prepare_inputs(module)

    service = KongService(base_url, auth_user, auth_password)
    if state == "present":
        response = service.add_or_update(**data)
    if state == "absent":
        if data.get("serviceid") is not None:
            response = service.delete(data.get("serviceid"))
        else:
            response = service.delete_by_name(data.get("name"))
    if state == "list":
        response = service.list()

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


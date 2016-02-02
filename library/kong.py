#!/usr/bin/python

DOCUMENTATION = '''
---
module: kong
short_description: Register sites with kong api gateway

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

class Kong:

    def __init__(self, base_uri):
        self.base_url = base_uri

    def call(self, path, data):
        print "calling"

    

class KongAPI(Kong):

    def __url(self, path):
        return "{}{}" . format (self.base_url, path)

    def add(self, name, upstream_url, request_host=None, request_path=None, strip_request_path=False, preserve_host=False):
        url = self.__url("/apis/")
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

        return requests.post(url, data)

    def upsert(self, name, upstream_url, request_host=None, request_path=None, strip_request_path=False, preserve_host=False):

        # does it exist? 
        response = self.info(name)
        if response.status_code == 404:
            self.add(name, upstream_url, request_host=None, request_path=None, strip_request_path=False, preserve_host=False)
        else:
            self.patch(name, upstream_url, request_host=None, request_path=None, strip_request_path=False, preserve_host=False)


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
        

class KongPlugin(Kong):

    def add(self, data):
        pass 

class KongConsumer(Kong):
    
    def add(self):
        pass       

## module utility methods:
def handle_present_state(module):

    url = module.params['kong_admin_uri']
    data = {
        "name":module.params['name'], 
        "upstream_url": module.params['upstream_url'], 
        "request_host": module.params['request_host'],        
    }
    return KongAPI(url).add(**data)    

def handle_delete_state(module):

    url = module.params['kong_admin_uri']
    return KongAPI(url).delete_by_name(module.params['name'])    

def get_module():

    args = dict(
        kong_admin_uri = dict(required=False, type='str'),
        name = dict(required=False, type='str'),
        upstream_url = dict(required=False, type='str'),
        request_host = dict(required=False, type='str'),    
        state = dict(required=False, default="present", choices=['present', 'absent', 'list', 'info'], type='str'),    
    )
    return AnsibleModule(argument_spec=args,supports_check_mode=False)
    


def main():
    '''
    ../../ansible/hacking/test-module -m ./kong.py -a "kong_admin_uri=http://192.168.99.100:8001/apis/ name=mockbin upstream_url=http://mockbin.com/ request_host=mockbin.com"
    ../../ansible/hacking/test-module -m ./kong.py -a "kong_admin_uri=http://staging.api.tangentmicroservices.com:8001/apis/ name=test upstream_url=http://10.133.16.85:8003/api/v1/ request_host=test.com"
    ../../ansible/hacking/test-module -m ./kong.py -a "kong_admin_uri=http://staging.api.tangentmicroservices.com:8001/apis/ name=test state=absent"
    '''
    global module
    module = get_module()

    state = module.params['state']

    if state == "present":
        success_status = [201]
        unchanged_status = [409]

        response = handle_present_state(module)   

        has_changed = response.status_code in success_status 
        module.exit_json(changed=has_changed, meta=response.json()) 

    if state == "absent":
        success_status = [204]
        unchanged_status = [404]        

        response = handle_delete_state(module)
        
        if response.status_code == 204:
            module.exit_json(changed=True, meta = {"status": "SUCCESS"})
        if response.status_code == 404:
            module.exit_json(changed=False, meta = {"status": "DOES NOT EXIST"})

        module.exit_json(changed=False, meta = json.dumps(response.content))


    if state == "list":
        success_status = [200]
        url = module.params['kong_admin_uri']
        response = KongAPI(url).list()
        response = requests.get(url)
        meta = {
            "url": url,
            "response": response.status_code,
            "text": response.content
        }
        module.exit_json(changed=False, meta=meta)

    
    
    
    



from ansible.module_utils.basic import *
from ansible.module_utils.urls import *

if __name__ == '__main__':
    main()
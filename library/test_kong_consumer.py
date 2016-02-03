import unittest, responses, requests, json, mock
from urlparse import parse_qsl, parse_qs
from kong_consumer import KongConsumer, ModuleHelper, main

from ansible.module_utils.basic import *


mock_kong_admin_url = "http://192.168.99.100:8001"

class KongPluginTestCase(unittest.TestCase):

	def setUp(self):
		self.api = KongConsumer(mock_kong_admin_url)

	@responses.activate
	def test_list(self):
		expected_url = "{}/consumers" . format(mock_kong_admin_url)
		responses.add(responses.GET, expected_url)
		response = self.api.list()

	@responses.activate
	def test_delete(self):
		
		expected_url = "{}/consumers/{}" . format(mock_kong_admin_url, 123)
		responses.add(responses.DELETE, expected_url, status=204)
		response = self.api.delete(123)

		assert response.status_code == 204

	@responses.activate 
	def test_add(self):

		expected_url = "{}/consumers" . format(mock_kong_admin_url)
		responses.add(responses.POST, expected_url, status=201)

		response = self.api.add(username='joesoap')
		assert response.status_code == 201

	@responses.activate 
	def test_add_invalid_inputs(self):
		self.assertRaises(AssertionError, self.api.add)



class ModuleHelperTestCase(unittest.TestCase):

	def setUp(self):
		self.helper = ModuleHelper()

	@mock.patch.object(ModuleHelper, 'get_response')
	@mock.patch.object(AnsibleModule, 'exit_json')
	@mock.patch.object(KongConsumer, 'add')
	@mock.patch.object(ModuleHelper, 'get_module')
	@mock.patch.object(ModuleHelper, 'prepare_inputs')
	def test_main_add(self, mock_prepare_inputs, mock_module, mock_add, mock_exit_json, mock_get_response):

		mock_prepare_inputs.return_value = (mock_kong_admin_url, "1","joesoap", "present")
		mock_get_response.return_value = (True, requests.Response())
		main()

		assert mock_add.called		

	@mock.patch.object(ModuleHelper, 'get_response')
	@mock.patch.object(AnsibleModule, 'exit_json')
	@mock.patch.object(KongConsumer, 'delete')
	@mock.patch.object(ModuleHelper, 'get_module')
	@mock.patch.object(ModuleHelper, 'prepare_inputs')
	def test_main_delete(self, mock_prepare_inputs, mock_module, mock_delete, mock_exit_json, mock_get_response):

		mock_prepare_inputs.return_value = (mock_kong_admin_url, "1","joesoap", "absent")
		mock_get_response.return_value = (True, requests.Response())
		main()

		assert mock_delete.called		
	
	@mock.patch.object(ModuleHelper, 'get_response')
	@mock.patch.object(AnsibleModule, 'exit_json')
	@mock.patch.object(KongConsumer, 'list')
	@mock.patch.object(ModuleHelper, 'get_module')
	@mock.patch.object(ModuleHelper, 'prepare_inputs')
	def test_main_list(self, mock_prepare_inputs, mock_module, mock_list, mock_exit_json, mock_get_response):

		mock_prepare_inputs.return_value = (mock_kong_admin_url, "1","joesoap", "list")
		mock_get_response.return_value = (True, requests.Response())
		main()

		assert mock_list.called				


	def test_prepare_inputs(self):
		class MockModule:
			pass

		mock_module = MockModule()
		mock_module.params = {
			'kong_admin_uri': mock_kong_admin_url,
			'state': 'present',
			'username': 'joesoap',
		}
		url, username, id, state = self.helper.prepare_inputs(mock_module)

		assert url == mock_kong_admin_url
		assert state == 'present'
		assert username == 'joesoap'
		assert id == None




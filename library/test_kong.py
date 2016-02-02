import unittest, responses, json, mock
from urlparse import parse_qsl, parse_qs
from kong_api import Kong, KongAPI, \
	handle_delete_state, handle_latest_state, handle_present_state

mock_kong_admin_url = "http://192.168.99.100:8001"

class MainTestCase(unittest.TestCase):

	def setUp(self):

		class MockModule: 
			pass

		self.module = MockModule()
		self.module.params = {
			"kong_admin_uri": "http://192.168.99.100:8001",
			"name":"mockbin", 
			"upstream_url":"http://mockbin.com", 
			"request_host" : "mockbin.com"
		}  

	def test_handle_delete_state(self):
		response = handle_delete_state(self.module)

	@mock.patch.object(KongAPI, "upsert")
	def test_handle_latest_state(self, mock_upsert):
		response = handle_latest_state(self.module)

		assert mock_upsert.called

	@mock.patch.object(KongAPI, "add")
	def test_handle_latest_state(self, mock_add):
		response = handle_latest_state(self.module)

		assert mock_add.called

		

class KongTestCase(unittest.TestCase):

	def setUp(self):
		self.kong = Kong(mock_kong_admin_url)

	def test_kong_call(self):
		pass

class KongAPITestCase(unittest.TestCase):

	def setUp(self):
		self.api = KongAPI(mock_kong_admin_url)

	@responses.activate
	def test_api_add(self):
		
		expected_url = '{}/apis/' . format (mock_kong_admin_url)
		responses.add(responses.POST, expected_url, status=201)

		request_data = {
			"name":"mockbin", 
			"upstream_url":"http://mockbin.com", 
			"request_host" : "mockbin.com"
		}
		response = self.api.add(**request_data)


		assert response.status_code == 201

		data = parse_qs(responses.calls[0].request.body)
		expected_keys = ['name', 'upstream_url', 'request_host', 'strip_request_path', 'preserve_host']
		for key in expected_keys:
			assert data.get(key, None) is not None, \
				"Expect all required data to have been sent. What was actually sent: {}" . format (data)

		num_calls = len(responses.calls)		
		assert num_calls == 1, \
		  "Expect exactly 1 call. got: {}" . format (num_calls)

	
	@responses.activate
	def test_api_upsert_update(self):
		"""A call to upsert with an existing API will create a valid PUT request"""
		
		expected_url = '{}/apis/mockbin' . format (mock_kong_admin_url)
		responses.add(responses.GET, expected_url, status=200)

		expected_url = '{}/apis/mockbin' . format (mock_kong_admin_url)
		responses.add(responses.PATCH, expected_url, status=200)

		request_data = {
			"name":"mockbin", 
			"upstream_url":"http://mockbin.com", 
			"request_host" : "mockbin.com"
		}
		response = self.api.upsert(**request_data)
		assert response.status_code == 200
		assert response.url =='{}/apis/mockbin' . format (mock_kong_admin_url), \
			"Expect call specific endpoint for API"

		data = parse_qs(responses.calls[1].request.body)
		expected_keys = ['name', 'upstream_url', 'request_host', 'strip_request_path', 'preserve_host']
		for key in expected_keys:
			assert data.get(key, None) is not None, \
				"Expect all required data to have been sent. What was actually sent: {}" . format (data)


	@mock.patch.object(KongAPI, "add")
	@responses.activate
	def test_api_upsert_add(self, mock_add):
		expected_url = '{}/apis/mockbin' . format (mock_kong_admin_url)
		responses.add(responses.GET, expected_url, status=404)

		request_data = {
			"name":"mockbin", 
			"upstream_url":"http://mockbin.com", 
			"request_host" : "mockbin.com"
		}
		self.api.upsert(**request_data)

		assert mock_add.called


	@responses.activate
	def test_list_apis(self):
		expected_url = '{}/apis' . format (mock_kong_admin_url)
		responses.add(responses.GET, expected_url, status=200)
		
		response = self.api.list()
		assert response.status_code == 200

	@responses.activate
	def test_api_info(self):
		expected_url = '{}/apis/123' . format (mock_kong_admin_url)
		responses.add(responses.GET, expected_url, status=200)
		response = self.api.info("123")

		assert response.status_code == 200

	@responses.activate
	def test_api_delete(self):

		expected_url = '{}/apis/123' . format (mock_kong_admin_url)
		responses.add(responses.DELETE, expected_url, status=204)
		response = self.api.delete("123")

		assert response.status_code == 204

	@responses.activate
	def test_api_delete_by_name(self):

		expected_get_url = '{}/apis/mockbin' . format (mock_kong_admin_url)
		get_body_response = {
			"upstream_url": "https://api.github.com",
			"id": "123",
			"name": "Github",
			"created_at": 1454348543000,
			"request_host": "github.com"
		}
		expected_del_url = '{}/apis/123' . format (mock_kong_admin_url)
		responses.add(responses.GET, expected_get_url, status=200, body=json.dumps(get_body_response))
		responses.add(responses.DELETE, expected_del_url, status=204)
		
		response = self.api.delete_by_name("mockbin")

		assert response.status_code == 204, \
			"Expect 204 DELETED response. Got: {}: {}" . format (response.status_code, response.content)

		
class KongPluginTestCase(unittest.TestCase):

	def setUp(self):
		self.api = KongPlugin(mock_kong_admin_url)




	
class IntegrationTests(unittest.TestCase):

	def setUp(self):
		self.api = KongAPI("http://192.168.99.100:8001")

	@unittest.skip("integration test")
	def test_add_api(self):

		request_data = {
			"name":"mockbin", 
			"upstream_url":"http://mockbin.com", 
			"request_host" : "mockbin.com"
		}
		response = self.api.add(**request_data)

		assert response.status_code in [201, 409], \
			"Expect status 201 Created. Got: {}: {}" . format (response.status_code, response.content)

if __name__ == '__main__':
    unittest.main()
import os
import requests
import json

from lib.project_path import ProjectPath
from lib.call_result import CallResult
from lib.store.update_context import UpdateContext
from lib.store.action import StatelessAction
from lib.store.help import Help
from requests_toolbelt.multipart.encoder import MultipartEncoder

# http://localhost:8082/shells/aHR0cHM6Ly9hYXMubXVycmVsZWt0cm9uaWsuY29tLzU4ODQxL2Fhcy8wLzAvMjAxNzEyMzQ1Njc4OQ
# http://localhost:8082/shells/aHR0cHM6Ly9hYXMubXVycmVsZWt0cm9uaWsuY29tLzU0NTMwL2Fhcy8wLzAvMjAxNzEyMzQ1Njc4OQ


class AASInstanceUpload(StatelessAction):
	def execute(self, asset:"Asset", context:UpdateContext, url:str, file:str, mime_type='multipart/form-data'):
		"""
		Uploads a file to the specified URL using a multipart/form-data request.

		:param url: base url for the request
		:param file: Path to the file to be uploaded.
		:return: Response object from the server.
		"""
		# url = 'http://localhost:8082/upload'
		file_path = ProjectPath.local(file)
		file_size = os.path.getsize(file_path)
		headers = {
			"Content-Length": str(file_size),
			'Content-Type': mime_type
		}

		try:
			# The 'files' parameter of requests handles the multipart/form-data content type.
			with open(file_path, 'rb') as file:
				encoder = MultipartEncoder(
					fields={"file": (file_path, file, "application/octet-stream")}
				)

				headers = {
					"Content-Type": encoder.content_type,  # Includes the boundary automatically
				}

				response = requests.post(url, data=encoder, headers=headers)

				# files = {'file': file}
				# response = requests.post(url, headers=headers, files=files)
				# response = requests.post(url, files=files)
				print("Status Code:", response.status_code)
				print("Response Text:", response.text)
		except Exception as ex:
			return CallResult.of(ex)

		return CallResult.of(response)

	def get_help(self):
		return Help.make(
			'Upload an AAS instance to the repos',
			'CallResult',
			url='str - base url for the request',
			file='path to the instance file'
		)


class AASInstancePut(StatelessAction):
	def execute(
			self,
			asset:"Asset",
			context:UpdateContext,
			url:str,
			file:str=None,
			data:object=None,
			mime_type='multipart/form-data'
	):
		"""
		Uploads a file to the specified URL using a multipart/form-data request.

		:param url: base url for the request
		:param file: Path to the file to be uploaded.
		:return: Response object from the server.
		"""
		if file is None and data is None:
			raise ValueError('either "file" or "data" is required')

		if file and data:
			raise ValueError('either "file" or "data" is required but not both')

		# url = 'http://localhost:8082/upload'
		headers = {
			'Content-Type': mime_type
		}

		try:
			# The 'files' parameter of requests handles the multipart/form-data content type.
			if data is None:
				with open(ProjectPath.local(file), 'r') as file:
					data = file.read()
			response = requests.put(url, headers=headers, data=data)
		except Exception as ex:
			return CallResult.of(ex)

		return CallResult.of(response)

	def get_help(self):
		return Help.make(
			'Upload an AAS instance to the repos',
			'CallResult',
			url='str - base url for the request',
			file='path to the instance file'
		)


class AASInstanceDownload(StatelessAction):
	def execute(self, asset:"Asset", context:UpdateContext, url:str):
		"""
		:param url: base url for the request
		:return: Response object from the server.
		"""

		try:
			# The 'files' parameter of requests handles the multipart/form-data content type.
			response = requests.get(url)
		except Exception as ex:
			return CallResult.of(ex)

		return CallResult.of(response)

	def get_help(self):
		return Help.make(
			'Upload an AAS instance to the repos',
			'CallResult',
			url='str - base url for the request',
			file='path to the instance file'
		)


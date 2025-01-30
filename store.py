import json
import requests
from idlelib.replace import replace

from flask import Flask, request, jsonify, Response
from lib.project_path import ProjectPath
from lib.fsutil import text_file_content
from lib.persistence import to_json
from lib.call_result import ErrorResult

from lib.store.user_registry import UserRegistry
from lib.store.asset_store import AssetStore, AssetFileStorage
from lib.store.update_context import UpdateContext
from lib.store.asset import Asset
from lib.store.action_registry import ActionRegistry

from lib.store.actions.file_directory import FileDirectory
from lib.store.actions.json_format import JsonFormat
from lib.store.actions.base64_encoding import Base64Encoding
from lib.store.actions.update_action import UpdateAssetAction

from app.actions.aas.instance.demo1_submit import InstanceDemoStep1
from app.actions.aas.instance.shell_finalized_upload import ShellFinalizer
from app.actions.aas.instance.upload_instance import AASInstanceDownload

from lib.store.actions.read_dir import ReadDir
from lib.store.actions.get_help import GetHelp
from lib.store.actions.get_asset_info import GetAssetInfo
import lib.store.actions.call_asset

from app.actions.tool.qrcode import QrEncode
from app.actions.aas.instance.test import Test1

from app.test.active_asset import TestActiveAction
from app.test.call_method import TestDispatchToMember


MAX_BODY_SIZE = 1_000_000

app = Flask(__name__)
global std_context
std_context: UpdateContext = None


# @app.route('/')
# def index():
# 	return text_file_content(ProjectPath.local('[]/data/html/start.html'))

def _make_user_registry():
	user_registry = UserRegistry()
	user_registry.make_entity("root")
	user_registry.make_entity("alice")
	user_registry.make_entity("bob")
	user_registry.make_entity("charly")

	user_registry.make_entity("system")
	user_registry.make_entity("team")
	user_registry.make_entity("developers")

	# all team members are devs
	user_registry.add_layer_to_entity("root", "system")
	user_registry.add_layer_to_entity("team", "developers")

	# bob is a member of the team
	user_registry.add_layer_to_entity("bob", "team")
	return user_registry


def store_setup():
	user_registry = _make_user_registry()
	store = AssetStore(storage=AssetFileStorage('[]/store'))
	store.load()

	context = UpdateContext(
		store=store,
		user_registry=user_registry,
		user='root',
		group='system'
	)
	return context


def create_basic_assets():
	# read_dir_asset = Asset(ReadDir())
	# std_context.store.store(std_context, read_dir_asset, path='bin.ls', mode='775')

	file_serve = Asset(FileDirectory().set_base_path('[]/data/www'))
	std_context.store.store(std_context, file_serve, path='www.files', mode='775')

	base64_encoding = Asset(Base64Encoding())
	std_context.store.store(std_context, base64_encoding, path='bin.base64', mode='775')

	instance_demo_1 = Asset(InstanceDemoStep1())
	std_context.store.store(std_context, instance_demo_1, path='app.aas.instance.demo', mode='775')

	demo_finalizer_1 = Asset(ShellFinalizer())
	std_context.store.store(std_context, demo_finalizer_1, path='app.aas.instance.finalize', mode='775')

	download_instance = Asset(AASInstanceDownload(), url='http://localhost:8082/shells')
	std_context.store.store(std_context, download_instance, path='app.aas.instance.shells', mode='775')

	test_instance = Asset(Test1())
	std_context.store.store(std_context, test_instance, path='app.aas.instance.test1', mode='775')

	p1_instance = Asset(
		AASInstanceDownload(),
		url='http://localhost:8082/shells/aHR0cHM6Ly9hYXMubXVycmVsZWt0cm9uaWsuY29tLzU0NTMwL2Fhcy8wLzAvMjAxNzEyMzQ1Njc4OQ'
	)
	std_context.store.store(std_context, p1_instance, path='app.aas.instance.source.intern.54530', mode='775')

	p2_instance = Asset(
		AASInstanceDownload(),
		url='http://localhost:8082/shells/aHR0cHM6Ly9hYXMubXVycmVsZWt0cm9uaWsuY29tLzU4ODQxL2Fhcy8wLzAvMjAxNzEyMzQ1Njc4OQ'
	)
	std_context.store.store(std_context, p2_instance, path='app.aas.instance.source.intern.58841', mode='775')

	p1_filtered = Asset(
		JsonFormat(),
		path='app.aas.instance.source.intern.54530'
	)
	std_context.store.store(std_context, p1_filtered, path='app.aas.instance.intern.54530', mode='775')

	p2_filtered = Asset(
		JsonFormat(),
		path='app.aas.instance.source.intern.58841'
	)
	std_context.store.store(std_context, p2_filtered, path='app.aas.instance.intern.58841', mode='775')
    
	# add actions from action registry:
	ActionRegistry.create_registered_actions(std_context)
	pass

# curl --location --request PUT 'http://localhost:8082/submodels/aHR0cHM6Ly9hYXMubXVycmVsZWt0cm9uaWsuY29tLzU0NTMwL3NtLzAvMC8yMDE3MTIzNDU2Nzg5L3RpbWVzZXJpZXM/submodel-elements/Segments' --header 'Content-Type: application/json' --data @demo_segments_leer.json


@app.route('/', methods=['GET', 'POST'])
def process():
	# Collect all URL parameters (query string or route parameters)
	parameters = {key: value for key, value in request.args.items()}

	# If the request is POST, add the body to the parameters dictionary
	if request.method == 'POST':
		# Check the content length
		content_length = request.content_length
		if content_length and content_length > MAX_BODY_SIZE:
			return jsonify({"error": "Request body exceeds maximum allowed size."}), 413

		# Check if JSON body is provided
		if request.is_json:
			parameters['body'] = request.get_json()
		# Check if form data is provided
		elif request.form:
			parameters.update({key: value for key, value in request.form.items()})
		# Otherwise, include raw data
		else:
			parameters['body'] = request.get_data()

	asset_path = 'www.index'
	if 'asset' in parameters:
		asset_path = parameters.get('asset')
		del parameters['asset']

	# set up call context and default mimetype
	call_context = UpdateContext(**std_context)
	call_context['mimetype'] = 'application/json'

	try:
		asset: Asset = call_context.store.acquire(call_context, asset_path)
	except Exception as ex:
		return ErrorResult.from_exception(ex).to_json()
	if asset is None:
		return jsonify({'error': f'asset not found: {asset_path}'})

	updated_asset = asset.update(call_context, **parameters)
	result = updated_asset.get_result()
	if result.is_error():
		return f'<pre>{json.dumps(result.as_json(), indent=2)}</pre>'

	reply = result.get_result()
	if call_context['mimetype'] == 'application/json':
		if not isinstance(reply, requests.models.Response):
			return Response(to_json(reply), mimetype=call_context['mimetype'])

	return Response(reply, mimetype=call_context['mimetype'])


if __name__ == '__main__':
	def main():
		global std_context
		std_context = store_setup()
		# create_basic_assets()
		#  app.run('0.0.0.0', 5001, debug=True)
		app.run('0.0.0.0', 5001)

	main()

import base64
import qrcode
import io

from lib.store.action import StatelessAction
from lib.store.help import Help
from lib.store.action_registry import ActionRegistry


def to_qrcode_png(qr_image):
	# Create an in-memory bytes buffer
	buffered = io.BytesIO()

	# Save the QR code image as PNG to the buffer
	qr_image.save(buffered, format="PNG")
	return buffered.getvalue()


def qr_encode(data: str):
	image = qrcode.make(data)
	return to_qrcode_png(image)


def qrcode_to_html_img(qr_image):
	"""
	Converts a qrcode.image.pil.PilImage object into an HTML <img> tag with a Base64-encoded source.

	Parameters:
		qr_image (qrcode.image.pil.PilImage): The QR code image to convert.

	Returns:
		str: An HTML <img> tag with a Base64-encoded source and the assigned class "qrcode".
	"""
	png_image = to_qrcode_png(qr_image)

	# Encode the image bytes in Base64
	base64_image = base64.b64encode(png_image).decode("utf-8")

	# Create the HTML <img> tag
	html_img_tag = f'<img src="data:image/png;base64,{base64_image}" alt="QR Code" class="qrcode">'

	return html_img_tag


@ActionRegistry.store_asset('app.qrcode.encode', user='root', group='system', mode='775')
class QrEncode(StatelessAction):
	"""
	Encode a string into a QR-code PNG.

	Returns:
		byte[]: the png image as bytes.

	Args:
		data (str): len<4000 -- the data to be encoded

	"""
	def execute(self, asset, context, data:str, **kwargs):
		if len(data) > 4000:
			raise ValueError('max size set to 4000')

		context['mimetype'] = 'image/png'
		return qr_encode(data)

	def get_help(self):
		return Help.from_docstring(self.__doc__)

import docstring_parser
from lib.persistence import BasicPersistentObject


class Variant(BasicPersistentObject):
	def __init__(self, returns, **kwargs):
		self.returns = returns
		self.param = kwargs

	def ctor_parameter(self):
		return {
			'returns': self.returns,
			**self.param
		}

	def entry(self):
		return {
			'returns': self.returns,
			'param': self.param
		}


class Help:
	@staticmethod
	def make(summary, returns, **parameter):
		return {
			'description': summary,
			'args': parameter,
			'returns': returns
		}

	@staticmethod
	def from_docstring(doc: str) -> dict:
		"""
		Parse a docstring to extract its general description, arguments, and return information using `docstring-parser`.

		Args:
			doc (str): The docstring to parse.

		Returns:
			dict: A JSON-compatible dictionary representation of the docstring.
		"""
		if not doc:
			return {"description": None, "args": [], "returns": None}

		# Parse the docstring
		parsed = docstring_parser.parse(doc)

		# Build the result dictionary
		result = {"description": parsed.short_description, "args": [], "returns": None}

		# Extract arguments
		for param in parsed.params:
			result["args"].append({
				"name": param.arg_name,
				"type": param.type_name,
				"description": param.description,
			})

		# Extract return information
		if parsed.returns:
			result["returns"] = {
				"type": parsed.returns.type_name,
				"description": parsed.returns.description,
			}

		return result

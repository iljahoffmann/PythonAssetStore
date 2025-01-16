#!/usr/bin/env python
# -*- coding: latin-1 -*-
import os
import platform
import glob


def select_files(directory, selector=None):
	for root, dirs, files in os.walk(directory):
		for file in files:
			path = os.path.join(root, file)
			if selector is None or selector(path):
				yield path


def apply_replacements(the_content:str, **replacements):
	text = the_content
	for pattern in replacements:
		replacement = replacements[pattern]
		if callable(replacement):
			replacement = replacement()
		text = text.replace(pattern, replacement)
	return text


def text_file_content(filename:str, replacements=None):
	with open(filename, 'r', encoding='utf8') as fd:
		content = fd.read()
		if replacements is not None:
			content = apply_replacements(content, **replacements)

		return content


def path_parts(path):
	"""
	Split path into its components. First element results in '/' under Linux and a drive identifier under Windows.
	"""
	parts = os.path.abspath(path).split(os.path.sep)
	if platform.system() == 'Windows':
		if len(parts[0]) == 2 and parts[0][1] == ':':
			parts[0] = f'{parts[0]}\\'
	elif platform.system() == 'Linux':
		if len(parts[0]) == 0:
			parts[0] = '/'

	return parts


def get_files(directory, key=os.path.getmtime):
	glob_pattern = os.path.join(directory, '**')
	list_of_files = filter(os.path.isfile, glob.glob(glob_pattern, recursive=True))
	result = list(sorted(list_of_files, key=key))
	return result


def files_in_directory(directory):
	"""
	List all files in the given directory, but not in its subdirectories.
	:param directory: Path to the directory
	:return: A list of file names
	"""
	return [file for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file))]


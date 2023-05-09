#!/usr/bin/env python

"""

This module recrate redirect.htm files the URLs that does not include 
any `latest` or `version` base URI. 
"""


import argparse
import os
import glob
from jinja2 import Template

parser = argparse.ArgumentParser()


parser.add_argument('-src', '--source') 
parser.add_argument('-base', '--base')


args=parser.parse_args()



for (dirpath, dirnames, filenames) in os.walk(args.source):

    with open('scripts/docs/redirect.html', 'rb') as f:
        template= Template(f.read().decode('utf-8'), 
                           autoescape=True,
                           keep_trailing_newline=True)
        href= f"/latest{dirpath.replace(args.base, '')}"
        index_html = template.render(href=href)

        # Overwrite index html
        with open(os.path.join(dirpath, 'index.html'), '+w') as file:
            file.write(index_html)
            file.close()

        # Remove md files and ipynb files from save same space from disk
        files= glob.glob((os.path.join(dirpath, '*.md')))
        for f in files:
            os.remove(f)

        files= glob.glob((os.path.join(dirpath, '*.ipynb')))
        for f in files:
            os.remove(f)
import os
import datetime

from flask import jsonify, request
from app import app
from schemas import ListDataFolder

from . import api
from utils import success, error, validate_json, validate_request_data, response, file_stats
from db import database


@api.route('/repository/list', methods=['POST'])
@validate_request_data(schema=ListDataFolder)
def list_data_path():
    """ API endpoint to list folders in the data path of the node.
        It only allows the list files in the basis of data path.

    Request {application/json}:

        path (list): List that includes folders in hierarchical order.

    Response {application/json}:
        400:
            success   : Boolean error status (False)
            result  : null
            message : Message about error. Can be exceptions from
                     os.path methods
        200:
            success: Boolean value indicates that the request is success
            result: List of items in the requested path as objects
            message: The message for response
    """

    req = request.json
    req_path = req['path']

    # Full path by including the base DATA_PATH
    dpath = os.path.join(app.config["DATA_PATH_RW"], *req_path)

    # Check if the path is existed, or it is a directory
    if os.path.exists(dpath) and os.path.isdir(dpath):
        base = os.sep if len(req_path) == 0 else os.path.join(*req_path)
        try:
            files = os.listdir(dpath)
        except Exception as e:
            return error(str(e)), 400

        res = {
            'level': len(req_path),
            'base': base,
            'files': [],
            'number': len(files),
            'displays': len(files) if len(files) <= 1000 else 1000,
            'path': req_path
        }

        files = files if len(files) <= 1000 else files[0:1000]

        table = database.db().table_datasets()
        query = database.query()

        for file in files:
            if not file.startswith('.'):
                fullpath = os.path.join(dpath, file)
                path_type = 'file' if os.path.isfile(fullpath) else 'dir'
                extension = os.path.splitext(fullpath)[1]

                # Get dataset registered with full path
                dataset = table.get(query.path == fullpath)

                # Get file statistics
                cdate, size = file_stats(fullpath, req['refresh'])

                # Folder that includes any data file
                includes = []
                if not dataset and os.path.isdir(fullpath):
                    includes = table.search(query.path.matches('^' + os.path.join(fullpath, '')))

                # This is the path that will be displayed on the GUI
                # It is created as list to be able to use it with `os.path.join`
                exact_path = [*req_path, file]


                res['files'].append({"type": path_type,
                                     "name": file,
                                     "path": exact_path,
                                     "extension": extension,
                                     'registered': dataset,
                                     'includes': includes,
                                     'created': cdate,
                                     'size': size})
        return response(res), 200

    else:

        return error(f'Requested path does not exist or it is not a directory. {req_path}')

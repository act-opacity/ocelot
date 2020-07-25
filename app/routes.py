import sys, json, os, time
from flask import jsonify, render_template, request, flash
from app import app
from app import db
from app.db_models import Account
from app.functions import get_short_handle, convert_js_bool_to_python, get_account_dir_path, \
    get_account_metadata_dir_path, object_as_dict, create_directory, get_local_path, time_expired
from celery import Celery, signature

celery = Celery()
celery.conf.task_routes = json.loads(os.environ.get("CELERY_ROUTES"))

@app.route('/')
@app.route('/index')
def index():
    headers = [
        ['File Name'],
        ['Type'],
        ['Directory'],
        ['Full Path'],
        ['Size'],
        ['Last Modified Date/Time'],
        ['Share Link'],
        ['Synced Y/N'],
        ['File Handle'],
        ['Version History']
        ]

    return render_template('index.html', headers=headers)

@app.route('/account/get-all', methods=['POST'])
def load_accounts():
    try:
        accounts = Account.query.all()
        build_result = []
        for account in accounts:
            build_result.append(object_as_dict(account, db))
        for account in build_result:
            account['handle'] = get_short_handle(account["handle"])
    except:
        print (f"Unexpected error: {sys.exc_info()[0]}")
        return "failed"

    return jsonify(build_result)

@app.route('/account/add-new', methods=['POST'])
def new_account():
    handle_name = request.form.get('handle_name')
    handle = request.form.get('handle')
    task_result = celery.signature("primary.get_account_details", 
        kwargs={'account_handle': handle, 'handle_name': handle_name}).delay().get()

    if task_result:
        # create unique local directory for syncing files for this account
        acct_dir = get_account_dir_path(handle)
        print("Creating account directory path as needed:")
        print(acct_dir)
        create_directory(acct_dir)

        # create unique local directory for storing account metadata
        meta_dir = get_account_metadata_dir_path(handle)
        print("Creating account metadata directory path as needed:")
        print(meta_dir)
        create_directory(meta_dir)

        # build initial file index
        in_progress = False
        if os.path.exists(f"{meta_dir}/process.lock") and not time_expired(5, f"{meta_dir}/process.lock"):
            in_progress = True

        if not os.path.exists(f"{meta_dir}/merged.json") and not in_progress:
            celery.signature("primary.refresh_table_data", 
                kwargs={"account_handle": handle}).delay()

        return "success"
    else:
        print("Unable to retrieve account from handle provided. Failed.")
        return "failed. maybe handle is wrong?"

@app.route('/account/delete', methods=['POST'])
def delete_account():
    try:
        id = request.form.get('handle_id')
        row = Account.query.filter(Account.id == id).first()
        # remove local account files and parent directory if delete_files_bool
        # otherwise delete only the metadata directory which contains json data of account
        delete_files_bool = convert_js_bool_to_python(request.form.get('delete_files_bool'))
        celery.signature("primary.remove_local_account_data", 
            kwargs={"account_handle": row.handle, "delete_files_bool": delete_files_bool}).delay().get()
        Account.query.filter(Account.id == id).delete()
        db.session.commit()
        return "Account successfully removed"
    except Exception:
        Account.query.filter(Account.id == id).delete()
        db.session.commit()
        return "Error: either failed to remove account's local data completely or the cleanup happened previously."

@app.route('/account/load-data', methods=['POST'])
def load_account_data():
    id = request.form.get('handle_id')
    refresh = convert_js_bool_to_python(request.form.get('refresh'))
    row = Account.query.filter(Account.id == id).first()
    
    dir_path = get_account_metadata_dir_path(row.handle)
    if not os.path.exists(f"{dir_path}/merged.json"):
        # ensure parent directory exists
        create_directory(dir_path)
        refresh = True
    
    wait_msg = ("Building file index now. Table data will load automatically when available. "
                "Rebuilding the index can take a few seconds to a few minutes depending on "
                "the number of files and folders in your account.")

    response= {
        "msg": wait_msg,
        "status": "pending",
        "handle_id": id
    }

    if refresh:
        # rebuild index
        celery.signature("primary.refresh_table_data", 
            kwargs={"account_handle": row.handle}).delay()
        time.sleep(1)
        return jsonify(response)
    else:
        # use /status/file-index-refresh to retrieve data
        return jsonify(response)

@app.route('/status/file-index-refresh', methods=['POST'])
def file_index_refresh():
    id = request.form.get('handle_id')
    row = Account.query.filter(Account.id == id).first()
    meta_dir = get_account_metadata_dir_path(row.handle)
    
    if os.path.exists(f"{meta_dir}/process.lock") and not time_expired(5, f"{meta_dir}/process.lock"):
        response= {
            "status": "pending"
        }
        return jsonify(response)
    else:
        with open(f"{meta_dir}/merged.json", 'r', encoding='utf-8') as f:
            data = f.read()
        response = {
            "data": json.loads(data),
            "status": "success"
        }
        return jsonify(response)

@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = celery.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)

@app.route('/directory/create', methods=['POST'])
def dir_create():
    handle_id = request.json["handle_id"]
    print(f"handle id is: {handle_id}")
    list_of_directories = request.json["array_of_directories"]
    row = Account.query.filter(Account.id == handle_id).first()
    account_handle = row.handle
    print(f"received from client: {list_of_directories}")
    for dir in list_of_directories:
        celery.signature("metadata.create_directory_local_and_remote_combined", 
            kwargs={"account_handle": account_handle, "remote_path": dir}).delay().get()
    return f"Remote and Local folder successfully created and/or existence verified: {list_of_directories}"

@app.route('/file/action', methods=['POST'])
def file_action():
    # Retrieve saved account information, specifically account handle
    row = Account.query.filter(Account.id == request.json["handle_id"]).first()
    account_handle = row.handle

    # describe file actions
    file_action_map = {
        'fa_download_file': "Downloading one or more files",
        'fa_upload_file':   "Uploading one or more files",
        'fa_delete_file':   "Deleting one or more files",
        'fa_move_file':     "Moving one or more files",
        'fa_rename_file':   "Renaming a file"
        }
        
    selected_action = request.json["selected_action"]
    delete_version = request.json["delete_version"]
    delete_storage = request.json["delete_storage"]
    rename_value = request.json["rename_value"]
    list_of_directories = request.json["array_of_directories"]
    list_of_filedata = request.json["array_of_filedata"]
    moveto_directory = request.json["moveto_directory"]
    
    kwargs = {
            "list_of_filedata":     list_of_filedata,
            "list_of_directories":  list_of_directories,
            "account_handle":       account_handle,
            "selected_action":      selected_action,
            "delete_storage":       delete_storage,
            "delete_version":       delete_version,
            "rename_value":         rename_value,
            "moveto_directory":     moveto_directory
    }    

    celery.signature("primary.file_action_dispatch", kwargs=kwargs).delay()    
    return f"Request dispatched successfully: {file_action_map[selected_action]}"

@app.route('/folder/action', methods=['POST'])
def folder_action():
    # Retrieve saved account information, specifically account handle
    row = Account.query.filter(Account.id == request.json["handle_id"]).first()
    account_handle = row.handle

    # Describe directory actions
    folder_action_map = {
        'da_create_folder': "Creating a folder",
        'da_delete_folder': "Deleting a folder and its contents",
        'da_move_folder':   "Moving a folder and its contents",
        'da_rename_folder': "Renaming a folder"
        }

    kwargs = {
        "Folder_Action":            folder_action_map[request.json["selected_action"]],
        "selected":                 request.json["selected_action"],
        "create_folder_parent_dir": request.json["parent_dir_of_create_folder"],
        "create_folder_new_name":   request.json["create_folder_new_name"],
        "movefrom_folder":          request.json["movefrom_folder"],
        "moveto_folder":            request.json["moveto_folder"],
        "rename_folder_path":       request.json["rename_folder_path"],
        "rename_folder_new_name":   request.json["rename_folder_new_name"],
        "delete_folder":            request.json["delete_folder"],
        "delete_storage":           request.json["delete_storage_option"],
        "account_handle":           account_handle
    }

    celery.signature("primary.folder_action_dispatch", kwargs=kwargs).delay()
    return "Request dispatched successfully"
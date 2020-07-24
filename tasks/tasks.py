import os, sys, json, shutil, time, datetime, sqlalchemy, requests
from pathlib import Path, PurePath
from celery import Celery, signature
from celery.utils.log import get_task_logger
from sqlalchemy import create_engine
from tasks.opacity_api import *
from tasks.opacity_api import Constants
from tasks.opacity_api import Opacity
from tasks.opacity_api.Helper import Helper
from tasks.opacity_api.FolderMetaData import FolderMetaData, FolderMetaFolder, FolderMetaFile, FolderMetaFileVersion
from tasks.functions import get_short_handle, get_file_extension, get_account_dir_path, \
    get_account_metadata_dir_path, size_human_readable, date_human_readable, create_directory, get_local_path

# SQL Alchemy
engine = create_engine(f"sqlite:///{os.environ.get('APPDATA')}/opacity.sqlite", echo = True)

app = Celery()
app.conf.task_routes = json.loads(os.environ.get("CELERY_ROUTES"))

logger = get_task_logger(__name__)

@app.task(name="primary.get_account_details")
def get_account_details(account_handle="", handle_name=""):
    try:
        # retrieve from Opacity
        account = Opacity.Opacity(account_handle)
        account_status = account._status

        c = datetime.datetime.strptime(account_status.account.createdAt, '%Y-%m-%dT%H:%M:%SZ')
        e = datetime.datetime.strptime(account_status.account.expirationDate, '%Y-%m-%dT%H:%M:%SZ')

        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.ext.automap import automap_base
        metadata = sqlalchemy.MetaData()
        metadata.reflect(bind=engine)
        Base = automap_base(metadata=metadata)
        Base.prepare(engine, reflect=True)
        Account = Base.classes.account

        add_account = Account(
                handle_name=handle_name,
                handle=account_handle,
                creation_date=f"{c.month}/{c.day}/{c.year}",
                expiration_date=f"{e.month}/{e.day}/{e.year}",
                months_in_subscription=account_status.account.monthsInSubscription,
                storage_capacity=account_status.account.storageLimit, 
                storage_used=f"{account_status.account.storageUsed:.7f}"
                )

        print(f"New record to add to db: {add_account}")

        Session = sessionmaker(bind = engine)
        session = Session()
        session.add(add_account)
        session.commit()

        return True

    except AttributeError:
        """
        self._status = self.checkAccountStatus()
        File "/home/opacity/Opacity.py", line 60, in checkAccountStatus
            raise AttributeError("The provided account handle is invalid!")
        AttributeError: The provided account handle is invalid!
        
        """
        print("Invalid Handle")
        print (f"handled error: {sys.exc_info()[0]}")
        return False
    except:
        print (f"Unexpected error: {sys.exc_info()[0]}")
        return False

''' start file actions '''
@app.task(name="metadata.move_file")
def move_file(**kwargs):
    # move remote file
    account = Opacity.Opacity(kwargs["account_handle"])
    account.move_file(kwargs["file_handle"], kwargs["remote_path"], kwargs["moveto_directory"])
    # move local file
    local_file = os.path.join(kwargs["local_path"], kwargs["file_name"])
    rename_file = os.path.join(get_local_path(kwargs["account_handle"], kwargs["moveto_directory"]), kwargs["file_name"])
    if os.path.isfile(local_file):
        os.rename(local_file, rename_file)
    return True

@app.task(name="metadata.rename_file")
def rename_file(**kwargs):
    # rename remote file
    account = Opacity.Opacity(kwargs["account_handle"])
    account.rename_file(kwargs["remote_path"], kwargs["file_handle"], kwargs["rename_value"])
    # rename local file
    local_file = os.path.join(kwargs["local_path"], kwargs["file_name"])
    rename_file = os.path.join(kwargs["local_path"], kwargs["rename_value"])
    if os.path.isfile(local_file):
        os.rename(local_file, rename_file)
    return True

@app.task(name="download.download_file")
def download_file(**kwargs):
    account = Opacity.Opacity(kwargs["account_handle"])
    account.download(kwargs["file_handle"], kwargs["local_path"], kwargs["file_name"])
    return True

@app.task(name="upload.upload_file")
def upload_file(**kwargs):
    account = Opacity.Opacity(kwargs["account_handle"])
    handle_hex = account.upload(kwargs["file_name"], kwargs["local_path"], kwargs["remote_path"])
    # add file to folder metadata
    app.signature("metadata.add_uploaded_file_to_folder_metadata", 
        kwargs={'account_handle': kwargs["account_handle"], 'file_name': kwargs["file_name"], 
            'local_path': kwargs["local_path"], 'remote_path': kwargs["remote_path"],
            'handle_hex': handle_hex}).delay()
    return True

@app.task(name="metadata.add_uploaded_file_to_folder_metadata")
def add_uploaded_file_to_folder_metadata(**kwargs):
    account = Opacity.Opacity(kwargs["account_handle"])
    file_abs_path = os.path.join(kwargs["local_path"], kwargs["file_name"])
    fileInfo = FolderMetaFile()
    fileInfo.name = os.path.basename(file_abs_path)
    fileInfo.created = int(os.path.getctime(file_abs_path) * 1000)
    fileInfo.modified = int(os.path.getmtime(file_abs_path) * 1000)
    fileInfo.versions.append(
        FolderMetaFileVersion(
            size=os.path.getsize(file_abs_path),
            handle=kwargs['handle_hex'],
            modified=fileInfo.modified,
            created=fileInfo.created
        )
    )
    account.AddFileToFolderMetaData(kwargs["remote_path"], fileInfo, isFile=True)
    return True

''' start delete file action '''
@app.task(name="metadata.delete_file")
def delete_file(**kwargs):
    # delete remote
    if kwargs["delete_storage"] in ["fa_delete_remote", "fa_delete_remote_and_local"] and kwargs["file_handle"]:
        # delete file object
        success = delete_file_object(**kwargs)
        # delete file metadata
        if success:
            delete_file_metadata(**kwargs)

    # delete local
    if kwargs["delete_storage"] in ["fa_delete_local", "fa_delete_remote_and_local"]:
        # check if file
        local_file = os.path.join(kwargs["local_path"], kwargs["file_name"])
        if kwargs["file_name"] and os.path.isfile(local_file):
            os.remove(local_file)

def delete_file_object(**kwargs):
    account = Opacity.Opacity(kwargs["account_handle"])
    file_name = kwargs["file_name"]
    file_handle = kwargs["file_handle"]
    folder_path = kwargs["remote_path"]
    # track file to directory mapping for later
    dir_to_file_dict = {}
    # delete file version or all versions depending on delete_version_option selection
    if kwargs["delete_version"] not in ["fa_delete_all_file_versions"]:
        # delete only the file version specifically requested by user
        dir_to_file_dict[file_name] = [file_handle]
        print("Don't delete all file versions")
    else:
        print("Delete all file versions")
        # need to locate all versions of file using file_name to match
        metadata = account.getFolderData(folder_path)
        for file in metadata["metadata"].files:
            dir_to_file_dict[file.name] = []
        for file in metadata["metadata"].files:
            for version in file.versions:
                dir_to_file_dict[file.name].append(version.handle)
        
        print(f'dir_to_file_dict is {dir_to_file_dict}')

    if dir_to_file_dict.get(file_name) and file_handle:
        for fhandle in dir_to_file_dict.get(file_name):
            requestBody = {"fileID": fhandle[:64]}
            rawPayload = Helper.GetJson(requestBody)
            payload = account.signPayloadDict(rawPayload)
            payloadJson = Helper.GetJson(payload)
            with requests.Session() as s:
                response = s.post(f"{account._baseUrl}delete", data=payloadJson)
            print(f"requesting to delete file object {file_name} with file id of {fhandle}")
            print(f"response status code: {response.status_code}")
            if response.status_code == 200 or response.content.decode() == '"record not found"':
                print(f"Successfully deleted file: {os.path.join(folder_path, file_name)}")
            elif response.status_code == 400:
                print("**********************************")
                print("Error:\n{}".format(response.content.decode()))
                print("Delete of object failed. Maybe incorrect file ID? Not retrying.")
                print("**********************************")                    
            else:
                print("**********************************")
                print("Error:\n{}".format(response.content.decode()))
                print("Delete of object failed. Retrying.")
                print("**********************************")
                # add back to list to retry
                dir_to_file_dict[file_name].append(fhandle)
    return True

def delete_file_metadata(**kwargs):
    account = Opacity.Opacity(kwargs["account_handle"])
    metadata = account.getFolderData(kwargs["remote_path"])
    file_handle = kwargs["file_handle"]
    files_to_retain = []
    for file in metadata["metadata"].files:
        versions_to_retain = []
        for version in file.versions:
            if version.handle != file_handle:
                if kwargs["delete_version"] != "fa_delete_all_file_versions":
                    versions_to_retain.append(version)
        if versions_to_retain:
            file.versions = versions_to_retain
            files_to_retain.append(file)
    metadata["metadata"].files = files_to_retain
    account.setMetadata(metadata)
    return True
''' end delete file action '''
''' end file actions '''

''' start folder actions '''
''' start delete folder action '''
@app.task(name="metadata.delete_folder")
def delete_folder(**kwargs):
    # delete remote
    folder_to_delete_path = kwargs["delete_folder"]
    if kwargs["delete_storage"] in ["da_delete_remote", "da_delete_remote_and_local"]:
        folder_metadata = get_all_files_and_subdirs_of_dir(account_handle=kwargs["account_handle"], dir_path=folder_to_delete_path)
        # reverse sort to delete contents of lowest subdirectory first and move up the chain
        for folder, folder_data in sorted(list(folder_metadata.items()), key=lambda x:x[0], reverse=True):
            for file in folder_data['files']:
                # delete each file one by one. delete file object. wait to complete. then delete file metadata
                _kwargs={'file_handle': file[1], 'delete_storage': 'fa_delete_remote', 'account_handle': kwargs['account_handle'],
                            'delete_version': '', 'remote_path': folder, 'file_name': file[0] }
                delete_file(**_kwargs)
        # delete folder metadata
        for folder, folder_data in sorted(list(folder_metadata.items()), key=lambda x:x[0], reverse=True):
            # delete folder metadata once all file objects deleted
            delete_directory_metadata(account_handle=kwargs['account_handle'], folder_handle=folder_data['folder_handle'])
        # delete folder from parent folder metadata
        # remote_path is parent directory of directory to delete
        _kwargs={'account_handle': kwargs['account_handle'], 'folder_name': Path(folder_to_delete_path).name, 
            'parent_path': Path(folder_to_delete_path).parent.as_posix()}
        delete_subdir_metadata(**_kwargs)

    # delete local
    if kwargs["delete_storage"] in ["da_delete_local", "da_delete_remote_and_local"]:
        try:
            shutil.rmtree(get_local_path(kwargs['account_handle'], folder_to_delete_path))
        except OSError as e:
            print (f"Error: {e.filename} - {e.strerror}")
            print('Local folder does not exist or could not be removed')

def delete_directory_metadata(**kwargs):
    account = Opacity.Opacity(kwargs["account_handle"])
    requestBody = {"timestamp": Helper.GetUnixMilliseconds(), "metadataKey": kwargs["folder_handle"]}
    rawPayload = Helper.GetJson(requestBody)
    payload = account.signPayloadDict(rawPayload)
    payloadJson = Helper.GetJson(payload)
    with requests.Session() as s:
        return s.post(f"{account._baseUrl}metadata/delete", data=payloadJson)

def delete_subdir_metadata(**kwargs):
    # remove subfolder from folder, similar to removing a file from folder
    account = Opacity.Opacity(kwargs["account_handle"])
    metadata = account.getFolderData(kwargs["parent_path"]) # parent dir of subdir
    folders_to_retain = []
    delete_dir_metadata = []
    for folder in metadata["metadata"].folders:
        print(f"folder.name: {folder.name}")
        print(f'kwargs[folder_name]: {kwargs["folder_name"]}')
        if folder.name == kwargs["folder_name"]:
            print("adding folder to delete_dir_metadata to delete")
            delete_dir_metadata.append(folder.handle)
        else:
            folders_to_retain.append(folder)
    metadata["metadata"].folders = folders_to_retain
    account.setMetadata(metadata)
    for folder_handle in delete_dir_metadata:
        delete_directory_metadata(account_handle=kwargs['account_handle'], folder_handle=folder_handle)
    return True

def get_all_files_and_subdirs_of_dir(**kwargs):
    account = Opacity.Opacity(kwargs["account_handle"])
    directory_metadata = {}
    directories_to_index = [kwargs["dir_path"]] # initialize
    '''
    Example
    directory_metadata = {'/dir1/sub1': 'folder_handle': '123456', 'files': [['file1','356496'],['file2','964731']]}
    '''
    while directories_to_index:
        current_dir = directories_to_index.pop()
        folder_handle = account.getFolderData(current_dir)['metadataKey']
        metadata = account._metaData
        directory_metadata[current_dir] = {'folder_handle': folder_handle, 'files': []}
        for folder in metadata.folders:
            absolute_path = os.path.join(current_dir, folder.name)
            directories_to_index.append(absolute_path)
        for file in metadata.files:
            for version in file.versions:
                directory_metadata[current_dir]['files'].append([file.name, version.handle])
    return directory_metadata
''' end delete folder action '''

@app.task(name="metadata.move_folder")
def move_folder(**kwargs):
    account_handle = kwargs["account_handle"]
    folder_movefrom_path = kwargs["movefrom_folder"]
    folder_name = Path(folder_movefrom_path).name
    folder_moveto_path = kwargs["moveto_folder"]
    account = Opacity.Opacity(account_handle)

    # Step 1: iterate directory to move. create new folder and metadata for main dir and subdirs.
    directories_to_index = [[folder_movefrom_path, folder_moveto_path]] # initialize
    i = 1
    while directories_to_index:
        print(f"directories to index (iteration {i}): {directories_to_index}")
        move_folder = directories_to_index.pop()
        folder = Path(move_folder[0]).name
        old_directory = move_folder[0]
        new_directory = os.path.join(move_folder[1], folder)
        metadata = account.getFolderData(move_folder[0])
        for folder in metadata["metadata"].folders:
            directories_to_index.append([os.path.join(old_directory, folder.name), new_directory])
        # create new directory
        create_directory_local_and_remote_combined(account_handle=account_handle, remote_path=new_directory)
        # copy metadata to new directory; retain any existing files if directory already
        newdir_metadata = account.getFolderData(new_directory)
        newdir_metadata["metadata"].files = newdir_metadata["metadata"].files + metadata["metadata"].files
        # transfer metadata to new location
        account.setMetadata(newdir_metadata)
        # delete metadata of old folder
        folder_handle = metadata['metadataKey']
        delete_directory_metadata(account_handle=account_handle, folder_handle=folder_handle)
        i = i + 1

    # Step 2: remove folder metadata from parent folder
    movefrom_metadata_parent = account.getFolderData(Path(folder_movefrom_path).parent.as_posix()) # move from this dir
    folders_to_retain = []
    for folder in movefrom_metadata_parent["metadata"].folders:
        if folder.name == folder_name:
            pass
        else:
            folders_to_retain.append(folder)
    movefrom_metadata_parent["metadata"].folders = folders_to_retain
    account.setMetadata(movefrom_metadata_parent)

    # Step 3: move local directory
    try:
        old_path = get_local_path(kwargs["account_handle"], folder_movefrom_path)
        new_path = get_local_path(kwargs["account_handle"], folder_moveto_path)
        if os.path.isdir(os.path.join(new_path, Path(old_path).name)):
            shutil.rmtree(os.path.join(new_path, Path(old_path).name))
        shutil.move(old_path, new_path)
    except Exception as e:
        print(e.__doc__)
    return True

@app.task(name="metadata.rename_folder")
def rename_folder(**kwargs):
    account_handle = kwargs["account_handle"]
    account = Opacity.Opacity(account_handle)
    parent_dir = Path(kwargs["rename_folder_path"]).parent.as_posix()
    folder_name = Path(kwargs["rename_folder_path"]).name
    rename_from = kwargs["rename_folder_path"]
    rename_to = os.path.join(parent_dir, kwargs["rename_folder_new_name"])

    # remove folder metadata from parent
    parent_metadata = account.getFolderData(parent_dir) # move from this dir
    folders_to_retain = []
    for folder in parent_metadata["metadata"].folders:
        if folder.name == folder_name:
            pass
        else:
            folders_to_retain.append(folder)
    parent_metadata["metadata"].folders = folders_to_retain
    account.setMetadata(parent_metadata)
    # retrieve and copy folder's metadata (folders and files)
    metadata = account.getFolderData(rename_from)
    # create new directory
    create_directory_local_and_remote_combined(account_handle=account_handle, remote_path=rename_to)
    # copy metadata to new directory
    newdir_metadata = account.getFolderData(rename_to)
    newdir_metadata["metadata"] = metadata["metadata"]
    # transfer metadata to new location
    account.setMetadata(newdir_metadata)
    # delete metadata of old folder
    folder_handle = metadata['metadataKey']
    delete_directory_metadata(account_handle=account_handle, folder_handle=folder_handle)

    # local
    try:
        old_path = get_local_path(account_handle, rename_from)
        new_path = get_local_path(account_handle, rename_to)
        if os.path.isdir(new_path):
            shutil.rmtree(new_path)
        os.rename(old_path, new_path)
    except:
        pass

''' end folder actions '''

''' start refresh index '''
@app.task(name="primary.refresh_table_data")
def refresh_table_data_parent_task(account_handle=""):
    meta_dir = get_account_metadata_dir_path(account_handle)
    lock_file = os.path.join(meta_dir, 'process.lock')
    Path(lock_file).touch()
    success = False
    try:
        build_remote_file_index(account_handle)
        build_local_file_index(account_handle)
        merge_local_remote_indexes(account_handle)
        merge_remote_local_directory_structure(account_handle)
        success = True
    except:
        pass
    finally:
        os.remove(lock_file)
    return success

# step 1 of 4 of refresh table data
def build_remote_file_index(account_handle):
    account = Opacity.Opacity(account_handle)
    all_files = []
    all_directories = []
    directories_to_index = ['/'] # initialize
    print(f"*****Executing build_remote_file_index()*****")
    while directories_to_index:
        current_dir = directories_to_index.pop()
        print(f"current_dir: {current_dir}")
        metadata = account.getFolderData(current_dir)
        print("Executed after call to getFolderData()")
        for folder in metadata["metadata"].folders:
            absolute_path = os.path.join(current_dir, folder.name)
            print(f"folder path: {absolute_path}")
            directories_to_index.append(absolute_path)
            all_directories.append([absolute_path, folder.handle])
        for file in metadata["metadata"].files:
            for version in file.versions:
                # 0: filename, 1: filetype (extension), 2: parentdir, 3: abspath_file, 
                # 4: filesize, 5: createdate, 6: modifydate, 7: handle, 8: abspath_dir
                all_files.append([  file.name, 
                                    get_file_extension(file.name),
                                    PurePath(current_dir).name,
                                    os.path.join(current_dir, file.name),
                                    version.size,
                                    version.created,
                                    version.modified,
                                    version.handle,
                                    current_dir]
                                )

    for item in all_files:
        # remove parent directory from files in root of account directory
        if not item[2]:
            item[2] = "/"

    data = {"data": all_files, "directories": all_directories}

    # write to disk
    meta_dir = get_account_metadata_dir_path(account_handle)
    create_directory(meta_dir)

    with open(f"{meta_dir}/remote.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    return True

# step 2 of 4 of refresh table data
def build_local_file_index(account_handle):
    account_dir = get_account_dir_path(account_handle)
    create_directory(account_dir)

    # store file metadata and relative path of all directories
    all_files = []
    all_directories = []
    dirs_to_index = [account_dir]

    for root, dirs, files in os.walk(account_dir, topdown=True):
        for name in dirs:
            dirs_to_index.append(os.path.join(root, name))

    for dir in dirs_to_index:
        with os.scandir(dir) as entries:
            for file in entries:
                if file.is_file():
                    # 0: filename, 1: filetype (extension), 2: parentdir, 3: abspath_file, 
                    # 4: filesize, 5: createdate, 6: modifydate, 7: handle, 8: abspath_dir
                    stat = file.stat()
                    local_rel_path = dir.split(account_dir, 1) [1] if dir.split(account_dir, 1) [1] else '/'

                    all_files.append([  file.name,
                                        get_file_extension(file.name),
                                        PurePath(dir).name,
                                        os.path.join(dir, file.name),
                                        stat.st_size,
                                        int(stat.st_ctime),
                                        int(stat.st_mtime),
                                        "",
                                        local_rel_path
                                    ])

    # Make local storage resemble remote (Opacity) storage
    for item in all_files:
        # remove/ignore directory path up to root of account directory
        item[3] = item[3].split(account_dir, 1) [1]
        # remove parent directory from files in root of account directory
        if item[2] == os.path.basename(account_dir):
            item[2] = "/"
    
    # remove/ignore directory path up to root of account directory
    # even though only one element per list, put in list to match remote list
    # i.e. select list[0] as the list is iterated
    for item in dirs_to_index:
        all_directories.append(item.split(account_dir, 1) [1])
    
    # Transform local all_directories to match remote.
    # Target: [['dir1',''],['dir2','']]
    data = {"data": all_files, "directories": [[i, ''] for i in all_directories if i]}

    # write to disk
    meta_dir = get_account_metadata_dir_path(account_handle)
    create_directory(meta_dir)

    with open(f"{meta_dir}/local.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    return True

# step 3 of 4 of refresh table data
def merge_local_remote_indexes(account_handle):
    merged_data = {}
    """
    merged_data = {
                    "data": [
                                [meta1, meta2, meta3],
                                [meta1, meta2, meta3]
                            ], 
                    "directories": {
                            "local": [
                                [dirname, ''],
                                [dirname, '']
                                ],
                            "remote": [
                                [dirname, handle ],
                                [dirname, handle ]
                                ],
                            "merged": [dirname, dirname, dirname]
                    },
                    "file_lookup": {
                        'abspath_file1': {
                            "local": [
                                        [meta1, meta2, meta3]
                                     ],
                            "remote": [
                                        [meta1, meta2, meta3],
                                        [meta1, meta2, meta3]
                                     ]
                        }
                    }
                  }
    """
    # load json files
    dir_path = get_account_metadata_dir_path(account_handle)
    with open(f"{dir_path}/remote.json", 'r', encoding='utf-8') as f:
        remote = json.loads(f.read())

    with open(f"{dir_path}/local.json", 'r', encoding='utf-8') as f:
        local = json.loads(f.read())
    
    # create lookup keys to retrieve all data related to a file,
    # including local and remote files and remote versions
    merged_data["file_lookup"] = {}

    # process remote data
    for file in remote["data"]:
        # file[3] is abspath_file, use as key
        if file[3] not in merged_data["file_lookup"]:
            merged_data["file_lookup"][file[3]] = {}
        if "remote" not in merged_data["file_lookup"][file[3]]:
            merged_data["file_lookup"][file[3]]["remote"] = []
        if "local" not in merged_data["file_lookup"][file[3]]:
            merged_data["file_lookup"][file[3]]["local"] = []
        merged_data["file_lookup"][file[3]]["remote"].append(file)

    # process local data
    for file in local["data"]:
        if file[3] not in merged_data["file_lookup"]:
            merged_data["file_lookup"][file[3]] = {}
        if "remote" not in merged_data["file_lookup"][file[3]]:
            merged_data["file_lookup"][file[3]]["remote"] = []
        if "local" not in merged_data["file_lookup"][file[3]]:
            merged_data["file_lookup"][file[3]]["local"] = []
        # file[3] is abspath_file, use as key
        merged_data["file_lookup"][file[3]]["local"].append(file)

    # create table data to display in datatables
    # 0: filename, 1: filetype (extension), 2: parentdir, 3: abspath_file, 
    # 4: filesize, 5: createdate, 6: modifydate, 7: handle, 8: abspath_dir
    merged_data["data"] = []
    for file in merged_data["file_lookup"]:
        if merged_data["file_lookup"][file]["remote"]:
            # tmp is list of lists e.g. [[attrib1, attrib2],[attrib1, attrib2]]
            tmp = merged_data["file_lookup"][file]["remote"]
            # determine which is newest remote file
            temp_dict = {}
            i = 0
            for item in tmp:
                temp_dict[i]=item[6] # item[6] is last modified date
                i = i+1
            # get index of list item with most recent modify time
            idx = max(temp_dict, key = temp_dict.get)
            # determine sync status
            sync_status = "no: opacity only"
            if merged_data["file_lookup"][file]["local"]:
                if tmp[idx][4] == merged_data["file_lookup"][file]["local"][0][4]:
                    sync_status = "synced"
                else:
                    sync_status = "no: out of sync"

            #share_link = f'<a target="_blank" rel="noopener noreferrer" href="https://opacity.io/share#handle={tmp[idx][7]}">link</a>'
            filedata = [
                        tmp[idx][0],
                        tmp[idx][1],
                        tmp[idx][2],
                        tmp[idx][8],
                        size_human_readable(tmp[idx][4]),
                        date_human_readable(tmp[idx][6]),
                        "",
                        sync_status,
                        tmp[idx][7]
                       ]

            merged_data["data"].append(filedata)

        elif merged_data["file_lookup"][file]["local"]:
            # tmp is list with one list e.g. [[attrib1, attrib2]]
            tmp = merged_data["file_lookup"][file]["local"][0]
            filedata = [
                        tmp[0], 
                        tmp[1], 
                        tmp[2], 
                        tmp[8], 
                        size_human_readable(tmp[4]), 
                        '', 
                        '', 
                        'no: local only',
                        ''
                       ]

            merged_data["data"].append(filedata)

    # augment file lookup data with human readable size and date
    for key in merged_data["file_lookup"]:
        for file in merged_data["file_lookup"][key]['remote']:
            file.append(size_human_readable(file[4]))
            file.append(date_human_readable(file[6]))

    # copy directories
    merged_data["directories"] = {}
    merged_data["directories"]["local"] = local["directories"]
    merged_data["directories"]["remote"] = remote["directories"]

    with open(f"{dir_path}/merged.json", 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False)
    return True

# step 4 of 4 of refresh table data
def merge_remote_local_directory_structure(account_handle):
    data = {}
    data["directories"] = set()

    # load local and remote json data from file
    meta_dir_path = get_account_metadata_dir_path(account_handle)
    with open(f"{meta_dir_path}/remote.json", 'r', encoding='utf-8') as f:
        remote = json.loads(f.read())
    with open(f"{meta_dir_path}/local.json", 'r', encoding='utf-8') as f:
        local = json.loads(f.read())

    for dir in remote["directories"]:
        data["directories"].add(dir[0])
    for dir in local["directories"]:
        data["directories"].add(dir[0])
    # get sorted list from set()
    data["directories"] = sorted(data["directories"])
    print(f"Synced directory list: {data}")

    # add to merged.json file
    with open(f"{meta_dir_path}/merged.json", 'r', encoding='utf-8') as f:
        merged = json.loads(f.read())
    merged["directories"]["merged"] = data["directories"]
    with open(f"{meta_dir_path}/merged.json", 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False)

    '''
    # this takes a while to run. instead let's present the merged directories list
    # i.e. local and remote together as one list. when user selects acions on directory
    # or involving directory, run create directory equivalents for both local and remote
    # just on the directory involved in the action

    # sync directories
    account = Opacity.Opacity(account_handle)
    account_home = get_account_dir_path(account_handle)
    for dir in data["directories"]:
        local_dir = f"{account_home}{dir}"
        create_directory(local_dir)
        create_remote_directory(dir)
    '''
    return True

''' end refresh index '''

@app.task(name="metadata.create_directory_local_and_remote_combined")
def create_directory_local_and_remote_combined(account_handle="", remote_path=""):
    # account_home has no trailing slash. remote_path starts with forward slash.
    # os.path.join ignores account_home since remote_path has leading slash.
    # just use string format instead.
    local_dir = get_local_path(account_handle, remote_path)
    create_directory(local_dir)
    print(f"Local directory created: {local_dir}")
    create_remote_directory(account_handle=account_handle, folder_path=remote_path)
    print(f"Remote directory created: {remote_path}")
    return True

@app.task(name="metadata.create_remote_directory")
def create_remote_directory(account_handle="", folder_path=""):
    # create all directories leading up to last directory
    # if directory already exists, Opacity API handles gracefully
    account = Opacity.Opacity(account_handle)
    dirs_in_path_in_order = [i for i in folder_path.split('/') if i]
    path = '/'
    list_position = -1
    for dir in dirs_in_path_in_order:
        list_position += 1
        path = os.path.join(path, dir)
        folderName = os.path.basename(path)
        parentDirectory = os.path.dirname(path)
        metadata = account.createMetadata(path)
        if metadata["addFolder"]:
            folder = FolderMetaFolder(name=folderName, handle=metadata["metadataKey"])
            account.AddFileToFolderMetaData(parentDirectory, folder, isFolder=True)
            print("Created successfully {}".format(path))
            if list_position == len(dirs_in_path_in_order) - 1:
                # Only return if at basename of original path passed in
                return folder
        else:
            if list_position == len(dirs_in_path_in_order) - 1:
                # Only return if at basename of original path passed in
                return FolderMetaFolder(name=folderName, handle=metadata["metadataKey"])

@app.task(name="primary.remove_local_account_data")
def remove_local_account_data(account_handle="", delete_files_bool=False):
    meta_dir = get_account_metadata_dir_path(account_handle)
    try:
        shutil.rmtree(meta_dir)
    except OSError as e:
        print (f"Error: {e.filename} - {e.strerror}")
        raise Exception('Metadata directory no longer exists or could not be removed')

    if delete_files_bool:
        root_dir = get_account_dir_path(account_handle)
        try:
            shutil.rmtree(root_dir)
        except OSError as e:
            print (f"Error: {e.filename} - {e.strerror}")
            raise Exception('Account directory no longer exists or could not be removed')

def get_all_files_of_dir(**kwargs):
    '''
    Example
    directory_metadata = {'folder_path': '/dir1/sub1', 'folder_handle': '123456', 'files': [['file1','356496'],['file2','964731']]}
    '''
    account = Opacity.Opacity(kwargs["account_handle"])
    current_dir = kwargs["dir_path"]
    folder_handle = account.getFolderData(current_dir)['metadataKey']
    metadata = account._metaData
    directory_metadata = {'folder_path': current_dir, 'folder_handle': folder_handle, 'files': []}
    for file in metadata.files:
        for version in file.versions:
            directory_metadata['files'].append([file.name, version.handle])
    return directory_metadata
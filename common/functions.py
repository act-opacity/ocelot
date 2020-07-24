def get_short_handle(account_handle):
    return account_handle[:20]

def get_account_dir_path(account_handle):
    import os
    LOCAL_DATA = os.environ.get('LOCAL_DATA')
    return f'{LOCAL_DATA}/{get_short_handle(account_handle)}'

def get_account_metadata_dir_path(account_handle):
    import os
    # this path is parent dir for account metadata files
    FILE_METADATA = os.environ.get('FILE_METADATA_JSON')
    return f"{FILE_METADATA}/{get_short_handle(account_handle)}"

def get_local_path(account_handle, remote_path):
    acct_dir = get_account_dir_path(account_handle)
    return f"{acct_dir}{remote_path}"

def convert_js_bool_to_python(js_bool):
    return True if js_bool == 'true' else False

def get_file_extension(filename):
    import os
    name, ext = os.path.splitext(filename)
    return ext

def size_human_readable(bytes, units=[' bytes','KB','MB','GB','TB', 'PB', 'EB']):
    return str(bytes) + units[0] if bytes < 1024 else size_human_readable(bytes>>10, units[1:])

def date_human_readable(timestamp):
    from datetime import datetime, timezone
    timestamp = int(str(timestamp)[:10])
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S (UTC)')

def object_as_dict(obj, db):
    return {c.key: getattr(obj, c.key)
            for c in db.inspect(obj).mapper.column_attrs}

def create_directory(dir):
    from pathlib import Path, PurePath
    print("creating directory structure:")
    Path(dir).mkdir(parents=True, exist_ok=True)

def time_expired(minutes, filename):
    from pathlib import Path
    from datetime import datetime, timedelta

    time_limit = datetime.now() - timedelta(minutes=minutes)
    filetime = datetime.fromtimestamp(Path(filename).stat().st_ctime)

    if filetime < time_limit:
        # file is older than given minutes
        return True
    else:
        return False

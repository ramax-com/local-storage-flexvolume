#!/usr/bin/python3

import json
import os
import re
import subprocess
import sys

LOCAL_STORAGE_ROOT = '/srv/local'
FILE_SYNC_STORAGE_ROOT = '/srv/file-sync'

# touch /tmp/debug-local-storage.log to enable debug log
DEBUG_LOG = '/tmp/debug-local-storage.log'
SUCCESS = '{"status": "Success"}'
VALID_FILE_NAME = re.compile(r'[0-9a-zA-Z,@_=+-]')
VALID_PATH_NAME = re.compile(r'[/0-9a-zA-Z,@_=+-]')


def DEBUG(*args):
    if os.path.exists(DEBUG_LOG):
        with(open(DEBUG_LOG, 'a')) as f:
            print(' '.join([str(a) for a in args]), file=f, flush=True)


class InvalidPathName(ValueError):
    pass


def validate_path(s):
    if not VALID_PATH_NAME.match(s):
        raise InvalidPathName(s)
    return s


def validate_name(s):
    if not VALID_FILE_NAME.match(s):
        raise InvalidPathName(s)
    return s


def decode_options(s):
    return json.loads(s, encoding='utf-8')


def is_mounted(mount_path):
    output = subprocess.run(['findmnt', '-n', mount_path], stdout=subprocess.PIPE).stdout.decode()
    parts = output.split()
    return parts and (parts[0] == mount_path)


def init():
    return '{"status": "Success", "capabilities": {"attach": false}}'


def mount(mount_path, options):
    validate_path(mount_path)
    if is_mounted(mount_path):
        return SUCCESS

    storage_dir = _get_storage_path(options)
    mode = options.get('volume-mode')
    uid = options.get('volume-uid')
    gid = options.get('volume-gid')

    os.makedirs(storage_dir, mode=int(mode or '0755', 8), exist_ok=True)
    if mode is not None:
        os.chmod(storage_dir, int(mode, 8))
    if (uid, gid) != (None, None):
        uid = int(uid) if uid is not None else -1
        gid = int(gid) if gid is not None else -1
        os.chown(storage_dir, uid, gid)
    subprocess.check_call(['mount', '--bind', storage_dir, mount_path])

    return SUCCESS


def _get_storage_path(options):
    root = FILE_SYNC_STORAGE_ROOT if options.get('file-sync') else LOCAL_STORAGE_ROOT
    volume_name = options.get('pvc-name', options['kubernetes.io/pvOrVolumeName'])
    path = os.path.join(root,
                        validate_name(options['kubernetes.io/pod.namespace']),
                        validate_name(volume_name))
    if options.get("pod-local") and options.get("pod-local") != "false":
        path = os.path.join(path, validate_name(options['kubernetes.io/pod.name']))
    return path


def unmount(mount_path, options):
    validate_path(mount_path)
    if not is_mounted(mount_path):
        return SUCCESS

    subprocess.check_call(['umount', mount_path])
    return SUCCESS


def failure(msg):
    print(json.dumps({'status': 'Failure', 'message': msg}))
    sys.exit(1)


def main():
    DEBUG(*sys.argv[1:])
    op = sys.argv[1]
    if op == 'init':
        print(init())
    elif op == 'mount':
        print(mount(sys.argv[2], decode_options(len(sys.argv) >= 4 and sys.argv[3] or 'null')))
    elif op == 'unmount':
        print(unmount(sys.argv[2], decode_options(len(sys.argv) >= 4 and sys.argv[3] or 'null')))
    else:
        print('{"status": "Not supported"}')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        failure(str(e))

"""
local-storage-driver.py init
touch /mnt/test-file
local-storage-driver.py mount /mnt '{"kubernetes.io/pod.namespace": "test0", "kubernetes.io/pod.name": "test-pod", "kubernetes.io/pvOrVolumeName": "data"}'
ls -l /srv/test0/test-pod/data
local-storage-driver.py unmount /mnt ''
rm /mnt/test-file
"""

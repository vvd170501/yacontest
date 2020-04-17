import pickle
import sys
from getpass import getpass
from pkg_resources import resource_filename
from shutil import copyfile

from .utils import choice

cfg_file = resource_filename(__name__, 'data/config')
cfg_backup = resource_filename(__name__, 'data/config.bak')  # used for updates


def get_cfg(noexit=False):
    def restore_backup():
        try:
            with open(cfg_backup, 'rb') as f:
                data = f.read()
        except FileNotFoundError:
            data = b''
        if data != b'':
             copyfile(cfg_backup, cfg_file)
        return data

    with open(cfg_file, 'rb') as f:
        data = f.read() or restore_backup()
    if data == b'':
        if noexit:
            return None
        print('ERROR: Config not found, run "yacontest config" first')
        sys.exit(1)

    return pickle.loads(data)


def set_cfg(cfg):
    with open(cfg_file, 'wb') as f:
        pickle.dump(cfg, f)
    copyfile(cfg_file, cfg_backup)


def create():
    cfg = get_cfg(True)
    if cfg is not None:
        if not input('Config already exists, overwrite? [yN]: ').lower().startswith('y'):
            return
        contest = cfg['contest']
    else:
        contest = 0
    domain = choice('Choose the domain:', ['official.contest.yandex.ru', 'contest.yandex.ru'])
    if domain is None:
        print('ERROR: Invalid choice, try again')
        sys.exit(1)
    login = input('Login: ')
    if input('Store password (insecure)? (yN): ').lower().startswith('y'):
        password = getpass()
    else:
        password = ""
    set_cfg({'domain': domain, 'login': login, 'password': password, 'contest': contest})


def select(contest_id):
    cfg = get_cfg()
    cfg['contest'] = contest_id
    cfg.pop('problems', None)
    set_cfg(cfg)
    print('Success!')

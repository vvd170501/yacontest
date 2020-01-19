import pickle
import sys
from getpass import getpass
from pkg_resources import resource_filename

cfg_file = resource_filename(__name__, 'data/config')


def get_cfg(noexit=False):
    with open(cfg_file, 'rb') as f:
        data = f.read()
    if data.strip() == b'':
        if noexit:
            return None
        print('ERROR: Config not found, run "yacontest config" first')
        sys.exit(1)

    return pickle.loads(data)


def set_cfg(cfg):
    with open(cfg_file, 'wb') as f:
        pickle.dump(cfg, f)


def create():
    cfg = get_cfg(True)
    if cfg is not None:
        if not input('Config already exists, overwrite? [yN]: ').lower().startswith('y'):
            return
        contest = cfg['contest']
    else:
        contest = 0
    print('Choose the domain:\n1) official.contest.yandex.ru\n2) contest.yandex.ru')
    choice = input('Domain (1/2): ')
    if choice == '1':
        domain = 'official.contest.yandex.ru'
    elif choice == '2':
        domain = 'contest.yandex.ru'
    else:
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

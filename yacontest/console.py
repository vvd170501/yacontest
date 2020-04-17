#!/usr/bin/env python3

import sys

from . import config
from .client import Client


def print_usage(args=None):
    print('Usage: yacontest <command> [options]')
    print('Available commands:')
    print('    config  -  create config file in interactive mode')
    print('    select <contest id>  -  choose a contest')
    print('    lang "..."  -  choose/reset preferred language / compiler')
    print('    lang  -  show selected language / compiler')
    print('    load  -  save all problem statements to ./problems/')
    print('    send <file> <problem id>  -  upload a solution')
    print('    check <file> <problem id> [--lang "..."]  -  upload a solution and wait for result')
    print('    status <problem id> [--lang "..."]   -  show status of the last solution')
    print('    leaderboard [page]-  show current leaderboard')
    print('    help  -  print this message')


def create_config(args):
    config.create()


def select(args):
    if not args:
        print('ERROR: Contest id is not specified')
        sys.exit(1)
    c_id = args[0]
    if not c_id.isnumeric():
        print('ERROR: Contest id must be a number')
        sys.exit(1)
    config.select(int(c_id))


def lang(args):
    if not args:
        cfg = config.get_cfg()
        print(cfg.get('lang', 'No language selected'))
        return
    choice = args[0]
    if choice == 'list':
        Client().choose_lang()
    else:
        config.lang(choice if choice.lower() != 'reset' else None)


def load_problems(args):
    Client().load_problems()


def _send(args, wait):
    if len(args) < 2:
        print('ERROR: Not enough options, check usage')
        sys.exit(1)
    fname, problem = args[:2]
    if len(args) > 3 and args[2] == '--lang':
        lang = args[3]
    else:
        lang = None
    Client().submit(problem, fname, wait, lang)



def check(args):
    _send(args, True)


def send(args):
    _send(args, False)


def status(args):
    if not args:
        print('ERROR: Problem id is not specified')
        sys.exit(1)
    problem = args[0]
    Client().show_status(problem)


def leaderboard(args):
    if not args:
        page = '1'
    else:
        page = args[0]
        if not page.isnumeric():
            print('ERROR: Invalid page number')
            sys.exit(1)
    Client().show_leaderboard(int(page))


def main():
    cmds = {
            'config': create_config,
            'select': select,
            'lang': lang,
            'load': load_problems,
            'send': send,
            'check': check,
            'status': status,
            'leaderboard': leaderboard,
            'help': print_usage
           }
    args = sys.argv
    if len(args) == 1 or args[1] not in cmds:
        print_usage()
        sys.exit(1)
    cmds[args[1]](args[2:])


if __name__ == '__main__':
    main()

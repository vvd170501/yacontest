#!/usr/bin/env python3

import sys

from . import config
from .client import Client


def print_usage(args=None):
    print('Usage: yacontest <command> [options]')
    print('Available commands:')
    print('    config  -  create config file in interactive mode')
    print('    select <contest id>  -  choose a contest')
    print('    send <file> <problem id>  -  upload a solution')
    print('    check <file> <problem id>  -  upload a solution and wait for result')
    print('    leaderboard [page]-  show current leaderboard')
    print('    status <problem id>  -  show status of the last solution')
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


def _send(args, wait):
    if len(args) < 2:
        print('ERROR: Not enough options, check usage')
        sys.exit(1)
    fname, problem = args[:2]
    Client().submit(problem, fname, wait)



def check(args):
    _send(args, True)


def send(args):
    _send(args, False)


def leaderboard(args):
    if not args:
        page = '1'
    else:
        page = args[0]
        if not page.isnumeric():
            print('ERROR: Invalid page number')
            sys.exit(1)
    Client().show_leaderboard(int(page))


def status(args):
    if not args:
        print('ERROR: Problem id is not specified')
        sys.exit(1)
    problem = args[0]
    Client().show_status(problem)


def main():
    cmds = {'config': create_config, 'select': select, 'send': send, 'check': check, 'leaderboard': leaderboard, 'status': status, 'help': print_usage}
    args = sys.argv
    if len(args) == 1 or args[1] not in cmds:
        print_usage()
        sys.exit(1)
    cmds[args[1]](args[2:])


if __name__ == '__main__':
    main()

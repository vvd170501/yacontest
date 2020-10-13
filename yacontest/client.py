import os
import re
import sys
from base64 import b64decode
from getpass import getpass
from urllib.parse import urlparse, parse_qs
from time import time, sleep

import requests
from bs4 import BeautifulSoup as BS
from html2text import HTML2Text as H2T

from .config import get_cfg, set_cfg
from .utils import clean_dir, choice


class SolutionStatus():
    def __init__(self, titles, values):
        for k, v in zip(titles, values):
            if k == 'ID':
                self.sid = v
            elif k == 'Вердикт':  # TODO add english?
                self.text = v
            elif k == 'Время':
                self.time = v
            elif k == 'Память':
                self.mem = v
            elif k == 'Тест':
                self.test = v if v != '-' else ''
            elif k == 'Баллы':
                self.score = v if v != '-' else ''
        self.ce = self.text == 'CE' or self.text == 'PCF'
        self.testing = self.text == 'Тестируется'
        self.checked = not self.testing and not self.text.startswith('Ожидание')  # assuming there are only 2 incomplete states

    def __str__(self):
        msg = f'Solution {self.sid}: {self.text}, Time: {self.time}, Mem: {self.mem}'
        if self.test:
            testmsg = 'Test' if self.testing else 'Failed test'
            msg += f', {testmsg}: {self.test}'
        if self.score:
            msg += f', Score: {self.score}'
        return msg


class Statement():
    def __init__(self, html):
        images = html.find_all('img')
        tex_path = '/testsys/tex/render/'
        for im in images:
            src_path = urlparse(im['src']).path
            m = re.match(tex_path + r'(.*)\..*', src_path)
            if m:
                im.replace_with('$' + b64decode(m.group(1)).decode() + '$')
        h2t = H2T()
        h2t.use_automatic_links = True
        h2t.mark_code = True
        h2t.body_width = 100
        h2t.protect_links = True
        def tomd(tag):
            return h2t.handle(str(tag)).strip().replace('\\-', '-').replace('\\+', '+')

        delim = '\n' + '=' * 20 + '\n'
        test_delim = '\n' + '-' * 20 + '\n'
        try:
            title = html.find('', class_='title').text.strip()
            limits = ''
            tl_el = html.find('tr', class_='time-limit')
            if tl_el is not None:
                limits = '\n'.join(': '. join(cell.text.strip() for cell in row.find_all('td')) for row in tl_el.parent.find_all('tr'))
            legend = ''
            legend_el = html.find(class_='legend')
            if legend_el is not None:
                legend = tomd(legend_el)
            inspec = ''
            is_el = html.find(class_='input-specification')
            if is_el is not None:
                hdr = is_el.find_previous_sibling()
                inspec = '\n'.join([hdr.text.strip(), tomd(is_el)])
            outspec = ''
            os_el = html.find(class_='output-specification')
            if os_el is not None:
                hdr = os_el.find_previous_sibling()
                outspec = '\n'.join([hdr.text.strip(), tomd(os_el)])
            notes = ''
            notes_el = html.find(class_='notes')
            if notes_el is not None:
                hdr = notes_el.find_previous_sibling()
                notes = '\n'.join([hdr.text.strip(), tomd(notes_el)])
            test_data = [[cell.text for cell in test.find_all('tr')[1].find_all('td')] for test in html.find_all('table', class_='sample-tests')]
            tests = test_delim.join('\n'.join(['>' * 10, in_, '<' * 10, out]) for (in_, out) in test_data)
            self.fields = [title, limits, legend, inspec, outspec, notes, tests]
            self.descr = delim.join([e for e in self.fields if e])
        except KeyboardInterrupt:
            raise
        except Exception as e:
            self.fields = []
            self.descr = delim.join('ERROR: problem statement was not loaded', str(e))

    def __str__(self):
        return self.descr


class Client():
    def __init__(self, nocid=False):
        self.cfg = get_cfg()
        self.domain = self.cfg['domain']
        contest = self.cfg['contest']
        if contest == 0 and not nocid:
            print('ERROR: No contest was selected. Run "yacontest select <id>" first')
            sys.exit(1)
        self._select(contest)
        self.problems = self.cfg.get('problems')

        self.http = requests.Session()
        self.http.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.93 Safari/537.36'
        if self.cfg.get('cookies') is not None:
            self.http.cookies = self.cfg['cookies']

    def _select(self, cid):
        self.contest = cid
        self.prefix = f'https://{self.domain}/contest/{cid}'

    def _check_result(self, r):
        return urlparse(r.url).path != f'/contest/{self.contest}/enter/'

    def _update_cookies(self, r):
        soup = BS(r.text, "html.parser")
        link = soup.find('a', class_='link_access_login')
        if not link:
            print('ERROR: Contest is not available, check the URL:')
            print(self.prefix + '/enter')
            sys.exit(1)
        authpath = link['href']
        url = f"https://{self.domain}{authpath}"
        r = self.http.get(url)
        soup = BS(r.text, "html.parser")
        form = soup.find('form')
        data = {e['name']: e.get('value', '') for e in form.find_all('input')}
        data['login'] = self.cfg['login']
        data['password'] = self.cfg['password']
        if not data['password']:
            login = data['login']
            print(f'{login} is not authorized, password is needed to continue')
            data['password'] = getpass()
        r = self.http.post(url, data=data)
        if urlparse(r.url).path == '/login/':
            print('ERROR: Incorrect login or password, try again')
            print(f'Your login is "{self.cfg["login"]}". If it\'s incorrect, run "yacontest config"')
            self.cfg['password'] = ''
            set_cfg(self.cfg)
            sys.exit(1)
        self.cfg['cookies'] = self.http.cookies
        set_cfg(self.cfg)

    def _req_get(self, url, params=None):
        r = self.http.get(url, params=params)
        if not self._check_result(r):
            self._update_cookies(r)
            r = self.http.get(url, params=params)
        return r

    def _req_post(self, url, params=None, data=None):
        r = self.http.post(url, params=params, data=data)
        if not self._check_result(r):
            self._update_cookies(r)
            r = self.http.post(url, params=params, data=data)
        return r

    def _get_status(self, problem):
        try:
            url = self._get_problems()[problem]
        except KeyError:
            print(f'Invalid problem id, available problems: {", ".join(self._get_problems().keys())}')
            sys.exit(1)
        r = self._req_get(url, params={'ajax': 'submit-table'})
        soup = BS(r.json()['result'], "html.parser")
        rows = soup.find_all('tr')
        if len(rows) < 2:
            print('No solutions found!')
            sys.exit(1)
        titles = [e.text for e in rows[0].find_all('th')]
        cells = [e.text for e in rows[1].find_all('td')]
        return SolutionStatus(titles, cells)
 
    def _status_details(self, status):
        url = self.prefix + f'/run-report/{status.sid}/'
        r = self._req_get(url)
        soup = BS(r.text, "html.parser")
        details = [e.text.strip() for e in soup.find_all('pre')]
        if not details:
            details = ['No description available']
        delim = '\n' + '-' * 20 + '\n'
        return delim[1:] + delim.join(details) + delim[:-1]

    def _get_problems(self):
        if self.problems:
            return self.problems
        url = self.prefix + '/problems/'
        r = self._req_get(url)
        soup = BS(r.text, "html.parser")
        problems = soup.find_all('ul')[-1]
        self.problems = {e.find('a')['href'].split('/')[-2].lower(): 'https://' + self.domain + e.find('a')['href'] for e in problems.find_all('li')}  # NOTE assuming that url doesn't include domain and ends with "/", does YC guarantee this?
        self.cfg['problems'] = self.problems
        set_cfg(self.cfg)
        return self.problems

    def load_problems(self):
        dirname = os.path.join(os.getcwd(), 'problems')
        if os.path.exists(dirname):
            if os.path.isdir(dirname):
                if input('"./problems/" already exists! Overwrite? [yN]: ').lower().startswith('y'):
                    clean_dir(dirname)
                else:
                    return
            else:
                print('ERROR: "./problems" is not a directory! Delete/rename it manually to continue')
                return
        else:
            os.mkdir(dirname)
        print('Loading problem list...')
        problems = self._get_problems()
        for pid, url in problems.items():
            print(f'Downloading problem {pid}...')
            r = self._req_get(url)
            soup = BS(r.text, "html.parser")
            statement = Statement(soup.find("div", class_="problem-statement"))
            with open(os.path.join(dirname, f'{pid}.txt'), 'w') as f:
                f.write(str(statement) + '\n')

    def load_code(self, ids=[]):
        if not ids:
            ids = [self.contest]

        basedir = os.path.join(os.getcwd(), 'solutions')
        if os.path.exists(basedir):
            if not os.path.isdir(basedir):
                print('ERROR: "./solutions" is not a directory! Delete/rename it manually to continue')
                return
        else:
            os.mkdir(basedir)

        for cid in ids:
            dirname = os.path.join(basedir, str(cid))
            if os.path.exists(dirname):
                if os.path.isdir(dirname):
                    if input(f'"./solutions/{cid}/" already exists! Overwrite? [yN]: ').lower().startswith('y'):
                        clean_dir(dirname)
                    else:
                        print(f'Skipping contest {cid}')
                        continue
                else:
                    print(f'ERROR: "./solutions/{cid}" is not a directory! Skipping contest {cid}')
                    continue
            else:
                os.mkdir(dirname)

            if self.contest != cid:  # don't reset problems if no cids were supplied
                self.problems = None  # looks awful
            self._select(cid)  # refactor?
            print(f'Selected contest {cid}, downloading solutions...')
            page = 1
            saved_problems = set()
            while self._dump_solutions(dirname, page, saved_problems):
                page += 1

    def _dump_solutions(self, dirname, page, saved_problems):
        # NOTE may work incorrectly for large lists (> 100 submits, if YC uses multipage) (not tested)
        url = self.prefix + '/submits'
        r = self._req_get(url, params={'p': page})
        soup = BS(r.text, "html.parser")
        rows = soup.find_all('tr')
        if len(rows) < 2:
            return False
        # TODO add option to save latest solutions if no accepted are found?
        rows = rows[1:]
        ext_p = re.compile(r'filename\*?=.+(\.\w+)', re.I) # NOTE assuming that extension is alphanumeric # TODO refactor? ext can be followed by a quote
        for row in rows:
            a_pid, a_res, a_rep = row.find_all('a') # NOTE are links always present??
            pid = a_pid.text.lower()
            if pid in saved_problems:
                continue
            result = a_res.text
            if result != 'OK':
                continue
            filepath = os.path.join(dirname, pid)
            #NOTE assuming URL doesn't include domain
            url = 'https://' + self.domain + a_rep['href'].replace('run-report', 'download-source')  # one less request, shouldn't break until YC changes URLs
            r = self._req_get(url)
            matches = ext_p.findall(r.headers['content-disposition'])
            ext = matches[0] if matches else ''
            with open(filepath + ext, 'wb') as f:
                f.write(r.content)
            print(f'Loaded an accepted solution for {pid}!')
            saved_problems.add(pid)
        return True

    def submit(self, problem, filename, wait, compiler=None):
        if compiler is None:
            compiler = self.cfg.get('lang')
        problem = problem.lower()
        if not os.path.isfile(filename):
            print('ERROR: File not found')
            sys.exit(1)
        try:
            url = self._get_problems()[problem]
        except KeyError:
            print(f'Invalid problem id, available problems: {", ".join(self._get_problems().keys())}')
            sys.exit(1)
        r = self._req_get(url)
        soup = BS(r.text, "html.parser")
        form = soup.find_all('form')[-1]
        formdata = {}
        file_field = None
        compiler_choice = True
        for el in form.find_all('input'):
            name = el['name']
            if name.endswith('solution'):
                formdata[name] = 'file'
            elif name.endswith('compiler') or name.endswith('compilerId'):
                formdata[name] = el['value']
                compiler_choice = False
            elif name.endswith('file'):
                file_field = name
            else:
                formdata[name] = el['value']
        if compiler_choice:
            for el in form.find_all('select'):
                name = el['name']
                if name.endswith('compilerId'):
                    available = {}
                    if compiler is not None:
                        compiler = re.sub(r'\s+', ' ', compiler)
                    for comp in el.find_all('option'):
                        cname = re.sub(r"\s+", ' ', comp.text)
                        if cname == compiler:
                            formdata[name] = comp['value']
                            break
                        available[cname] = comp['value']
                    else:
                        if compiler is not None:
                            print('Unknown language: {}'.format(compiler))
                        compiler = choice('Select a language/compiler:', list(available.keys()))
                        if compiler is not None:
                            formdata[name] = available[compiler]
                        else:
                            print('Incorrect choice, try again')
                            sys.exit(1)
                    break
        url = self.prefix + '/submit/'
        r = self.http.post(url, data=formdata, files={file_field: (filename, open(filename, 'r'))})
        err = parse_qs(urlparse(r.url).query).get('error')
        if err:
            print('Error:', err[0])
            sys.exit(1)
        print('Uploaded!')
        if wait:
            print('Waiting...')
            status = self._get_status(problem)
            testing = False
            last_req = time()
            while not status.checked:
                if status.testing and not testing:
                    testing = True
                    print('Testing...')  # TODO show current test??
                sleep(max(0, 0.5 - (time() - last_req)))
                status = self._get_status(problem)
                last_req = time()
            print(status)
            if status.ce:
                print(self._status_details(status))

    def show_leaderboard(self, page=1):
        #TODO get additional info, print as a table?
        url = self.prefix + '/standings/'
        params = {'p': page}
        r = self._req_get(url, params=params)
        soup = BS(r.text, "html.parser")
        table = soup.find('table')
        if table is None:
            print('No results, try another page...')
            return
        data = [tr.find_all('td') for tr in table.find_all('tr')[1:]]
        last_task = None # element after last task
        if data:
            row = data[0]
            for i in range(2, len(row)):
                if row[i].find('div') is None:
                    last_task = i
                    break
        text = [[row[0].text, row[1].text, *[el.find('div').text for el in row[2:last_task]], *[el.text for el in row[last_task:]]] for row in data]
        cell_sizes = [max(map(len, col)) for col in zip(*text)]
        lines = []
        fmtstr = '  '.join(['{{:{}s}}'.format(sz) for sz in cell_sizes])
        for row in text:
            lines.append(fmtstr.format(*row)
)
        print('\n'.join(lines))

    def show_status(self, problem):
        problem = problem.lower()
        status = self._get_status(problem)
        print(status)
        if status.ce:
            print(self._status_details(status))

    def choose_lang(self):  # TODO refactor / remove copypaste in submit()
        url = sorted(self._get_problems().values())[0]
        r = self._req_get(url)
        soup = BS(r.text, "html.parser")
        form = soup.find_all('form')[-1]
        for el in form.find_all('input'):
            name = el['name']
            if name.endswith('compiler') or name.endswith('compilerId'):
                print('ERROR: No available languages!')
                return
        for el in form.find_all('select'):
            name = el['name']
            if name.endswith('compilerId'):
                available = {re.sub(r"\s+", ' ', comp.text): comp['value'] for comp in el.find_all('option')}
                compiler = choice('Select a language/compiler:', list(available.keys()))
                if compiler is not None:
                    self.cfg['lang'] = compiler
                    set_cfg(self.cfg)
                else:
                    print('Incorrect choice, try again')
                    sys.exit(1)
                break

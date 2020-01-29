import os
import sys
from base64 import b64decode
from getpass import getpass
from urllib.parse import urlparse, parse_qs
from time import time, sleep

import requests
from bs4 import BeautifulSoup as BS
from html2text import HTML2Text as H2T

from .config import get_cfg, set_cfg
from .utils import clean_dir


class SolutionStatus():
    def __init__(self, titles, values):
        for k, v in zip(titles, values):
            if k == 'ID':
                self.sid = v
            elif k == 'Вердикт':
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
        self.checked = not self.testing and not self.text.startswith('Ожидание') #TODO check correctness

    def __str__(self):
        msg = f'SOlution {self.sid}: {self.text}, Time: {self.time}, Mem: {self.mem}'
        if self.test:
            msg += f', Failed test: {self.test}'
        if self.score:
            msg += f', Score: {self.score}'
        return msg


class Statement():
    def __init__(self, html):
        images = html.find_all('img')
        tex_path = '/testsys/tex/render/'
        for im in images:
            src_path = urlparse(im['src']).path
            if src_path.startswith(tex_path):
                im.replace_with('$' + b64decode(src_path.rstrip('.png').lstrip(tex_path)).decode() + '$')
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
    def __init__(self):
        self.cfg = get_cfg()
        self.domain = self.cfg['domain']
        self.contest = self.cfg['contest']
        if self.contest == 0:
            print('ERROR: No contest was selected. Run "yacontest select <id>" first')
            sys.exit(1)
        self.problems = self.cfg.get('problems')

        self.http = requests.Session()
        self.http.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.93 Safari/537.36'
        if self.cfg.get('cookies') is not None:
            self.http.cookies = self.cfg['cookies']

        self.prefix = f'https://{self.domain}/contest/{self.contest}'

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
        self.problems = {e.find('a')['href'].split('/')[-2].lower(): 'https://' + self.domain + e.find('a')['href'] for e in problems.find_all('li')} #TODO optimize? check keys (url without trailing /)
        self.cfg['problems'] = self.problems
        set_cfg(self.cfg)
        return self.problems

    def load_problems(self):
        dirname = os.path.join(os.getcwd(), 'problems')
        if os.path.exists(dirname):
            if os.path.isdir(dirname):
                if input('"./problems" already exists! Overwrite? [yN]: ').lower().startswith('y'):
                    clean_dir(dirname)
                else:
                    return
            else:
                print('"ERROR: ./problems" is not a directory! Delete/rename it manually to continue')
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

    def submit(self, problem, filename, wait):
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
        fields = form.find_all('input')
        formdata = {}
        file_field = None
        for el in fields:
            name = el['name']
            if name.endswith('solution'):
                formdata[name] = 'file'
            elif name.endswith('compiler'):
                formdata[name] = el['value'] #TODO support multi-choice
            elif name.endswith('file'):
                file_field = name
            else:
                formdata[name] = el['value']
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
                    print('Testing...')
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
        text = [[row[0].text, row[1].text, *[el.find('div').text for el in row[2:-1]], row[-1].text] for row in data]
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

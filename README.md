# yacontest
This is a console utility for interaction with Yandex.Contest


## Installation
Python 3.6 or newer is required

```bash
git clone https://github.com/vvd170501/yacontest.git
cd yacontest
pip install --user .
```

## Usage
#### Create config file (stores ya.contest domain, login + (optionally) password)
`yacontest config`

#### Select a contest
If the contest URL is https://official.contest.yandex.ru/contest/123, use `yacontest select 123`

#### Save problem statements (text only)
`yacontest load` -- saves all statements to `./problems/`

#### Upload a solution
`yacontest send <file> <problem id>` -- upload and exit
`yacontest check <file> <problem id>` -- upload and wait for result
`yacontest send foo.cpp A` sends the contents of `foo.cpp` as a solution for problem A in the selected contest

#### Show status of the last solution
`yacontest status <problem id>`

#### Show leaderboard
`yacontest leaderboard [page]`


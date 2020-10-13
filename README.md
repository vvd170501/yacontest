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

#### Select/reset/show preferred compiler/language
`yacontest lang "language name"`

`yacontest lang list` for interactive choice (you need to select a contest first)

`yacontest lang reset`

`yacontest lang` -- show selected language

some of available languages/compilers: `GCC C++17`, `GNU c++17 7.3`, `Python 3.4` (should be exactly the same as shown in the contest webpage or one-time choice dialogue)

#### Save problem statements (text only)
`yacontest load` -- saves all statements to `./problems/`

#### Upload a solution
`yacontest send <file> <problem id> [--lang "language/compiler"]` -- upload and exit

`yacontest check <file> <problem id> [--lang "..."]` -- upload and wait for result

`yacontest send foo.cpp A` sends the contents of `foo.cpp` as a solution for problem A in the selected contest

lang option, if used, should be exactly the same as in one-time choice dialogue

#### Show status of the last solution
`yacontest status <problem id>`

#### Show leaderboard
`yacontest leaderboard [page]`

#### Download solutions
`yacontest loadcode [id1,id2,...]` -- download latest accepted solutions for contests with listed ids

`yacontest loadcode` -- download solutions for the selected contest

Solutions are saved as `./solutions/contest_id/task_id`

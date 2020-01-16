This is a console utility for interaction with Yandex.Contest

# Usage

### Create config file (stores ya.contest domain, login + (optionally) password)
`yacontest config`

### Select a contest
If the contest URL is https://official.contest.yandex.ru/contest/123, use `yacontest select 123`

### Upload a solution
`yacontest send <file> <problem id>` -- upload and exit
`yacontest check <file> <problem id>` -- upload and wait for result
Problem ids start with 1
`yacontest send foo.cpp 1` sends the contents of `foo.cpp` as a solution for the first problem in the selected contest

### Show leaderboard
`yacontest leaderboard [page]`

### Show status of the last solution
`yacontest status <problem id>`

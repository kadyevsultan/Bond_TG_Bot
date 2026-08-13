# Деплой bond_bot на serv00

serv00 — бесплатный шелл-хостинг на **FreeBSD**: 512 МБ RAM, 3 ГБ SSD, 15 процессов, SSH.
Карта не нужна. Выбран владельцем 2026-08-13 как единственный бескарточный вариант с
настоящей файловой системой (SQLite выживает рестарт) и без засыпания.

**Docker там не работает** — FreeBSD. `Dockerfile` и `docker-compose.yml` остаются для
любого другого хостинга, здесь бот запускается напрямую из venv под `tmux`.

## Шаг 0. Главный риск — проверить ДО всего остального

На FreeBSD нет готовых колёс с PyPI, а `pydantic-core` (жёсткая зависимость aiogram 3)
собирается только Rust-компилятором. **Rust в документации serv00 не заявлен**, и на их
форуме есть тема с ошибкой `Failed building wheel for maturin`.

Поэтому первым делом:

```bash
ssh ВАШ_ЛОГИН@sХХ.serv00.com
git clone https://github.com/ВАШ_АККАУНТ/bond_bot.git ~/bond_bot
bash ~/bond_bot/scripts/serv00/check-deps.sh
```

Скрипт печатает наличие python3.12/3.11, cargo, mise, tmux, sqlite3 — и пытается собрать
`pydantic` в одноразовом venv с однопоточной сборкой. Дальше два пути.

### Путь А — pydantic собрался

Идём в шаг 1.

### Путь Б — pydantic не собрался

Два варианта, по возрастанию возни:

**Б1. Поставить Rust через mise** (mise у serv00 в документации есть):

```bash
mise use -g rust@stable
rustc --version
export CARGO_BUILD_JOBS=1
```

и повторить `check-deps.sh`. Компиляция `pydantic-core` на 512 МБ RAM тяжёлая — обязательно
`CARGO_BUILD_JOBS=1`, иначе процесс упадёт по памяти или по лимиту в 15 процессов.

**Б2. Взять готовые бинарники из пакетов FreeBSD.** FreeBSD собирает `py311-pydantic2` сам,
и пакет можно распаковать в venv руками, без root:

```bash
fetch https://pkg.freebsd.org/FreeBSD:14:amd64/latest/All/py311-pydantic-core-X.Y.Z.pkg
tar -xf py311-pydantic-core-*.pkg -C /tmp/pc
cp -R /tmp/pc/usr/local/lib/python3.11/site-packages/* \
      ~/.virtualenvs/bond_bot/lib/python3.11/site-packages/
```

Версию пакета и ABI (`FreeBSD:14:amd64`) сверить с тем, что печатает `uname -a` и
`freebsd-version`. Это требует **Python 3.11**, а в `pyproject.toml` стоит `>=3.12` —
придётся ослабить до `>=3.11`. Код это переживёт: из свежего синтаксиса мы используем
`datetime.UTC` (3.11+) и `X | None` (3.10+), ничего специфичного для 3.12 нет.

Если не сработало ни Б1, ни Б2 — serv00 не наш вариант, возвращаемся к
[отчёту по хостингу](../reports/2026-08-13_hosting_and_cicd.md).

## Шаг 1. Аккаунт и доступ

1. Зарегистрироваться на serv00.com (бесплатно, без карты; регистрация иногда закрыта —
   бывают волны набора)
2. В панели включить **Binexec** — без него не работает собственный софт, включая venv
3. Загрузить свой SSH-ключ, проверить вход: `ssh ВАШ_ЛОГИН@sХХ.serv00.com`

## Шаг 2. Окружение и зависимости

```bash
mkdir -p ~/.virtualenvs
python3.12 -m venv ~/.virtualenvs/bond_bot        # или python3.11 для пути Б2
source ~/.virtualenvs/bond_bot/bin/activate

export MAKEFLAGS="-j1" CPUCOUNT=1 MAX_CONCURRENCY=1
export CFLAGS="-I/usr/local/include" CXXFLAGS="-I/usr/local/include"

cd ~/bond_bot
pip install --upgrade pip wheel
pip install -e .
```

`-e .` вместо poetry: на 512 МБ RAM тянуть ещё и Poetry незачем, зависимости описаны в
`pyproject.toml`. Переменные компиляции — из документации serv00, они обязательны из-за
лимита процессов.

Переменные окружения serv00 читает из `~/.bash_profile`, **не** из `~/.bashrc` — если
что-то экспортируете постоянно, пишите туда.

## Шаг 3. Конфигурация

```bash
cd ~/bond_bot
cp .env.example .env
vi .env
```

```
BOT_TOKEN=токен_от_BotFather
ADMIN_IDS=1055275164
DB_PATH=/usr/home/ВАШ_ЛОГИН/bond_bot_data/bond_bot.sqlite3
```

`DB_PATH` лучше вынести **за пределы** каталога репозитория: тогда `git pull` и любые
операции с рабочей копией физически не могут задеть базу.

## Шаг 4. Первый запуск

```bash
mkdir -p ~/bond_bot_data
chmod +x ~/bond_bot/scripts/serv00/*.sh
~/bond_bot/scripts/serv00/run.sh
tail -f ~/logs/bond_bot.log
```

В логе должно появиться применение миграций (`Running upgrade`), затем `Бот запущен`.
Миграции и сид встроенных тем выполняются автоматически при старте, отдельного шага нет.

Проверить процесс: `tmux ls`, зайти внутрь — `tmux attach -t bond_bot`, выйти без остановки —
`Ctrl+B`, затем `D`.

## Шаг 5. Автозапуск и присмотр

```bash
crontab -e
```

```cron
@reboot /usr/local/bin/bash /usr/home/ВАШ_ЛОГИН/bond_bot/scripts/serv00/run.sh
*/5 * * * * /usr/local/bin/bash /usr/home/ВАШ_ЛОГИН/bond_bot/scripts/serv00/watchdog.sh
0 4 * * * /usr/local/bin/sqlite3 /usr/home/ВАШ_ЛОГИН/bond_bot_data/bond_bot.sqlite3 ".backup '/usr/home/ВАШ_ЛОГИН/backups/daily.sqlite3'"
```

- `@reboot` — поднять бота после перезагрузки сервера
- watchdog каждые 5 минут — поднять, если процесс умер. Это же страхует от документированного
  правила serv00 «если к сайту нет запросов 24 часа, приложение выключается»: правило описано
  для веб-приложений, а не для процессов в `tmux`, но проверять это на живом боте не хочется
- бэкап базы раз в сутки. Забирать копию наружу: `scp ВАШ_ЛОГИН@sХХ.serv00.com:~/backups/daily.sqlite3 .`

## Шаг 6. Обновления

```bash
~/bond_bot/scripts/serv00/deploy.sh
```

Скрипт делает бэкап базы, `git pull --ff-only`, доустанавливает зависимости и перезапускает
`tmux`-сессию. Держит 14 последних бэкапов.

## Шаг 7. CI/CD (когда основное заработает)

GitHub Actions по SSH-ключу вызывает тот же `deploy.sh`:

```yaml
- uses: appleboy/ssh-action@v1
  with:
    host: ${{ secrets.SERV00_HOST }}
    username: ${{ secrets.SERV00_USER }}
    key: ${{ secrets.SERV00_SSH_KEY }}
    script: ~/bond_bot/scripts/serv00/deploy.sh
```

Тесты гонять в Actions на ubuntu-runner, а не на serv00 — там 512 МБ и лимит процессов.
Для тестов в CI нужен фиктивный `.env` (`BOT_TOKEN=123:fake`), потому что `Settings()`
создаётся при импорте `bond_bot.config`.

## Что важно помнить

- **Один экземпляр.** Два процесса на одном токене → `TelegramConflictError`. `deploy.sh`
  сначала убивает сессию, потом поднимает новую
- **Деплой обрывает активные партии** — они живут в памяти процесса
- **Бэкап обязателен.** 3 ГБ бесплатного диска — это не гарантия сохранности; пользовательские
  темы существуют только в этом файле
- **Poetry на сервере не нужен**, но `pyproject.toml` остаётся источником правды по зависимостям
- **Docker-файлы не удалять** — они пригодятся при переезде на любой Linux-хостинг

## Открытые вопросы, которые проверяются только на живом аккаунте

1. Соберётся ли `pydantic-core` (шаг 0) — главный
2. Есть ли `tmux` в системе; если нет — заменить в скриптах на `screen` или `nohup`
3. Применяется ли правило «24 часа без запросов → выключение» к процессам в `tmux`
4. Хватит ли 512 МБ при сборке зависимостей (при работе бот занимает ~80–120 МБ)

# Деплой bond_bot на alwaysdata (бесплатный план)

Выбран 2026-08-13 вместо serv00: регистрация без карты и без ожидания, **Linux** вместо
FreeBSD (значит колёса с PyPI ставятся как есть, `pydantic-core` компилировать не нужно),
а процесс держит и перезапускает сама платформа.

Условия бесплатного плана (с сайта alwaysdata): «Registration without credit card»,
«Valid without time limit», «0 € for life», «All features of the Plus offer», SSH включён.
По обзорам: **100 МБ диска, 256 МБ RAM**.

Замерено **на живом аккаунте** 2026-08-13: все зависимости приходят готовыми колёсами,
компиляции нет (`aiogram 3.30`, `pydantic-core 2.46.4`), Python 3.11/3.12/3.13, есть `git`,
`sqlite3`, `rsync`, `curl`.

Размер venv зависит от того, как ставить:

| Способ | Размер |
|---|---|
| `pip install` по умолчанию | **74 МБ** — байт-код `.pyc` занимает 27 МБ |
| `--no-compile` + чистка `__pycache__` | **47 МБ** |

Поэтому в скриптах стоит `--no-compile`, а служба запускается через `serve.sh`, который
выставляет `PYTHONDONTWRITEBYTECODE=1` — иначе Python создаст кеши заново при первом импорте
и съест те же 27 МБ. Итог: ~47 МБ venv + ~1 МБ код + ~1 МБ база + бэкап из 100 МБ.

Docker здесь не используется — бот запускается из venv как **служба** платформы.

## Что делается руками, а что автоматом

Руками — **три вещи, по одному разу**: SSH-ключ, секреты в GitHub, служба в панели.
Всё остальное делает GitHub Actions при каждом пуше в `main`.

Сервер при этом **ничего не знает про GitHub**: код заливается по `rsync` с раннера.
Работает и с приватным репозиторием, деплой-ключи на сервере не нужны.

## Шаг 1. SSH-ключ для деплоя

Локально:

```bash
ssh-keygen -t ed25519 -C "github-actions-bond-bot" -f ~/.ssh/bond_deploy -N ""
cat ~/.ssh/bond_deploy.pub     # это в панель
cat ~/.ssh/bond_deploy         # это в секрет GitHub
```

**Поля для ключа в панели нет** — оно есть только у Private Cloud. На общих аккаунтах ключ
кладётся в `~/.ssh/authorized_keys` по SSH, поэтому порядок такой:

1. В панели: **Remote access → SSH/SFTP → `bond`** — галочка `Enable password-based login`
   включена, пароль задан. Без этого первый вход невозможен и ключ положить некуда
2. Скопировать ключ на сервер:

```bash
ssh-copy-id -i ~/.ssh/bond_deploy.pub bond@ssh-bond.alwaysdata.net
```

Если `ssh-copy-id` нет:

```bash
cat ~/.ssh/bond_deploy.pub | ssh bond@ssh-bond.alwaysdata.net \
  'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

3. Проверить, что вход именно по ключу:

```bash
ssh -i ~/.ssh/bond_deploy -o PreferredAuthentications=publickey \
    bond@ssh-bond.alwaysdata.net "echo ok"
```

4. Только после этого снять галочку `Enable password-based login` в панели

alwaysdata принимает **только ED25519** — ключи DSA не поддерживаются; наш `ssh-keygen -t ed25519`
подходит. Passphrase должен быть пустым, иначе CI не сможет им воспользоваться.

## Шаг 2. Секреты в GitHub

Репозиторий → **Settings → Secrets and variables → Actions → New repository secret**:

| Секрет | Значение | Обязателен |
|---|---|---|
| `AD_SSH_HOST` | `ssh-bond.alwaysdata.net` | да |
| `AD_SSH_USER` | `bond` | да |
| `AD_SSH_KEY` | содержимое `~/.ssh/bond_deploy` (приватный ключ целиком) | да |
| `BOT_TOKEN` | токен от BotFather | да |
| `ADMIN_IDS` | `1055275164` | да |
| `AD_API_KEY` | токен из **Profile** (нужен security key) | нет, если настроен способ 2 |
| `AD_SERVICE_ID` | id службы из URL её страницы (у нас `28793`) | нет, если настроен способ 2 |

Токен бота хранится **только** в секретах GitHub. Файл `.env` на сервере пишет CI, и `rsync`
его никогда не перезаписывает и не удаляет — он в исключениях.

**Служба работает на отдельной машине от SSH-хоста** — выяснилось на живом сервере:
`hostname` в SSH выдаёт `ssh2`, а процесса бота в `ps -u bond` и `pgrep` нет вообще. Значит
погасить процесс из SSH нельзя, и перезапуск после деплоя нужно устраивать иначе. Есть два
способа, `restart.sh` поддерживает оба.

### Способ 1 — API (предпочтительный)

Токены лежат в **Profile**, а не в «Customer area → API». Для их выдачи alwaysdata может
потребовать security key (их двухфакторная защита).

Формат аутентификации из документации: `--basic --user "APIKEY account=bond:"` — двоеточие
на месте пароля обязательно, а **`account=bond` необходим**, иначе API не увидит службу
аккаунта. Проверить ключ:

```bash
curl --basic --user "КЛЮЧ account=bond:" https://api.alwaysdata.com/v1/service/
```

### Способ 2 — маркер и Monitoring command (без API и без security key)

`Monitoring command` платформа выполняет периодически: ненулевой код возврата = перезапуск
службы. Этим и пользуемся.

В панели, в поле **Monitoring command**:

```
/home/bond/bond_bot/scripts/alwaysdata/monitor.sh
```

Логика [monitor.sh](../../../scripts/alwaysdata/monitor.sh): если лежит маркер
`~/.bond_restart_requested` — удалить его и вернуть 1 (платформа перезапустит службу), иначе
вернуть 0. `restart.sh` без API-ключа просто создаёт маркер.

Проверку живости через `pgrep` в мониторинг **намеренно не добавляли**: из SSH процесс службы
не виден (она на другой машине), и если платформа когда-нибудь начнёт выполнять мониторинг в
таком же контексте, `pgrep` будет всегда возвращать 1 и служба уйдёт в бесконечный
перезапуск. Живость и так обеспечена: упавший процесс платформа поднимает сама.

Маркер удаляется до выхода с кодом 1 — поэтому перезапуск ровно один, цикла не будет
(проверено локально). Задержка — до одной проверки мониторинга, обычно меньше минуты.

## Шаг 3. Первый прогон

Запушить в `main` (или **Actions → CI → Run workflow**). Конвейер:

```
test    poetry install --with dev → ruff → pytest        (~1 минута)
deploy  rsync кода → .env из секретов → pip install -e . → перезапуск службы
```

Джоб `deploy` идёт только на пуше в `main` и только если `test` прошёл. `concurrency`
не даёт двум деплоям пересечься — важно, потому что двух ботов на одном токене быть не должно.

После первого прогона на сервере появятся `~/bond_bot`, `~/venv`, `~/bond_data` и `.env`.
Служба ещё не создана, поэтому шаг перезапуска честно скажет: «процесс не найден — запустите
службу в панели».

## Шаг 4. Служба (один раз)

Панель: **Advanced → Services → Add a service**.

| Поле | Значение |
|---|---|
| Command | `/home/bond/bond_bot/scripts/alwaysdata/serve.sh` |
| Working directory | `/home/bond/bond_bot` |

Через обёртку, а не напрямую `python -m bond_bot`: она выставляет `PYTHONDONTWRITEBYTECODE=1`
и `exec`-ает интерпретатор, то есть процесс остаётся в foreground, как требует платформа.
Порт не нужен, бот только исходящий.

Логи: `$HOME/admin/logs/services/ГОД/ID-ДАТА.log`, у нас
`~/admin/logs/services/2026/28793-2026-08-17.log`. Формат: `STDERR:` плюс наши строки, а
события платформы — `service: 28793 started / finished / restart requested`.

Упавшую службу платформа поднимает сама.

**Monitoring command** (необязательное поле) — команда, которую платформа гоняет
периодически; ненулевой код возврата = перезапуск. Поставили `pgrep -f "venv/bin/python -m
bond_bot"`. Если в логе появятся перезапуски каждую минуту — значит мониторинг выполняется не
на той машине, где живёт служба, и поле надо очистить.

Id службы из адресной строки её страницы — в секрет `AD_SERVICE_ID`.

## Шаг 5. Проверка

```bash
ssh -i ~/.ssh/bond_deploy bond@ssh-bond.alwaysdata.net
tail -f ~/admin/logs/services/*.log
du -sh ~                      # сколько из 100 МБ занято
```

В логе — миграции (`Running upgrade`), затем `Бот запущен`. В Telegram — `/start`.

Дальше деплой сводится к `git push`: тесты, заливка, перезапуск.

## Бэкап

Панель **Advanced → Scheduled tasks**, раз в сутки:

```
0 4 * * * /usr/bin/sqlite3 /home/bond/bond_data/bond_bot.sqlite3 ".backup '/home/bond/bond_data/backup.sqlite3'"
```

`deploy.sh` тоже делает копию перед каждым обновлением. Держим **одну** копию — диск 100 МБ.
Забирать к себе:

```bash
scp -i ~/.ssh/bond_deploy bond@ssh-bond.alwaysdata.net:~/bond_data/backup.sqlite3 ./backup-$(date +%F).sqlite3
```

Без выгрузки наружу бэкап бесполезен: пользовательские темы живут только в этом файле.

## Скрипты

| Файл | Когда |
|---|---|
| `scripts/alwaysdata/check-env.sh` | разово, посмотреть Python, квоту, память и что колёса ставятся без компиляции |
| `scripts/alwaysdata/deploy.sh` | вызывает CI: бэкап → venv → `pip install -e .` → перезапуск |
| `scripts/alwaysdata/restart.sh` | перезапуск через API, иначе гасит процесс |
| `scripts/alwaysdata/serve.sh` | команда для службы: запрещает `.pyc` и запускает бота |
| `scripts/alwaysdata/monitor.sh` | Monitoring command: перезапуск по маркеру + проверка живости |
| `scripts/alwaysdata/install.sh` | ручная установка, если деплоить без CI |

## Что помнить

- **Диск 100 МБ на всё.** Раз в неделю смотреть `du -sh ~`. Растут: логи службы, кеш pip
  (отключён), `__pycache__` (чистится скриптами), бэкапы (держим один)
- **RAM 256 МБ.** Бот занимает ~80–120 МБ. При превышении лимита система убивает процесс —
  служба его поднимет, но партии потеряются
- **Один экземпляр.** Второй процесс на том же токене → `TelegramConflictError`
- **Деплой и перезапуск обрывают активные партии** — они в памяти
- **Миграции применяются при старте** (`init_db()` → `alembic upgrade head`)
- Docker-файлы не удалять: пригодятся при переезде на Linux-хостинг с Docker

## Проверяется только на живом аккаунте

1. Доступна ли фича **Services** на бесплатном плане. Формулировка «all features of the Plus
   offer» это подразумевает, но точной документации по лимитам free я не нашёл.
   Если недоступна — запускать под `tmux` и поднимать по `cron @reboot` + watchdog, как в
   [инструкции для serv00](serv00.md)
2. Реальная квота диска (`quota -s` в `check-env.sh`)
3. Хватает ли 256 МБ RAM при установке зависимостей

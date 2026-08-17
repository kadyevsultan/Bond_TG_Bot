# Session 003 — 2026-08-17

**Mode:** DEEP (score: 46)
**Ветка:** main · коммиты `66a19e7`, `a106286`, `9b14d48`
**Продолжение:** session_002
**Тема:** Хостинг, деплой, CI/CD
**Статус:** завершено — бот работает 24/7

## TL;DR
Бот живёт на alwaysdata как служба `28793`, деплой — `git push` через GitHub Actions;
критерий «бесплатно и без карты» отсёк почти всё, а выбор упёрся в две вещи, которые видно
только на живом сервере: FreeBSD без колёс `pydantic-core` и служба на отдельной от SSH машине.

## Решения с WHY
| Решение | Альтернативы | WHY | Initiator | Turn | Risk if wrong |
|---|---|---|---|---|---|
| alwaysdata | GCP `e2-micro`, Oracle Always Free, Northflank, serv00, своё железо | единственный без карты, где Linux (колёса ставятся), диск постоянный и служба перезапускается сама | me → user | T12 | переезд ради 100 МБ квоты |
| CI заливает код `rsync` с раннера | `git pull` на сервере | сервер не знает про GitHub: работает с приватным репо, деплой-ключи на сервере не нужны | me | T14 | лишний секрет на сервере |
| `.env` пишет CI из секретов, через stdin | создать руками один раз; передать аргументом ssh | ротация в одном месте; аргументы команды видны в `ps` на сервере | me | T14 | утечка токена в список процессов |
| Poetry с лок-файлом в CI | `pip install ruff pytest` | свежий ruff добавил `UP042` и падал на `(str, Enum)` при локально зелёном прогоне | me | T15 | CI красный на неизменённом коде |
| `--no-compile` + `PYTHONDONTWRITEBYTECODE=1` | ставить как обычно | 74 МБ против 47 МБ при квоте 100 МБ | me | T22 | переполнение диска в первый месяц |
| Служба через обёртку `serve.sh` | `python -m bond_bot` напрямую | обёртка выставляет запрет `.pyc` и делает `exec`, процесс остаётся в foreground | me | T22 | кеши возвращают 27 МБ |
| Перезапуск: API **или** маркер + Monitoring command | только API (нужен security key) | владелец не хотел заводить security key | user | T27 | без обоих путей бот остаётся на старом коде |
| `monitor.sh` реагирует только на маркер | плюс проверка живости через `pgrep` | из SSH процесс службы не виден; если мониторинг попадёт в такой контекст — бесконечный перезапуск | me | T28 | служба перезапускается каждую минуту |
| serv00 → резерв, не основной | ждать одобрения регистрации | одобрение не пришло, а FreeBSD требует собирать `pydantic-core` Rust'ом | user | T11 | недели ожидания без деплоя |

## Открытия (скрытое/неочевидное)
- **Служба alwaysdata работает на отдельной машине от SSH-хоста:** `hostname` → `ssh2`, процесса
  бота нет ни в `ps -u bond`, ни в `pgrep`. Значит `pkill` из SSH бесполезен как способ
  перезапуска → `scripts/alwaysdata/restart.sh`
- **`poetry.toml` с `virtualenvs.create = false` ломает CI:** Poetry ставит пакеты в системный
  Python раннера и падает на `PermissionError: /usr/include/python3.12/greenlet` и
  `Cannot uninstall idna 3.6, RECORD file not found. Hint: The package was installed by debian`.
  Лечится переменными окружения — они приоритетнее файла → `.github/workflows/ci.yml`
- **`pydantic-settings` не разворачивает `$HOME` в `.env`** — `DB_PATH` должен быть абсолютным;
  подставляет сам сервер при записи файла
- **Basic-auth alwaysdata требует `account=`:** `--user "APIKEY account=bond:"`, иначе API не
  видит службу аккаунта
- **Мой `pkill -f "bond_bot"` убил бы сам `deploy.sh`** — путь скрипта содержит `bond_bot`
- venv на сервере: 74 МБ по умолчанию против 47 МБ с `--no-compile`; всего занято 55 МБ из 100
- GCP: внешний IPv4 стоит $0.005/час ≈ $3.65/мес, и **в описании Always Free про IP не сказано
  ничего** — ни что включён, ни что платный; сторонние обзоры противоречат друг другу
- GCP: после 90-дневного триала без ручного апгрейда ресурсы останавливаются, а данные
  «marked for deletion» — Always Free работает только на платном аккаунте
- Oracle отзывает простаивающие инстансы (95-й процентиль CPU < 20% за 7 дней) — polling-бот по
  этой формуле простаивает; политика описана только для Always Free аккаунтов
- Oracle 15.06.2026 без объявления урезал Always Free A1 с 4 OCPU/24 ГБ до 2 OCPU/12 ГБ
- serv00 — это бесплатная версия MyDevil.net; FreeBSD, поэтому `pydantic-core` без колёс

## Метрики / Numbers
| Что | Было | Стало | Источник |
|---|---|---|---|
| venv на сервере | 74 МБ | 47 МБ | `du -sh ~/venv` до/после `--no-compile` |
| Занято из квоты | — | 55 МБ из 100 МБ | `du -sh ~` |
| Аптайм службы после старта | — | 56 минут без перезапусков | лог `28793-2026-08-17.log` |
| CI: тесты | — | 128 зелёных, ruff 0.8.6 | прогон в чистом окружении |
| Квота GitHub Actions | — | 2000 мин/мес приватные, 500 МБ пакетов, 6 ч на job | документация GitHub |
| База на сервере | 0 | 14 тем / 372 слова / 1116 похожих | сид при первом старте |

## Внешние источники / Research
| Факт | Источник | Применимость |
|---|---|---|
| Fly.io: бесплатный тариф закрыт, минимум ~$5/мес | fly.io/docs/about/pricing | отсеян |
| Render: фоновые воркеры не в free tier, спит через 15 мин, диски платные | render.com/docs/free | отсеян |
| Koyeb: куплен Mistral AI 02.2026, free закрыт для новых | koyeb.com/docs/faqs/pricing | отсеян |
| GCP Always Free: `e2-micro`, 30 ГБ standard, 1 ГБ egress, US-регионы | docs.cloud.google.com/free | резерв, если нужна карта |
| Oracle: 1500 OCPU-часов A1, 200 ГБ, 10 ТБ + отзыв за простой | docs.oracle.com FreeTier | резерв при переводе в PAYG |
| alwaysdata: «Registration without credit card», «0 € for life», SSH включён | alwaysdata.com | выбран |
| alwaysdata: службы автоперезапускаются, foreground обязателен, логи в `admin/logs/services/` | help.alwaysdata.com | легло в `serve.sh` и панель |
| alwaysdata: ключи в `~/.ssh/authorized_keys`, поле в панели только у Private Cloud; только ED25519 | help.alwaysdata.com SSH | исправило мою неверную инструкцию |
| GitHub AUP запрещает «serverless hosting или запуск постоянных приложений» | docs.github.com AUP | Actions как хостинг отвергнут |
| PythonAnywhere: `api.telegram.org` в белом списке, но always-on только платно | pythonanywhere.com/whitelist | отсеян |
| Amvera: 111 ₽ стартового баланса без карты на месяц | amvera.ru | резерв |

## Отвергнутые подходы
| Подход | kind | Причина отказа | Кто отверг | Commit (if TRIED) |
|---|---|---|---|---|
| serv00 (FreeBSD) | TRIED | регистрацию не подтвердили; `pydantic-core` требует Rust, которого нет в их документации | user | `a8613d8` — оставлено резервом |
| GitHub Actions как хостинг | CONSIDERED | AUP запрещает; 6 ч на job; нет постоянного диска; на стыке job'ов два бота → `TelegramConflictError` | me | — |
| Hugging Face Spaces | CONSIDERED | диск эфемерный ($5/мес за постоянный), спит через 48 ч без визитов | me | — |
| Vercel / Cloudflare Workers | CONSIDERED | serverless ломает партии в памяти и SQLite-файл | me | — |
| `pip install ruff pytest` в CI | TRIED | свежий ruff (`UP042`) красный на локально зелёном коде | me | заменено в `66a19e7` |
| `pkill` как способ перезапуска службы | TRIED | процесс службы не виден из SSH — другая машина | me | заменено в `9b14d48` |
| `pgrep` в Monitoring command | TRIED | риск бесконечного перезапуска, если мониторинг переедет в контекст без видимости процесса | me | убрано в `9b14d48` |
| Секреты `AD_API_KEY`/`AD_SERVICE_ID` как обязательные | CONSIDERED | требуют security key; маркерный путь даёт то же с задержкой до минуты | user | — |

## Поправки юзера
| Поправка | Контекст | Scope применения |
|---|---|---|
| «шаги по деплою не правильные — я хочу чтобы мы сделали github action» | я расписал ручную установку по SSH | деплой только через CI/CD; ручные шаги — три разовых |
| «в панели alwaysdata нет отдельного поля для ssh ключей» | я сослался на несуществующее поле | ключ кладётся в `~/.ssh/authorized_keys`, пароль включать до этого |
| «нужно создать security key для API-ключа» | я объявил API обязательным | добавлен маркерный перезапуск без API |
| «serv00 после регистрации не ответили — нужен другой вариант» | ждали одобрения | переход на alwaysdata за одну сессию |

## Открытые вопросы к юзеру
- [ ] Заменить `Monitoring command` в панели на `/home/bond/bond_bot/scripts/alwaysdata/monitor.sh`
- [ ] Заводить ли `AD_API_KEY` / `AD_SERVICE_ID` (мгновенный перезапуск против задержки до минуты)
- [ ] Отключить `Enable password-based login` — вход по ключу проверен

## WIP / Незавершено
- [ ] Бэкап: задача в **Advanced → Scheduled tasks** и регулярная выгрузка `scp` наружу
- [ ] Следить неделю за логом службы: если появятся перезапуски каждую минуту — очистить
      `Monitoring command`
- [ ] Долги из отчёта по техдолгу: A5, A6, B4, C1–C5, D1–D3

## Сделано (только не-reconstruct-able)
- Служба в панели: id `28793`, команда `scripts/alwaysdata/serve.sh`, рабочий каталог
  `/home/bond/bond_bot` — в репозитории этого нет, только в панели alwaysdata
- Ключ деплоя `~/.ssh/bond_deploy` (ED25519, без пароля) лежит в `authorized_keys` на сервере и
  в секрете `AD_SSH_KEY`; личный `id_ed25519` намеренно не использован — чтобы отзыв ключа CI
  не ломал остальные доступы
- `monitor.sh` удаляет маркер **до** выхода с кодом 1 — иначе перезапуск повторялся бы вечно

## Изменённые файлы (pointer only)
| Файл | Тип | Зачем (нетривиально) |
|---|---|---|
| `.github/workflows/ci.yml` | new | `POETRY_VIRTUALENVS_CREATE=true` + `poetry env use` обходят `poetry.toml`; `concurrency: deploy-production` не даёт двум деплоям пересечься |
| `scripts/alwaysdata/serve.sh` | new | команда службы: запрет `.pyc`, `exec` для foreground |
| `scripts/alwaysdata/monitor.sh` | new | маркерный перезапуск, единственный путь без API-ключа |
| `scripts/alwaysdata/restart.sh` | new | API с `account=`, иначе маркер; ошибки API не глотает |
| `docs_claude/project/deploy/alwaysdata.md` | new | инструкция с замерами и открытыми вопросами |

## Для следующей сессии
- [ ] Бэкап-задача и первая выгрузка копии базы
- [ ] Живая игра: проверить музыкальный режим и вердикт шпиона на сервере
- [ ] Если понадобится больше ресурсов: Oracle в PAYG (2 OCPU / 12 ГБ) или своё железо —
      разбор в `docs_claude/project/reports/2026-08-13_hosting_and_cicd.md`

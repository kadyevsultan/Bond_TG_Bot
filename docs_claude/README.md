# docs_claude — архив знаний проекта

Трёхслойная система. Этот каталог — **третий слой**: не грузится автоматически,
читается по необходимости.

| Слой | Где | Автозагрузка | Назначение |
|---|---|---|---|
| CLAUDE.md | корень | да, каждый разговор | Запреты, инварианты, self-check |
| .claude/rules/ | `.claude/rules/` | да, каждый разговор | Домен, архитектура, стиль, ловушки |
| docs_claude/ | здесь | **нет** | Полные карты, отчёты, журнал сессий |
| memory/ | `~/.claude/projects/-Users-kadyevsultan521-Desktop-bond-bot/memory/` | индекс | Решения владельца, состояние |

## Что где

```
project/architecture/   PROJECT_STRUCTURE.md, MODELS_MAP.md, GAME_ENGINE_MAP.md, UI_MAP.md
project/business/       DOMAIN_MODEL.md, BUSINESS_RULES.md, DECISIONS_LOG.md
project/issues/         KNOWN_ISSUES.md, TECHNICAL_DEBT.md
project/reports/        (глубокие разборы по мере появления)
sessions/               README.md — журнал по дням, YYYY-MM-DD/session_NNN.md
knowledge/              (внешние материалы, исследования)
```

## Когда сюда идти

- Нужна полная карта моделей или всех экранов — `project/architecture/`
- Нужно понять **почему** решение такое, а не другое — `project/business/DECISIONS_LOG.md`
- Что уже сломано и известно — `project/issues/`
- Что делали в прошлый раз — `sessions/README.md`

Дистиллят этих файлов лежит в `.claude/rules/` — там короче и грузится всегда.

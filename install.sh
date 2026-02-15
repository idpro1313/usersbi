#!/usr/bin/env bash
# Установка и запуск приложения «Сводная AD / MFA / Кадры» на Ubuntu.
# Запуск из корня репозитория (после git clone):
#   ./install.sh        — первый запуск или обычный старт
#   ./install.sh update — обновление из GitHub и пересборка контейнера
# Пути относительные от каталога, куда клонирован проект.

set -e

# Корень проекта = каталог, где лежит этот скрипт (репозиторий)
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

DATA_DIR="${PROJECT_ROOT}/data"
COMPOSE_OPTS=(-f "${PROJECT_ROOT}/docker-compose.yml" --project-directory "$PROJECT_ROOT")

echo "Проект: ${PROJECT_ROOT}"

if [ "${1:-}" = "update" ]; then
  echo "Режим: обновление из GitHub"
  if [ -d .git ]; then
    git pull
  else
    echo "Каталог .git не найден, обновление пропущено."
  fi
  echo "Пересборка контейнера (с кэшем слоёв)..."
  docker compose "${COMPOSE_OPTS[@]}" build
else
  echo "Режим: установка / запуск"
  docker compose "${COMPOSE_OPTS[@]}" build
fi

mkdir -p "$DATA_DIR"
echo "Каталог данных: ${DATA_DIR}"

docker compose "${COMPOSE_OPTS[@]}" up -d

docker image prune -f

echo ""
echo "Приложение запущено. Откройте в браузере: http://localhost:3456"
echo "БД и настройки хранятся в: ${DATA_DIR}"

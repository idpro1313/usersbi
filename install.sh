#!/usr/bin/env bash
# Установка и запуск приложения «Девелоника Пользователи» на Ubuntu.
# Первый запуск:
#   git clone https://gitlabacr.aplanadc.ru/IYatsishen/usersbi.git
#   cd usersbi && ./install.sh
# Обновление:
#   ./install.sh update — обновление из GitLab и пересборка контейнера

set -e

# Корень проекта = каталог, где лежит этот скрипт (репозиторий)
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

DATA_DIR="${PROJECT_ROOT}/data"
COMPOSE_OPTS=(-f "${PROJECT_ROOT}/docker-compose.yml" --project-directory "$PROJECT_ROOT")

echo "Проект: ${PROJECT_ROOT}"

if [ "${1:-}" = "update" ]; then
  echo "Режим: обновление из GitLab"
  if [ -d .git ]; then
    # Запоминаем текущий коммит
    OLD_HEAD=$(git rev-parse HEAD)
    git pull
    NEW_HEAD=$(git rev-parse HEAD)

    if [ "$OLD_HEAD" = "$NEW_HEAD" ]; then
      echo "Обновлений нет — контейнер не перезапускается."
      exit 0
    fi

    echo "Обнаружены изменения (${OLD_HEAD:0:8} → ${NEW_HEAD:0:8}), пересборка..."
  else
    echo "Каталог .git не найден, обновление пропущено."
    exit 0
  fi
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

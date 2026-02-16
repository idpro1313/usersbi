<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const BRAND = 'Девелоника Пользователи'
const ITEMS = [
  { to: '/upload',     label: 'Загрузка' },
  { to: '/',           label: 'Сводная' },
  { to: '/users',      label: 'Пользователи' },
  { to: '/groups',     label: 'Группы AD' },
  { to: '/structure',  label: 'Структура OU' },
  { to: '/org',        label: 'Организация' },
  { to: '/duplicates', label: 'Дубли' },
  { to: '/security',   label: 'Безопасность' },
]

function isActive(to) {
  if (to === '/') return route.path === '/'
  return route.path.startsWith(to)
}
</script>

<template>
  <nav class="main-nav">
    <div class="main-nav-inner">
      <span class="main-nav-brand">{{ BRAND }}</span>
      <div class="main-nav-links">
        <router-link
          v-for="item in ITEMS"
          :key="item.to"
          :to="item.to"
          class="main-nav-item"
          :class="{ active: isActive(item.to) }"
        >
          {{ item.label }}
        </router-link>
      </div>
    </div>
  </nav>
</template>

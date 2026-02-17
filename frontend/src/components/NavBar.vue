<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from '../composables/useTheme'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const { mode, cycle } = useTheme()
const { isLoggedIn, isAdmin, displayName, logout } = useAuth()

const BRAND = 'Девелоника Пользователи'

const NAV_ITEMS = [
  { to: '/',           label: 'Сводная',       needsAuth: true },
  { to: '/users',      label: 'Пользователи',  needsAuth: true },
  { to: '/groups',     label: 'Группы AD',      needsAuth: true },
  { to: '/structure',  label: 'Структура OU',   needsAuth: true },
  { to: '/org',        label: 'Организация',    needsAuth: true },
  { to: '/duplicates', label: 'Дубли',          needsAuth: true },
  { to: '/security',   label: 'Безопасность',   needsAuth: true },
  { to: '/settings',   label: 'Настройки',      needsAuth: true, adminOnly: true },
]

const visibleItems = computed(() =>
  NAV_ITEMS.filter(item => {
    if (item.needsAuth && !isLoggedIn.value) return false
    if (item.adminOnly && !isAdmin.value) return false
    return true
  })
)

function isActive(to) {
  if (to === '/') return route.path === '/'
  return route.path.startsWith(to)
}

function doLogout() {
  logout()
  router.push('/login')
}

const themeIcons = { auto: '◑', light: '☀', dark: '☾' }
const themeLabels = { auto: 'Авто', light: 'Светлая', dark: 'Тёмная' }
</script>

<template>
  <nav class="main-nav" v-if="route.meta?.hideNav !== true">
    <div class="main-nav-inner">
      <span class="main-nav-brand">{{ BRAND }}</span>
      <div class="main-nav-links">
        <router-link
          v-for="item in visibleItems"
          :key="item.to"
          :to="item.to"
          class="main-nav-item"
          :class="{ active: isActive(item.to) }"
        >
          {{ item.label }}
        </router-link>
      </div>
      <div class="main-nav-right">
        <span v-if="isLoggedIn" class="nav-user-name" :title="displayName">{{ displayName }}</span>
        <button v-if="isLoggedIn" class="btn-nav-logout" title="Выйти" @click="doLogout">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
        <button class="btn-theme" :title="'Тема: ' + themeLabels[mode]" @click="cycle">
          {{ themeIcons[mode] }}
        </button>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.main-nav-right {
  display: flex;
  align-items: center;
  gap: .5rem;
  margin-left: auto;
}
.nav-user-name {
  font-size: .85rem;
  color: var(--muted);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.btn-nav-logout {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--muted);
  padding: .25rem;
  border-radius: 4px;
  transition: color .2s, background .2s;
}
.btn-nav-logout:hover {
  color: var(--danger, #e53935);
  background: rgba(229,57,53,.08);
}
</style>

import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const routes = [
  { path: '/login',     name: 'login',        component: () => import('../views/LoginView.vue'),     meta: { public: true, hideNav: true } },
  { path: '/',          name: 'consolidated',  component: () => import('../views/ConsolidatedView.vue') },
  { path: '/settings',  name: 'settings',      component: () => import('../views/SettingsView.vue'),  meta: { requiresAdmin: true } },
  { path: '/users',     name: 'users',         component: () => import('../views/UsersView.vue') },
  { path: '/groups',    name: 'groups',        component: () => import('../views/GroupsView.vue') },
  { path: '/structure', name: 'structure',     component: () => import('../views/StructureView.vue') },
  { path: '/org',       name: 'org',           component: () => import('../views/OrgView.vue') },
  { path: '/duplicates',name: 'duplicates',    component: () => import('../views/DuplicatesView.vue') },
  { path: '/security',  name: 'security',      component: () => import('../views/SecurityView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const { isLoggedIn, isAdmin, getAuthStatus } = useAuth()

  if (to.meta.public) return true

  const configured = await getAuthStatus()
  if (!configured) {
    if (to.name === 'settings') return true
    return { name: 'settings' }
  }

  if (!isLoggedIn.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.requiresAdmin && !isAdmin.value) {
    return { name: 'consolidated' }
  }

  return true
})

export default router

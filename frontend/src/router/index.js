import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/',          name: 'consolidated', component: () => import('../views/ConsolidatedView.vue') },
  { path: '/upload',    name: 'upload',       component: () => import('../views/UploadView.vue') },
  { path: '/users',     name: 'users',        component: () => import('../views/UsersView.vue') },
  { path: '/groups',    name: 'groups',       component: () => import('../views/GroupsView.vue') },
  { path: '/structure', name: 'structure',    component: () => import('../views/StructureView.vue') },
  { path: '/org',       name: 'org',          component: () => import('../views/OrgView.vue') },
  { path: '/duplicates',name: 'duplicates',   component: () => import('../views/DuplicatesView.vue') },
  { path: '/security',  name: 'security',     component: () => import('../views/SecurityView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'

const router = useRouter()
const auth = useAuth()
const toast = useToast()

const username = ref('')
const password = ref('')
const domain = ref('izhevsk')
const loading = ref(false)
const authConfigured = ref(true)
const hasLdap = ref(false)

const domains = [
  { value: 'izhevsk', label: 'Ижевск' },
  { value: 'kostroma', label: 'Кострома' },
  { value: 'moscow', label: 'Москва' },
]

async function handleLogin() {
  if (!username.value.trim() || !password.value) {
    toast.warn('Введите логин и пароль')
    return
  }
  loading.value = true
  try {
    await auth.login(username.value.trim(), password.value, domain.value)
    toast.success('Добро пожаловать!')
    const redirect = router.currentRoute.value.query.redirect || '/'
    router.push(redirect)
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (auth.isLoggedIn.value) {
    const ok = await auth.checkAuth()
    if (ok) { router.push('/'); return }
  }
  try {
    const r = await fetch('/api/auth/status')
    const data = await r.json()
    authConfigured.value = data.configured
    hasLdap.value = data.ldap
  } catch {
    authConfigured.value = false
  }
})
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1 class="login-title">Девелоника</h1>
        <p class="login-subtitle">Управление пользователями</p>
      </div>

      <template v-if="authConfigured">
        <form class="login-form" @submit.prevent="handleLogin">
          <div class="form-group">
            <label for="login-user">Логин</label>
            <input id="login-user" v-model="username" type="text" autocomplete="username"
              placeholder="Имя пользователя" autofocus>
          </div>
          <div class="form-group">
            <label for="login-pass">Пароль</label>
            <input id="login-pass" v-model="password" type="password" autocomplete="current-password">
          </div>
          <div v-if="hasLdap" class="form-group">
            <label for="login-domain">Домен</label>
            <select id="login-domain" v-model="domain">
              <option v-for="d in domains" :key="d.value" :value="d.value">{{ d.label }}</option>
            </select>
          </div>
          <button type="submit" class="btn btn-login" :disabled="loading">
            {{ loading ? 'Вход…' : 'Войти' }}
          </button>
        </form>
      </template>

      <template v-else>
        <div class="login-setup-msg">
          <p>Авторизация не настроена.</p>
          <p>Обратитесь к администратору для настройки.</p>
          <button class="btn" @click="router.push('/settings')">Перейти к настройке</button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--bg);
  padding: 1rem;
}
.login-card {
  background: var(--surface);
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0,0,0,.12);
  padding: 2.5rem 2rem;
  width: 100%;
  max-width: 400px;
}
.login-header {
  text-align: center;
  margin-bottom: 2rem;
}
.login-title {
  font-family: var(--font-brand);
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--accent);
  margin: 0;
}
.login-subtitle {
  color: var(--muted);
  margin: .25rem 0 0;
  font-size: .95rem;
}
.login-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: .35rem;
}
.form-group label {
  font-size: .85rem;
  font-weight: 500;
  color: var(--text);
}
.form-group input,
.form-group select {
  padding: .6rem .75rem;
  border: 1.5px solid var(--border);
  border-radius: 6px;
  font-size: .95rem;
  background: var(--bg);
  color: var(--text);
  transition: border-color .2s;
}
.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--accent);
}
.btn-login {
  margin-top: .5rem;
  padding: .7rem;
  font-size: 1rem;
  font-weight: 600;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: opacity .2s;
}
.btn-login:hover { opacity: .9; }
.btn-login:disabled { opacity: .5; cursor: not-allowed; }
.login-setup-msg {
  text-align: center;
  color: var(--muted);
  line-height: 1.6;
}
.login-setup-msg .btn {
  margin-top: 1rem;
}
</style>

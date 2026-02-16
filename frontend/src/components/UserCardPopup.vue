<script setup>
import { ref, onMounted } from 'vue'
import PopupOverlay from './PopupOverlay.vue'
import FieldsTable from './FieldsTable.vue'
import AdSections from './AdSections.vue'
import LoadingSpinner from './LoadingSpinner.vue'
import { fetchJSON } from '../api'

const props = defineProps({
  userKey: { type: String, required: true },
  displayName: { type: String, default: '' },
})
const emit = defineEmits(['close', 'open-dn', 'open-card'])

const data = ref(null)
const error = ref('')
const title = ref(props.displayName || 'Карточка УЗ')

onMounted(async () => {
  try {
    data.value = await fetchJSON('/api/users/card?key=' + encodeURIComponent(props.userKey))
    if (data.value.fio) title.value = data.value.fio
  } catch (e) {
    error.value = e.message
  }
})

function summaryParts() {
  if (!data.value) return []
  const d = data.value
  const sp = []
  if (d.city) sp.push(['Город', d.city])
  if (d.hub) sp.push(['Локация', d.hub])
  if (d.dp_unit) sp.push(['Подразделение DP', d.dp_unit])
  if (d.rm) sp.push(['RM', d.rm])
  return sp
}
</script>

<template>
  <PopupOverlay :title="title" wide @close="emit('close')">
    <p v-if="error" class="muted-text">Ошибка: {{ error }}</p>
    <LoadingSpinner v-else-if="!data" />
    <template v-else>
      <!-- Header -->
      <div class="ucard-header">
        <h2 class="ucard-fio">{{ data.fio || '—' }}</h2>
        <span v-if="data.staff_uuid" class="ucard-uuid">StaffUUID: {{ data.staff_uuid }}</span>
        <span v-if="data.logins?.length" class="ucard-logins">Логины: {{ data.logins.join(', ') }}</span>
        <div v-if="summaryParts().length" class="ucard-summary">
          <span v-for="sp in summaryParts()" :key="sp[0]" class="ucard-summary-item">
            <b>{{ sp[0] }}:</b> {{ sp[1] }}
          </span>
        </div>
      </div>

      <!-- People -->
      <div v-if="data.people" class="ucard-section">
        <h3 class="ucard-section-title">Кадры</h3>
        <FieldsTable :pairs="[
          ['ФИО', data.people.fio], ['Email', data.people.email],
          ['Телефон', data.people.phone], ['Подразделение', data.people.unit],
          ['Хаб', data.people.hub], ['Статус', data.people.employment_status],
          ['RM', data.people.unit_manager],
        ]" />
      </div>

      <!-- AD -->
      <div v-if="data.ad?.length" class="ucard-section">
        <h3 class="ucard-section-title">Учётные записи AD ({{ data.ad.length }})</h3>
        <div v-for="(a, i) in data.ad" :key="i"
          class="ucard-ad-block" :class="{ 'uz-inactive': a.enabled === 'Нет' }">
          <div class="ucard-ad-domain">{{ a.domain }} — {{ a.login }}</div>
          <AdSections :account="a" @open-dn="(dn, name) => emit('open-dn', dn, name)" />
        </div>
      </div>

      <!-- MFA -->
      <div v-if="data.mfa?.length" class="ucard-section">
        <h3 class="ucard-section-title">MFA ({{ data.mfa.length }})</h3>
        <div v-for="(m, j) in data.mfa" :key="j" class="ucard-mfa-block">
          <FieldsTable :pairs="[
            ['Identity', m.identity], ['Статус', m.status],
            ['Последний вход', m.last_login], ['Аутентификаторы', m.authenticators],
          ]" />
        </div>
      </div>
    </template>
  </PopupOverlay>
</template>

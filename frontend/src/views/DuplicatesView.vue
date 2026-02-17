<script setup>
import { ref, onMounted } from 'vue'
import MembersTable from '../components/MembersTable.vue'
import { fetchJSON } from '../api'
import { useExport } from '../composables/useExport'

const COLUMNS = [
  { key: 'login',             label: 'Логин' },
  { key: 'domain',            label: 'Домен AD' },
  { key: 'display_name',      label: 'ФИО' },
  { key: 'email',             label: 'Email' },
  { key: 'phone',             label: 'Телефон' },
  { key: 'mobile',            label: 'Мобильный' },
  { key: 'enabled',           label: 'Активна' },
  { key: 'account_type',      label: 'Тип УЗ' },
  { key: 'password_last_set', label: 'Смена пароля' },
  { key: 'account_expires',   label: 'Срок УЗ' },
  { key: 'staff_uuid',        label: 'StaffUUID' },
  { key: 'title',             label: 'Должность' },
  { key: 'department',        label: 'Отдел' },
  { key: 'company',           label: 'Компания' },
]

const DATE_KEYS = { password_last_set: true, account_expires: true }

const rows = ref([])
const statsText = ref('')
const loading = ref(true)
const { exportToXLSX } = useExport()

onMounted(async () => {
  try {
    const data = await fetchJSON('/api/duplicates')
    rows.value = data.rows || []
    statsText.value = 'Уникальных логинов: ' + data.unique_logins + ' | Записей: ' + data.total_records
  } catch (e) {
    statsText.value = 'Ошибка: ' + e.message
  } finally {
    loading.value = false
  }
})

function doExport() {
  if (!rows.value.length) return
  exportToXLSX(COLUMNS, rows.value, 'Дубли_логинов_AD.xlsx', 'Дубли')
}
</script>

<template>
  <div class="table-toolbar">
    <h2>Дубли логинов между AD</h2>
    <span class="muted-text">{{ statsText }}</span>
    <button type="button" class="btn-icon btn-export" title="Выгрузить XLSX" @click="doExport">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
    </button>
  </div>
  <div class="table-container">
    <MembersTable
      :columns="COLUMNS"
      :rows="rows"
      :dateKeys="DATE_KEYS"
      :loading="loading"
      emptyMessage="Дублей логинов между доменами AD не найдено"
    />
  </div>
</template>

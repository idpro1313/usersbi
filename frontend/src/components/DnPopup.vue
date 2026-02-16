<script setup>
import { ref, onMounted } from 'vue'
import PopupOverlay from './PopupOverlay.vue'
import LoadingSpinner from './LoadingSpinner.vue'
import FieldsTable from './FieldsTable.vue'
import { fetchJSON } from '../api'

const props = defineProps({
  dn: { type: String, required: true },
  displayName: { type: String, default: '' },
})
const emit = defineEmits(['close', 'open-card'])

const error = ref('')
const parsed = ref(null)

onMounted(async () => {
  try {
    const data = await fetchJSON('/api/users/by-dn?dn=' + encodeURIComponent(props.dn))
    if (data.found && data.key) {
      emit('open-card', data.key, data.display_name || props.displayName)
      emit('close')
      return
    }
    const cn = props.dn.match(/^CN=([^,]+)/i)
    const name = cn ? cn[1] : props.dn
    const ous = []
    const re = /OU=([^,]+)/gi
    let match
    while ((match = re.exec(props.dn)) !== null) ous.push(match[1])
    ous.reverse()
    parsed.value = { name, ous, dn: props.dn }
  } catch (e) {
    error.value = e.message
  }
})
</script>

<template>
  <PopupOverlay :title="displayName || 'Объект AD'" wide @close="emit('close')">
    <p v-if="error" class="muted-text">Ошибка: {{ error }}</p>
    <LoadingSpinner v-else-if="!parsed" />
    <template v-else>
      <FieldsTable :pairs="[
        ['Имя (CN)', parsed.name],
        ['OU', parsed.ous.length ? parsed.ous.join(' › ') : ''],
        ['Полный DN', parsed.dn],
      ]" />
      <p class="muted-text" style="margin-top:12px">
        Объект не найден среди учётных записей пользователей в базе данных.
      </p>
    </template>
  </PopupOverlay>
</template>

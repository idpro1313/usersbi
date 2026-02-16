<script setup>
import { escapeHtml } from '../utils/format'

const props = defineProps({
  dnString: { type: String, default: '' },
  asGroups: { type: Boolean, default: false },
})
const emit = defineEmits(['dn-click'])

function parseDns() {
  if (!props.dnString) return []
  return props.dnString.split(';').map(s => s.trim()).filter(Boolean).map(dn => {
    const cn = dn.match(/^CN=([^,]+)/i)
    return { dn, display: cn ? cn[1] : dn }
  })
}

function onClick(entry) {
  emit('dn-click', entry.dn, entry.display)
}
</script>

<template>
  <template v-if="asGroups">
    <span v-for="(entry, i) in parseDns()" :key="i">
      <span v-if="i > 0">; </span>{{ entry.display }}
    </span>
  </template>
  <template v-else>
    <span v-for="(entry, i) in parseDns()" :key="i">
      <span v-if="i > 0">; </span>
      <a class="ucard-link" href="#" @click.prevent="onClick(entry)">{{ entry.display }}</a>
    </span>
  </template>
</template>

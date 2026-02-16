<script setup>
const props = defineProps({
  pairs: { type: Array, required: true },
})

function isHtml(v) { return v && typeof v === 'object' && v.html !== undefined }
function needsLong(v) {
  if (isHtml(v)) return true
  return typeof v === 'string' && v.length > 80
}
</script>

<template>
  <table class="ucard-fields" v-if="pairs.some(p => p[1])">
    <tr v-for="(pair, i) in pairs" :key="i" v-show="pair[1]">
      <td class="ucard-label">{{ pair[0] }}</td>
      <td v-if="isHtml(pair[1])" class="ucard-val-long" v-html="pair[1].html"></td>
      <td v-else :class="{ 'ucard-val-long': needsLong(pair[1]) }">{{ pair[1] || '' }}</td>
    </tr>
  </table>
  <p v-else class="muted-text">Нет данных</p>
</template>

<script setup>
defineProps({
  text: { type: String, default: '' },
  size: { type: String, default: '24px' },
})
</script>

<template>
  <div class="spinner-wrap">
    <div class="spinner" :style="{ width: size, height: size }"></div>
    <span v-if="text" class="spinner-text">{{ text }}</span>
  </div>
</template>

<style>
.spinner-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 1.5rem 0;
}
.spinner-text {
  color: var(--muted);
  font-size: 0.85rem;
}
.spinner {
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

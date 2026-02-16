<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import LoadingSpinner from './LoadingSpinner.vue'

const props = defineProps({
  title: { type: String, default: '' },
  wide: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const visible = ref(false)

function close() { emit('close') }
function onOverlayClick(e) { if (e.target === e.currentTarget) close() }
function onKeydown(e) { if (e.key === 'Escape') close() }

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  document.body.style.overflow = 'hidden'
  requestAnimationFrame(() => { visible.value = true })
})
onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal" appear>
      <div v-if="visible" class="popup-overlay" @click="onOverlayClick"
        role="dialog" aria-modal="true" :aria-label="title">
        <div class="popup-window" :class="{ 'popup-window-wide': wide }">
          <div class="popup-header">
            <h3 class="popup-title">{{ title }}</h3>
            <button class="popup-close btn-icon" title="Закрыть" @click="close">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="popup-body">
            <slot>
              <LoadingSpinner text="Загрузка…" />
            </slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

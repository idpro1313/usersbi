<script setup>
import { useToast } from '../composables/useToast'

const { toasts, remove } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite">
      <TransitionGroup name="toast">
        <div v-for="t in toasts" :key="t.id"
          class="toast-item" :class="'toast-' + t.type"
          @click="remove(t.id)">
          <span class="toast-msg">{{ t.message }}</span>
          <button class="toast-close" aria-label="Закрыть">&times;</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style>
.toast-container {
  position: fixed;
  top: 52px;
  right: 16px;
  z-index: 9500;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
  max-width: 420px;
}

.toast-item {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--radius, 10px);
  font-size: 0.85rem;
  line-height: 1.4;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  color: #fff;
  backdrop-filter: blur(6px);
}

.toast-success { background: var(--success); }
.toast-error   { background: var(--danger); }
.toast-warn    { background: var(--warn); color: #333; }
.toast-info    { background: var(--accent); }

.toast-msg { flex: 1; }

.toast-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 1.2rem;
  cursor: pointer;
  opacity: 0.7;
  padding: 0 2px;
  line-height: 1;
}
.toast-close:hover { opacity: 1; }

.toast-enter-active { transition: all 0.3s ease; }
.toast-leave-active { transition: all 0.25s ease; }
.toast-enter-from { opacity: 0; transform: translateX(80px); }
.toast-leave-to   { opacity: 0; transform: translateX(80px); }
.toast-move { transition: transform 0.25s ease; }
</style>

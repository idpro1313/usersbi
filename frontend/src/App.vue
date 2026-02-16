<script setup>
import NavBar from './components/NavBar.vue'
import ToastContainer from './components/ToastContainer.vue'
</script>

<template>
  <div class="layout">
    <NavBar />
    <router-view v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <component :is="Component" />
      </Transition>
    </router-view>
    <ToastContainer />
  </div>
</template>

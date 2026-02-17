<script setup>
import NavBar from './components/NavBar.vue'
import ToastContainer from './components/ToastContainer.vue'
</script>

<template>
  <div class="layout">
    <NavBar />
    <router-view v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <div :key="$route.path" class="page-wrap">
          <component :is="Component" />
        </div>
      </Transition>
    </router-view>
    <ToastContainer />
  </div>
</template>

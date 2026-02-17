<script setup>
import { useRoute } from 'vue-router'
import NavBar from './components/NavBar.vue'
import ToastContainer from './components/ToastContainer.vue'

const route = useRoute()
</script>

<template>
  <div :class="route.meta?.hideNav ? 'layout-full' : 'layout'">
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

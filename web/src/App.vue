<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AuthLayout from './layouts/AuthLayout.vue'
import MainLayout from './layouts/MainLayout.vue'
import ToastNotification from './components/ToastNotification.vue'

const route = useRoute()
const layout = computed(() => {
  return route.meta.layout === 'auth' ? AuthLayout : MainLayout
})
</script>

<template>
  <component :is="layout">
    <router-view v-slot="{ Component, route: currentRoute }">
      <transition name="route" mode="out-in">
        <component :is="Component" :key="currentRoute.path" />
      </transition>
    </router-view>
  </component>
  <ToastNotification />
</template>

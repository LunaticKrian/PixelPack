import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/Login.vue'),
      meta: { layout: 'auth', guest: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/Register.vue'),
      meta: { layout: 'auth', guest: true },
    },
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/Dashboard.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/world-map',
      name: 'world-map',
      component: () => import('../views/WorldMap.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/items',
      name: 'items',
      component: () => import('../views/ItemList.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/items/new',
      name: 'item-new',
      component: () => import('../views/ItemForm.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/items/:id',
      name: 'item-detail',
      component: () => import('../views/ItemDetail.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/items/:id/edit',
      name: 'item-edit',
      component: () => import('../views/ItemForm.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/categories',
      name: 'categories',
      component: () => import('../views/Categories.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/tags',
      name: 'tags',
      component: () => import('../views/Tags.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/stats',
      name: 'stats',
      component: () => import('../views/Stats.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/Settings.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/quests',
      name: 'quests',
      component: () => import('../views/Quests.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/character/create',
      name: 'character-create',
      component: () => import('../views/CharacterCreation.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/blog',
      name: 'blog',
      component: () => import('../views/BlogList.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/blog/new',
      name: 'blog-new',
      component: () => import('../views/BlogEditor.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/blog/:id',
      name: 'blog-detail',
      component: () => import('../views/BlogDetail.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/blog/:id/edit',
      name: 'blog-edit',
      component: () => import('../views/BlogEditor.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/share/:token',
      name: 'blog-share',
      component: () => import('../views/BlogShare.vue'),
      meta: { guest: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (!auth.user && !auth.loading) {
    await auth.initialize()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.guest && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }

  // Redirect to character creation if profile not completed
  if (auth.isAuthenticated && auth.user && !auth.user.profile_completed && to.name !== 'character-create') {
    return { name: 'character-create' }
  }
})

export default router

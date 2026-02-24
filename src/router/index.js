import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import DrawBoundaryView from '../views/DrawBoundaryView.vue'
import ZonesView from '../views/ZonesView.vue'
import FinalizeView from '../views/FinalizeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/draw-boundary',
      name: 'draw-boundary',
      component: DrawBoundaryView
    },
    {
      path: '/zones',
      name: 'zones',
      component: ZonesView
    },
    {
      path: '/finalize',
      name: 'finalize',
      component: FinalizeView
    }
  ]
})

export default router

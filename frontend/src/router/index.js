import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

export default createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/', component: HomeView },
    { path: '/profile', component: () => import('../views/ProfileView.vue') },
    { path: '/diet', component: () => import('../views/DietView.vue') },
    { path: '/exercise', component: () => import('../views/ExerciseView.vue') },
    { path: '/sleep', component: () => import('../views/SleepView.vue') },
    { path: '/cycle', component: () => import('../views/CycleView.vue') },
    { path: '/:pathMatch(.*)*', component: () => import('../views/NotFoundView.vue') },
  ],
})

<script setup>
import AppIcon from './components/AppIcon.vue'
import { modules } from './data/modules'
</script>

<template>
  <div class="app-layout">
    <a class="skip-link" href="#main-content">跳转到主要内容</a>
    <aside class="sidebar">
      <RouterLink class="brand" to="/" aria-label="健康管理首页">
        <span class="brand-icon"><AppIcon /></span>
        <span><strong>健康管理</strong><small>HEALTH JOURNAL</small></span>
      </RouterLink>
      <p class="nav-label">我的健康空间</p>
      <nav aria-label="主导航">
        <RouterLink class="nav-item" to="/"><AppIcon name="home" /><span>总览</span></RouterLink>
        <RouterLink v-for="module in modules" :key="module.code" class="nav-item" :to="module.route">
          <AppIcon :name="module.icon" /><span>{{ module.name }}</span>
        </RouterLink>
      </nav>
      <div class="sidebar-note"><span class="small-dot"></span>一点一滴，记录健康日常。<small>本地运行 · v0.1.0</small></div>
    </aside>
    <div class="workspace">
      <header class="topbar"><span>个人健康管理系统</span><span class="version-badge">v0.1 初始预览</span></header>
      <main id="main-content" tabindex="-1"><RouterView /></main>
      <footer>HEALTH JOURNAL <span>用记录，连接每一天。</span></footer>
    </div>
  </div>
</template>

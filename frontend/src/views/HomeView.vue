<script setup>
import { onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import { modules } from '../data/modules'
import { getHealth } from '../api/client'

const state = ref('checking')
const checkedAt = ref('')
async function refreshHealth() {
  state.value = 'checking'
  try {
    await getHealth()
    state.value = 'online'
  } catch {
    state.value = 'offline'
  }
  checkedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
}
onMounted(refreshHealth)
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">YOUR DAILY WELLBEING</p><h1>健康，从了解自己开始。</h1><p>在一个地方，照顾生活的每个侧面。</p></div><span class="outline-badge">项目初始版本</span></div>
  <section class="welcome-panel" aria-label="项目介绍">
    <div><span class="hero-label">记录日常 · 看见变化</span><h2>让健康管理，<br />成为生活的小习惯。</h2><p>饮食、运动、睡眠与身体变化，<br />从每一条简单的记录开始。</p><RouterLink to="/profile" class="button light">了解个人档案<AppIcon name="arrow" /></RouterLink></div>
    <div class="hero-art" aria-hidden="true"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="heart-core"><AppIcon /></div><span class="floating-icon leaf"><AppIcon name="diet" /></span><span class="floating-icon moon"><AppIcon name="sleep" /></span><span class="floating-label">A LITTLE BETTER, EVERY DAY</span></div>
  </section>
  <div class="section-heading"><div><h2>五个模块，一份完整的关照</h2><p>模块入口已就绪，业务功能将在后续版本接入。</p></div><span class="section-count">01 — 05</span></div>
  <section class="module-grid" aria-label="健康模块">
    <RouterLink v-for="(module, index) in modules" :key="module.code" :to="module.route" class="module-card" :class="module.color">
      <div class="card-top"><span class="module-icon"><AppIcon :name="module.icon" /></span><span class="card-number">0{{ index + 1 }}</span></div>
      <h3>{{ module.name }}</h3><p>{{ module.description }}</p>
      <div class="card-bottom"><span>查看模块</span><AppIcon name="arrow" /></div>
    </RouterLink>
  </section>
  <section class="status-panel" aria-label="系统连接状态">
    <div class="status-copy" role="status" aria-live="polite"><span class="status-dot" :class="state"></span><div><h3>{{ state === 'online' ? '服务连接正常' : state === 'checking' ? '正在检查服务连接…' : '暂未连接到后端' }}</h3><p>{{ state === 'online' ? '后端与数据库已就绪，可以开始模块开发。' : state === 'checking' ? '正在检查后端与数据库状态。' : '请先按 README 启动后端，然后重新检查。' }}</p></div></div>
    <div class="status-actions"><span v-if="checkedAt">检查于 {{ checkedAt }}</span><button class="button secondary" :disabled="state === 'checking'" @click="refreshHealth">重新检查</button></div>
  </section>
  <p class="preview-note">当前为项目骨架预览；尚未开放健康数据的录入与分析。</p>
</template>

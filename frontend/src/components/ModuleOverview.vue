<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import { modules } from '../data/modules'

const props = defineProps({ code: { type: String, required: true } })
const module = computed(() => modules.find((item) => item.code === props.code))
</script>

<template>
  <div v-if="module" class="module-overview" :class="module.color">
    <RouterLink class="back-link" to="/">← 返回总览</RouterLink>
    <div class="page-heading"><div><p class="eyebrow">{{ module.english }}</p><h1>{{ module.name }}</h1><p>{{ module.description }}</p></div><span class="outline-badge">{{ module.owner }} 负责</span></div>
    <section class="module-intro"><span class="module-icon large"><AppIcon :name="module.icon" /></span><div><h2>下一步，让记录发生。</h2><p>{{ module.detail }}</p></div></section>
    <div class="section-heading"><div><h2>核心功能规划</h2><p>以下功能将在后续业务版本实现。</p></div></div>
    <section class="feature-list" aria-label="待开发功能"><article v-for="(feature, index) in module.features" :key="feature"><span class="feature-number">0{{ index + 1 }}</span><h3>{{ feature }}</h3><span class="planned-badge">待开发</span></article></section>
    <section class="empty-state"><div class="empty-icon"><AppIcon :name="module.icon" /></div><h2>模块入口已准备好</h2><p>{{ module.next }}</p><p>当前版本暂不支持录入数据。</p><RouterLink class="button primary" to="/">返回总览<AppIcon name="arrow" /></RouterLink></section>
  </div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { DIET_DEMO_CONTEXT } from './demoContext.js'
import { recipeSource } from './recipeSource.js'
const props = defineProps({ recipe: { type: Object, required: true } })
const demo = inject(DIET_DEMO_CONTEXT, null)
const source = computed(() => recipeSource(props.recipe, demo?.value))
</script>
<template><div class="recipe-source">
  <p>{{ source.label }}</p>
  <p v-if="source.review">{{ source.review }}</p><p>{{ source.trial }}</p>
  <p v-if="source.description">{{ source.description }}</p>
  <p>营养信息沿用食谱已保存的资料；按食材计算的数值为估算，不代表成品实测或过敏安全证明。</p>
  <a v-if="source.href" :href="source.href" target="_blank" rel="noopener noreferrer">查看配方来源 ↗</a>
  <details><summary>开发调试信息（原始来源）</summary><pre>{{ recipe.source_note || '未填写' }}</pre><p>{{ recipe.source_url }}</p></details>
</div></template>
<style scoped>.recipe-source{font-size:12px;line-height:1.7;color:#64796d;margin:12px 0}.recipe-source p{margin:6px 0}.recipe-source a{color:#246b58}.recipe-source details{margin-top:12px}.recipe-source pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}</style>

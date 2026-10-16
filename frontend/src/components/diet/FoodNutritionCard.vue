<script setup>
import {dateTimeText} from './displayTime.js'
import { computed, inject } from 'vue'
import { DIET_DEMO_CONTEXT } from './demoContext.js'
import { foodSource, nutrientDisplay, sourceLabels } from './foodPresentation.js'

const props = defineProps({ food: { type: Object, required: true }, category: { type: String, default: '未分类' }, timeZone: { type: String, required: true }, busy: Boolean })
defineEmits(['edit', 'archive'])
const demo = inject(DIET_DEMO_CONTEXT, null)
const source = computed(() => foodSource(props.food, demo?.value))
const nutrients = computed(() => [
  ['calories_per_100g', '热量', 'kcal', '热'], ['protein_g_per_100g', '蛋白质', 'g', '蛋'],
  ['fat_g_per_100g', '脂肪', 'g', '脂'], ['carbohydrate_g_per_100g', '碳水化合物', 'g', '碳'],
].map(([key, label, unit, icon]) => ({ key, label, unit, icon, ...nutrientDisplay(props.food[key]) })))
const updated = computed(() => dateTimeText(props.food.updated_at,props.timeZone))
</script>

<template>
  <article class="food-card">
    <header class="food-title"><h3>{{ food.name }}</h3><span class="badge" :class="{ example: food.is_example }">{{ sourceLabels[food.source_type] || '来源未填写' }}</span></header>
    <p class="category">{{ category }}</p>
    <p class="nutrition-caption">每100g可食部分营养含量</p>
    <dl class="nutrients">
      <div v-for="item in nutrients" :key="item.key" class="nutrient" :class="{ unknown: !item.known }">
        <dt><span class="nutrient-icon" aria-hidden="true">{{ item.icon }}</span>{{ item.label }}</dt>
        <dd>{{ item.text }}<small v-if="item.known">{{ item.unit }}</small></dd>
      </div>
    </dl>
    <p v-if="food.is_example" class="example-note">示例数据，仅用于演示，不代表真实食物营养值。</p>
    <div class="source-info">
      <p class="source-label">{{ source.label }}</p>
      <p v-if="source.review" class="review-note">{{ source.review }}</p>
      <a v-if="source.href" :href="source.href" target="_blank" rel="noopener noreferrer" class="source-link" :aria-label="`查看来源：${food.name}`">查看来源 <span aria-hidden="true">↗</span></a>
    </div>
    <div class="card-footer"><small>更新于 {{ updated }}</small><div class="actions"><button class="button secondary" :disabled="busy" :aria-label="`编辑食物 ${food.name}`" @click="$emit('edit', food)">编辑</button><button class="button danger" :disabled="busy" :aria-label="`归档食物 ${food.name}`" @click="$emit('archive', food)">归档</button></div></div>
  </article>
</template>

<style scoped>
.food-card { display:flex; flex-direction:column; min-width:0; padding:24px; background:#fff; border:1px solid #dde8e1; border-radius:18px; box-shadow:0 4px 18px #254b3505; overflow-wrap:anywhere; }
.food-title { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }.food-title h3 { min-width:0; margin:0; font-size:18px; line-height:1.5; color:#234c40; }.badge { flex-shrink:0; margin-top:3px; padding:4px 8px; border-radius:6px; font-size:11px; background:#edf5ef; color:#48705a; }
.category { margin:7px 0 20px; font-size:12px; color:#657c6f; }.nutrition-caption { margin:0 0 12px; color:#596f63; font-size:12px; letter-spacing:.02em; }.nutrients { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin:0 0 20px; }.nutrient { min-width:0; padding:14px; border:1px solid #e8eee9; border-radius:12px; background:#f5f8f5; }.nutrient dt { display:flex; align-items:center; gap:7px; font-size:12px; color:#607769; }.nutrient-icon { display:inline-grid; place-items:center; width:22px; height:22px; flex-shrink:0; border-radius:7px; background:#e6efe8; color:#40745b; font-size:11px; }.nutrient dd { display:flex; flex-wrap:wrap; align-items:baseline; gap:5px; margin:9px 0 0; color:#246451; font-size:24px; font-weight:600; line-height:1.3; font-variant-numeric:tabular-nums; }.nutrient small { color:#698373; font-size:12px; font-weight:400; }.unknown dd { color:#7c857f; font-size:20px; }
.source-info { margin-top:auto; padding-top:16px; border-top:1px solid #eaf0eb; }.source-label { margin:0; font-size:12px; line-height:1.6; color:#486353; }.review-note { margin:7px 0 0; color:#8a642a; font-size:11px; line-height:1.6; }.source-link { display:inline-flex; align-items:center; gap:6px; margin-top:10px; padding:6px 10px; border:1px solid #dce8df; border-radius:7px; color:#2a6c53; font-size:12px; text-decoration:none; }.source-link:hover { background:#edf5ef; }.source-link:focus-visible { outline:2px solid #246451; outline-offset:3px; }.example-note { color:#926222; background:#fff5e7; padding:9px; border-radius:8px; font-size:12px; }.badge.example { color:#926222; background:#fff5e7; }.card-footer { display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; margin-top:20px; }.card-footer>small { color:#78877e; font-size:10px; }.actions { display:flex; gap:8px; }.danger { background:#fff1ed; border-color:#ecd1c8; color:#a04431; }
@media(max-width:600px) { .food-card { padding:18px; border-radius:14px; }.food-title { flex-wrap:wrap; gap:5px 10px; }.food-title h3 { flex:1 1 170px; font-size:17px; }.nutrient { padding:12px; }.nutrient dd { font-size:22px; } }
</style>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { listCatalog, referenceFood, copyPublicRecipe } from '../../api/catalog.js'
import FoodLibraryPanel from './FoodLibraryPanel.vue'
import RecipeLibraryPanel from './RecipeLibraryPanel.vue'
import { preparationText } from './recipeUI.js'
const props = defineProps({ kind: { type: String, default: 'foods' }, timeZone: { type: String, default: 'Asia/Shanghai' } })
const privateMode = ref(false), items = ref([]), categories = ref([]), query = ref(''), category = ref(''), loading = ref(false), busy = ref(false), error = ref(''), message = ref('')
const isFood = computed(() => props.kind === 'foods')
const nutrientFields = [['calories_per_100g','热量','kcal'],['protein_g_per_100g','蛋白质','g'],['fat_g_per_100g','脂肪','g'],['carbohydrate_g_per_100g','碳水','g']]
async function load() {
  if (loading.value) return
  loading.value = true; error.value = ''
  try { const [a,b] = await Promise.all([listCatalog(props.kind, { q: query.value, category: category.value }), listCatalog(isFood.value ? 'food-categories' : 'recipe-categories')]); items.value = a.items; categories.value = b.items }
  catch(e) { items.value = []; error.value = e.message } finally { loading.value = false }
}
async function use(item) {
  busy.value = true; error.value = ''; message.value = ''
  try {
    if (isFood.value) { await referenceFood(item.food_key); message.value = '已加入我的可用食品，可用于饮食记录、库存及禁忌。未创建摄入记录。' }
    else { await copyPublicRecipe(item.recipe_key); message.value = '已另存为我的食谱，公共原件保持不变。修改后的副本需重新核对食材与营养信息。' }
  } catch(e) { error.value = e.message } finally { busy.value = false }
}
onMounted(load)
</script>
<template><section class="catalog-panel">
  <div class="catalog-heading"><h2>{{ isFood ? '食物营养库' : '食谱库' }}</h2><div class="catalog-actions"><button class="button" :class="privateMode?'secondary':'primary'" :aria-pressed="!privateMode" @click="privateMode=false">公共{{ isFood ? '食品' : '食谱' }}</button><button class="button" :class="privateMode?'primary':'secondary'" :aria-pressed="privateMode" @click="privateMode=true">我的{{ isFood ? '食品' : '食谱' }}</button></div></div>
  <template v-if="!privateMode">
    <p class="catalog-intro">公共参考数据 · 无需建档即可浏览。个人记录、库存与推荐需登录并建立档案。</p>
    <details class="catalog-notice"><summary>数据来源与使用说明</summary><p>134 种 USDA 食物已完成来源技术核验；12 道菜谱为团队自编、AI 辅助，未经实际试做。营养为食材投料估算，不等于成品实测；过敏原及加工配料未全面核验。数据仅供参考，不构成医学建议或过敏安全认证。</p></details>
    <form class="catalog-filters" @submit.prevent="load"><label>搜索<input v-model="query" :placeholder="isFood?'中文、英文或 FDC ID':'菜谱名称'"></label><label>分类<select v-model="category"><option value="">全部分类</option><option v-for="c in categories" :key="c.category_key" :value="c.category_key">{{ c.name }}</option></select></label><button class="button primary" :disabled="loading">搜索</button></form>
    <p v-if="loading" role="status">正在读取公共目录…</p><p v-if="error" class="catalog-error" role="alert">{{ error }}</p><p v-if="message" role="status">{{ message }}</p>
    <p v-if="!loading">共 {{ items.length }} 项公共参考数据</p>
    <div class="catalog-grid"><article v-for="item in items" :key="item.food_key || item.recipe_key" class="catalog-card"><span class="catalog-badge">公共参考数据 · 只读</span><h3>{{ item.name }}</h3>
      <template v-if="isFood"><p class="catalog-original">{{ item.original_english_name }}</p><p>FDC ID：{{ item.fdc_id }}</p><p class="catalog-small">每 100g 可食部分</p><dl><div v-for="[key,label,unit] in nutrientFields" :key="key"><dt>{{ label }}</dt><dd>{{ item[key] ?? '未知' }} <small v-if="item[key] != null">{{ unit }}</small></dd></div></dl><a :href="item.source_url" target="_blank" rel="noopener noreferrer">USDA 原始来源 ↗</a></template>
      <template v-else><p>{{ item.description }}</p><p>{{ item.servings }} 份 · {{ preparationText(item.preparation_minutes) }}</p><p>每份估算热量：{{ item.per_serving?.calories_kcal?.total ?? '未知' }} kcal</p><details><summary>查看食材与制作步骤</summary><ul><li v-for="i in item.ingredients" :key="i.food_key">{{ i.food_name_snapshot }} · {{ i.amount_g }} g</li></ul><ol><li v-for="(step,index) in item.steps" :key="index">{{ step }}</li></ol><p class="catalog-small">团队自编、AI 辅助、未经实际试做。{{ item.source_note }}</p></details></template>
      <button class="button secondary catalog-use" :disabled="busy" @click="use(item)">{{ isFood ? '加入我的可用食品' : '另存为我的食谱' }}</button>
    </article></div>
  </template>
  <FoodLibraryPanel v-else-if="isFood" :time-zone="timeZone"/>
  <RecipeLibraryPanel v-else/>
</section></template>
<style scoped>
.catalog-panel{color:#273e36;min-width:0}.catalog-heading,.catalog-actions,.catalog-filters{display:flex;gap:12px;flex-wrap:wrap;align-items:center}.catalog-heading{justify-content:space-between}.catalog-heading h2{font-size:24px}.catalog-intro,.catalog-small{font-size:13px;line-height:1.7;color:#607769}.catalog-notice{padding:12px;background:#edf5ef;border:1px solid #dce8df;border-radius:10px;line-height:1.7}.catalog-notice summary,details summary{cursor:pointer}.catalog-filters{align-items:flex-end;margin:20px 0}.catalog-filters label{display:flex;flex-direction:column;gap:8px;min-width:0}.catalog-filters input,.catalog-filters select{padding:11px;border:1px solid #cddace;border-radius:8px;font:inherit;min-width:0;max-width:100%;box-sizing:border-box}.catalog-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.catalog-card{padding:22px;background:white;border:1px solid #dde8e1;border-radius:16px;display:flex;flex-direction:column;gap:10px;min-width:0;overflow-wrap:anywhere}.catalog-card h3,.catalog-card p{margin:0;line-height:1.7}.catalog-card h3{font-size:18px;color:#234c40}.catalog-badge{font-size:11px;color:#40745b}.catalog-original{font-size:12px;color:#607769}.catalog-card dl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:0}.catalog-card dl div{padding:10px;background:#f5f8f5;border-radius:10px}.catalog-card dt{font-size:12px}.catalog-card dd{margin:8px 0 0;font-size:19px;color:#246451}.catalog-card small{font-size:11px}.catalog-card a{color:#246451;font-size:13px}.catalog-use{margin-top:auto;align-self:flex-start}.catalog-card details{line-height:1.7}.catalog-card li{margin:8px 0}.catalog-error{padding:12px;background:#fff0ec;color:#a04431;border-radius:8px}@media(max-width:1000px){.catalog-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:650px){.catalog-grid{grid-template-columns:1fr}.catalog-card{padding:16px}.catalog-filters label{width:100%}.catalog-heading h2{font-size:22px}.catalog-actions{gap:8px}.catalog-actions .button{padding:10px}}
</style>

<script setup>
import { ref } from 'vue'
import { listCatalog, referenceFood } from '../../api/catalog.js'
const emit = defineEmits(['selected'])
const foods = ref([]), selected = ref(''), query = ref(''), error = ref(''), busy = ref(false), loaded = ref(false)
async function search() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { foods.value = (await listCatalog('foods', { q: query.value })).items; loaded.value = true; selected.value = '' }
  catch (e) { error.value = e.message } finally { busy.value = false }
}
async function choose() {
  if (busy.value || !selected.value) return
  busy.value = true; error.value = ''
  try { emit('selected', await referenceFood(selected.value)); selected.value = '' }
  catch (e) { error.value = e.message } finally { busy.value = false }
}
</script>
<template><details class="public-picker" @toggle="($event.target.open && !loaded && !busy) && search()">
  <summary>从公共食品中选择</summary>
  <p>只在确认选择时建立私人引用，不会新增摄入记录或修改公共食品。需要登录、健康数据授权、个人档案及 006 迁移。</p>
  <div class="picker-row"><input v-model="query" aria-label="搜索公共食品" placeholder="中文、英文或 FDC ID" @keydown.enter.prevent="search"><button type="button" class="button secondary" :disabled="busy" @click="search">搜索</button></div>
  <select v-model="selected" aria-label="公共食品" :disabled="busy"><option value="">请选择公共食品</option><option v-for="f in foods" :key="f.food_key" :value="f.food_key">{{ f.name }} · {{ f.fdc_id }}</option></select>
  <button type="button" class="button secondary" :disabled="busy || !selected" @click="choose">使用此公共食品</button>
  <p v-if="error" role="alert">{{ error }}</p><p v-else-if="loaded && !foods.length">没有匹配的食品。</p>
</details></template>
<style scoped>
.public-picker{padding:12px;border:1px solid #cddace;border-radius:10px;margin:12px 0;min-width:0;color:#315c4c;overflow-wrap:anywhere}.public-picker summary{cursor:pointer}.public-picker p{font-size:12px;line-height:1.7}.picker-row{display:flex;gap:8px;flex-wrap:wrap}.public-picker input,.public-picker select{width:100%;min-width:0;padding:10px;border:1px solid #cddace;border-radius:7px;box-sizing:border-box;margin:8px 0}.picker-row input{flex:1 1 140px}
</style>

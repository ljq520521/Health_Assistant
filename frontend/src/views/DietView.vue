<script setup>
import { nextTick, onMounted, ref, provide, readonly } from 'vue'
import { DIET_DEMO_CONTEXT } from '../components/diet/demoContext.js'
import { onBeforeRouteLeave } from 'vue-router'
import { modules } from '../data/modules'
import WaterPanel from '../components/diet/WaterPanel.vue'
import RecipeWorkspace from '../components/diet/RecipeWorkspace.vue'
import DietReportPanel from '../components/diet/DietReportPanel.vue'
import WaterReminderHost from '../components/diet/WaterReminderHost.vue'
import DietRecordsPanel from '../components/diet/DietRecordsPanel.vue'
import NutritionAnalysisPanel from '../components/diet/NutritionAnalysisPanel.vue'
import FoodLibraryPanel from '../components/diet/CatalogPanel.vue'
import DietUsageGuide from '../components/diet/DietUsageGuide.vue'
import { getDietConfig } from '../api/foodLibrary.js'

const module = modules.find((item) => item.code === 'diet')
const active = ref('library'), openedLibrary = ref(true), timeZone = ref(''), error = ref(''), loading = ref(false)
const waterPanel = ref(null), reminderHost = ref(null)
const demo = ref(null)
provide(DIET_DEMO_CONTEXT, readonly(demo))

async function recordWater() {
  active.value = 'water'
  await nextTick()
  waterPanel.value?.open()
}

async function select(tab) {
  if (tab !== active.value && active.value === 'water' && (await waterPanel.value?.confirmLeave()) === false) return
  active.value = tab
  if (tab === 'library') openedLibrary.value = true
}

async function loadConfig() {
  loading.value = true
  error.value = ''
  try {
    const config = await getDietConfig()
    timeZone.value = config.time_zone
    demo.value = config.demo || null
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onBeforeRouteLeave(async () => active.value !== 'water' || (await waterPanel.value?.confirmLeave()) !== false)
onMounted(loadConfig)
</script>

<template>
  <section v-if="module" class="module-overview" :class="module.color">
    <RouterLink class="back-link" to="/">← 返回总览</RouterLink>
    <div class="page-heading diet-heading">
      <div class="diet-heading-copy">
        <p class="eyebrow">{{ module.english }}</p>
        <h1>{{ module.name }}</h1>
        <p>{{ module.description }}</p>
      </div>
      <DietUsageGuide @select="select" />
    </div>
    <div class="diet-tabs" role="group" aria-label="饮食功能分区">
      <button class="button" :class="active === 'records' ? 'primary' : 'secondary'" :aria-pressed="active === 'records'" @click="select('records')">饮食记录</button>
      <button class="button" :class="active === 'library' ? 'primary' : 'secondary'" :aria-pressed="active === 'library'" @click="select('library')">食物营养库</button>
      <button class="button" :class="active === 'analysis' ? 'primary' : 'secondary'" :aria-pressed="active === 'analysis'" @click="select('analysis')">营养摄入分析</button>
      <button class="button" :class="active === 'water' ? 'primary' : 'secondary'" :aria-pressed="active === 'water'" @click="select('water')">饮水管理</button>
      <button class="button" :class="active === 'recipes' ? 'primary' : 'secondary'" :aria-pressed="active === 'recipes'" @click="select('recipes')">食谱推荐</button>
      <button class="button" :class="active === 'reports' ? 'primary' : 'secondary'" :aria-pressed="active === 'reports'" @click="select('reports')">饮食报告</button>
    </div>
    <p v-if="loading" role="status">正在加载…</p>
    <div v-else-if="error" class="diet-error" role="alert">{{ error }} <button class="button secondary" @click="loadConfig">重试</button></div>
    <template v-else-if="timeZone">
      <WaterReminderHost ref="reminderHost" :time-zone="timeZone" @record="recordWater" />
      <RecipeWorkspace v-if="active === 'recipes'" :time-zone="timeZone" />
      <DietReportPanel v-if="active === 'reports'" :time-zone="timeZone" :demo="demo" />
      <WaterPanel v-if="active === 'water'" ref="waterPanel" :time-zone="timeZone" @changed="reminderHost?.check()" />
      <NutritionAnalysisPanel v-if="active === 'analysis'" :time-zone="timeZone" />
      <DietRecordsPanel v-if="active === 'records'" :time-zone="timeZone" />
      <FoodLibraryPanel v-if="openedLibrary" v-show="active === 'library'" :time-zone="timeZone" />
    </template>
  </section>
</template>

<style scoped>
/* The shared shell has min-width:320px; desktop scrollbars reduce a 320px
   test viewport's content width. Relax that minimum only on the diet page. */
:global(body:has(.diet-heading)) { min-width: 0; }
.diet-heading { margin-bottom: 20px; }
.diet-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; padding-bottom: 14px; border-bottom: 1px solid #dfe7db; }
.diet-error { padding: 16px; background: #fff0ec; color: #983b2d; border-radius: 8px; }
.diet-heading-copy { min-width:0; flex:1; }
@media(max-width:600px) {
  .diet-heading { align-items:flex-start; flex-wrap:wrap; gap:12px; }
  .diet-heading-copy { flex-basis:100%; }
}
</style>

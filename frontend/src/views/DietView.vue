<script setup>
import { nextTick, onMounted, ref, provide, readonly } from 'vue'
import { DIET_DEMO_CONTEXT, isDevelopmentDemo, isCourseApproved, demoApprovalText } from '../components/diet/demoContext.js'
import { onBeforeRouteLeave } from 'vue-router'
import { modules } from '../data/modules'
import WaterPanel from '../components/diet/WaterPanel.vue'
import RecipeWorkspace from '../components/diet/RecipeWorkspace.vue'
import DietReportPanel from '../components/diet/DietReportPanel.vue'
import WaterReminderHost from '../components/diet/WaterReminderHost.vue'
import DietRecordsPanel from '../components/diet/DietRecordsPanel.vue'
import NutritionAnalysisPanel from '../components/diet/NutritionAnalysisPanel.vue'
import FoodLibraryPanel from '../components/diet/FoodLibraryPanel.vue'
import { getDietConfig } from '../api/foodLibrary.js'

const module = modules.find((item) => item.code === 'diet')
const active = ref('records'), openedLibrary = ref(false), timeZone = ref(''), error = ref(''), loading = ref(false)
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
        <div class="diet-title-row"><h1>{{ module.name }}</h1><span v-if="isDevelopmentDemo(demo)" class="diet-demo-badge">演示模式</span></div>
        <p>{{ module.description }}</p>
        <div v-if="isDevelopmentDemo(demo)" class="diet-data-info">
          <p class="diet-approval" role="status">{{ demoApprovalText(demo) }}</p>
          <details class="diet-data-details">
            <summary>数据说明</summary>
            <div class="diet-data-content">
              <ul>
                <li>当前为开发演示环境，使用非真实用户和非真实健康记录。</li>
                <template v-if="isCourseApproved(demo)">
                  <li>134种USDA食物已完成来源技术核验。</li>
                  <li>12道菜谱已批准用于课程演示，为团队自编、AI辅助草案，仍未经实际试做。</li>
                </template>
                <li v-else>{{ demo.notice }}；菜谱为团队自编、AI辅助草案，{{ demo.recipe_trial_status }}。</li>
                <li>营养为食材投料估算，不等于成品实测。</li>
                <li>过敏原及加工配料未完成全面安全核验。</li>
              </ul>
              <p>仅用于Health_Assistant软件工程课程设计演示，不代表医学或正式生产用途批准。新增或修改内容不自动获得批准。</p>
              <details class="diet-dev-details"><summary>开发详情</summary><p>当前演示数据库路径</p><code>{{ demo.database_path }}</code></details>
            </div>
          </details>
        </div>
      </div>
      <span class="outline-badge">{{ module.owner }} 负责</span>
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
      <DietRecordsPanel v-show="active === 'records'" :time-zone="timeZone" />
      <FoodLibraryPanel v-if="openedLibrary" v-show="active === 'library'" :time-zone="timeZone" />
    </template>
  </section>
</template>

<style scoped>
.diet-tabs { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 26px; padding-bottom: 18px; border-bottom: 1px solid #dfe7db; }
.diet-error { padding: 16px; background: #fff0ec; color: #983b2d; border-radius: 8px; }
.diet-heading-copy { min-width:0; flex:1; }
.diet-title-row { display:flex; align-items:center; flex-wrap:wrap; gap:10px 14px; }
.diet-demo-badge { padding:4px 10px; border:1px solid #cbded2; border-radius:999px; background:#edf5ef; color:#39735b; font-size:12px; line-height:1.5; white-space:nowrap; }
.diet-data-info { margin-top:12px; color:#526e5f; font-size:13px; line-height:1.7; }
.diet-data-info .diet-approval { margin:0; color:#39735b; font-size:13px; }
.diet-data-details { margin-top:2px; }
.diet-data-info summary { width:fit-content; padding:4px 0; cursor:pointer; color:#39735b; }
.diet-data-info summary:hover { color:#214f40; }
.diet-data-info summary:focus-visible { outline:2px solid #39735b; outline-offset:3px; border-radius:3px; }
.diet-data-content { margin-top:6px; padding:12px 16px; border-left:2px solid #cbded2; background:#f2f7f3; border-radius:0 8px 8px 0; overflow-wrap:anywhere; }
.diet-data-content ul { margin:0; padding-left:18px; }
.diet-data-content li + li { margin-top:4px; }
.diet-data-content p { margin:8px 0 0; font-size:12px; line-height:1.7; }
.diet-dev-details { margin-top:8px; padding-top:6px; border-top:1px solid #dbe7df; }
.diet-dev-details code { display:block; margin-top:6px; white-space:normal; overflow-wrap:anywhere; font-size:12px; }
@media(max-width:600px) {
  .diet-heading { align-items:flex-start; flex-wrap:wrap; gap:12px; }
  .diet-heading-copy { flex-basis:100%; }
  .diet-title-row { gap:8px 10px; }
  .diet-data-info summary { padding:8px 0; }
  .diet-data-content { padding:10px 12px; }
}
</style>

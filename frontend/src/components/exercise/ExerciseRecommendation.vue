<script setup>
import { computed, onMounted, ref } from 'vue'
import { getExerciseRecommendation } from '../../api/exercise.js'

const data = ref(null)
const loading = ref(false)
const error = ref('')
const hidden = ref(false)

const progress = computed(() => Math.min(100, Math.max(0, data.value?.weekly_progress_percent ?? 0)))

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await getExerciseRecommendation()
    hidden.value = false
  } catch (err) {
    if (err.status === 409) {
      hidden.value = true
      data.value = null
    } else {
      error.value = err.message
    }
  } finally {
    loading.value = false
  }
}

defineExpose({ reload: load })
onMounted(load)
</script>

<template>
  <section v-if="!hidden" class="panel recommendation" aria-labelledby="exercise-recommendation-title">
    <div class="rec-head">
      <div>
        <h2 id="exercise-recommendation-title">个性化运动推荐</h2>
        <p>根据健康档案、健康目标和最近 7 天记录生成；仅供日常参考，不替代医疗建议。</p>
      </div>
      <span v-if="data" class="rec-focus">{{ data.focus_label }}</span>
    </div>

    <p v-if="loading" class="rec-status" role="status">正在根据档案生成推荐…</p>
    <p v-else-if="error" class="rec-error" role="alert">
      {{ error }}
      <button class="button secondary" @click="load">重新生成</button>
    </p>

    <template v-else-if="data">
      <p class="rec-summary">{{ data.summary }}</p>

      <div class="rec-progress">
        <div
          class="rec-bar"
          role="progressbar"
          :aria-valuenow="progress"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`本周运动目标完成 ${progress}%`"
        >
          <span :style="{ width: `${progress}%` }" />
        </div>
        <p>
          本周已完成 <strong>{{ data.weekly_done_minutes }}</strong> / {{ data.weekly_target_minutes }} 分钟 ·
          {{ data.days_active_last_week }} 天有运动
          <span v-if="data.bmi" class="rec-bmi">· BMI {{ data.bmi }}（{{ data.bmi_label }}）</span>
        </p>
      </div>

      <ul class="rec-list">
        <li v-for="item in data.suggestions" :key="item.title">
          <span class="rec-tag">{{ item.tag }}</span>
          <div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
          </div>
        </li>
      </ul>

      <div v-if="data.safety_notes.length" class="rec-safety">
        <strong>安全提示</strong>
        <ul>
          <li v-for="note in data.safety_notes" :key="note">{{ note }}</li>
        </ul>
      </div>

      <details class="rec-evidence">
        <summary>推荐依据</summary>
        <ul>
          <li v-for="line in data.evidence" :key="line">{{ line }}</li>
        </ul>
      </details>
    </template>
  </section>
</template>

<style scoped>
.recommendation { margin-bottom: 26px; }
.rec-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.rec-head h2 { font-size: 17px; font-weight: 600; }
.rec-head p { margin-top: 6px; font-size: 12px; color: #7a8779; }
.rec-focus {
  flex-shrink: 0;
  padding: 4px 12px;
  border-radius: 999px;
  background: var(--tint, #eaf1f8);
  color: var(--accent, #6587ab);
  font-size: 12px;
  line-height: 1.8;
  white-space: nowrap;
}
.rec-status { margin-top: 16px; font-size: 13px; color: #7a8779; }
.rec-error { margin-top: 16px; padding: 11px 14px; border-radius: 8px; background: #fff0ec; color: #983b2d; font-size: 13px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.rec-summary { margin-top: 16px; font-size: 13px; line-height: 1.8; color: #41544a; }
.rec-progress { margin-top: 14px; }
.rec-bar { height: 8px; border-radius: 999px; background: #edf1ec; overflow: hidden; }
.rec-bar > span { display: block; height: 100%; border-radius: 999px; background: var(--accent, #6587ab); transition: width .3s ease; }
.rec-progress p { margin-top: 8px; font-size: 12px; color: #6f7d70; }
.rec-progress strong { color: #33473d; }
.rec-bmi { color: #7a8779; }
.rec-list { list-style: none; margin: 18px 0 0; padding: 0; display: grid; gap: 12px; }
.rec-list li { display: flex; gap: 12px; align-items: flex-start; padding: 13px 14px; background: #f7faf5; border: 1px solid #e8eee4; border-radius: 10px; }
.rec-tag { flex-shrink: 0; padding: 2px 9px; border-radius: 5px; background: #fff; border: 1px solid #dde6d9; color: #5c6f58; font-size: 11px; line-height: 1.9; }
.rec-list strong { display: block; font-size: 13px; font-weight: 600; }
.rec-list p { margin-top: 4px; font-size: 12.5px; line-height: 1.75; color: #6f7d70; }
.rec-safety { margin-top: 16px; padding: 13px 15px; border-left: 3px solid #c98d64; background: #fdf5ee; border-radius: 8px; }
.rec-safety strong { font-size: 12.5px; color: #8a5a34; }
.rec-safety ul { margin: 6px 0 0; padding-left: 18px; }
.rec-safety li { font-size: 12.5px; line-height: 1.75; color: #7b5f45; }
.rec-evidence { margin-top: 14px; font-size: 12px; color: #7a8779; }
.rec-evidence summary { width: fit-content; cursor: pointer; padding: 4px 0; color: #61806f; }
.rec-evidence summary:hover { color: #33574a; }
.rec-evidence ul { margin: 6px 0 0; padding: 10px 14px 10px 30px; border-left: 2px solid #e3ebdf; background: #f7faf5; border-radius: 0 8px 8px 0; }
.rec-evidence li + li { margin-top: 4px; }
@media (max-width: 700px) {
  .rec-head { flex-direction: column; }
  .rec-list li { flex-direction: column; gap: 6px; }
}
@media (prefers-reduced-motion: reduce) { .rec-bar > span { transition: none; } }
</style>

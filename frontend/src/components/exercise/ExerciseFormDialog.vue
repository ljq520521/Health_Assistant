<script setup>
import { nextTick, reactive, ref } from 'vue'
import { createExercise, updateExercise } from '../../api/exercise.js'
import {
  EXERCISE_SUGGESTIONS,
  INTENSITY_OPTIONS,
  MAX_DURATION_MINUTES,
  MAX_NOTES_LENGTH,
  todayInZone,
  validDate,
} from './exerciseStats.js'

const props = defineProps({
  timeZone: { type: String, default: 'Asia/Shanghai' },
})
const emit = defineEmits(['saved'])

const dialog = ref(null)
const firstField = ref(null)
const editingId = ref(null)
const busy = ref(false)
const error = ref('')
const profileMissing = ref(false)
let returnFocus = null

const form = reactive({
  record_date: '',
  exercise_type: '',
  duration_minutes: '',
  intensity: 'medium',
  notes: '',
})

function open(record = null) {
  returnFocus = document.activeElement
  editingId.value = record?.id ?? null
  Object.assign(form, {
    record_date: record?.record_date || todayInZone(props.timeZone),
    exercise_type: record?.exercise_type || '',
    duration_minutes: record?.duration_minutes ?? '',
    intensity: record?.intensity || 'medium',
    notes: record?.notes || '',
  })
  error.value = ''
  profileMissing.value = false
  busy.value = false
  dialog.value.showModal()
  nextTick(() => firstField.value?.focus())
}

function close() {
  if (busy.value) return
  dialog.value.close()
  returnFocus?.focus()
}

function onCancel(event) {
  if (busy.value) {
    event.preventDefault()
    return
  }
  returnFocus?.focus()
}

defineExpose({ open, close })

function validate() {
  if (!validDate(form.record_date)) return '请选择合法的运动日期'
  const type = String(form.exercise_type).trim()
  if (type.length < 1 || type.length > 50) return '运动类型应为 1～50 个字符'
  const minutes = Number(form.duration_minutes)
  if (!Number.isInteger(minutes) || minutes < 1 || minutes > MAX_DURATION_MINUTES) {
    return `运动时长需为 1～${MAX_DURATION_MINUTES} 之间的整数分钟`
  }
  if (!INTENSITY_OPTIONS.some((option) => option.value === form.intensity)) return '请选择运动强度'
  if (String(form.notes).length > MAX_NOTES_LENGTH) return `备注不能超过 ${MAX_NOTES_LENGTH} 个字符`
  return ''
}

async function save() {
  error.value = ''
  const problem = validate()
  if (problem) {
    error.value = problem
    return
  }
  const payload = {
    record_date: form.record_date,
    exercise_type: String(form.exercise_type).trim(),
    duration_minutes: Number(form.duration_minutes),
    intensity: form.intensity,
    notes: String(form.notes).trim(),
  }
  busy.value = true
  try {
    if (editingId.value === null) {
      await createExercise(payload)
      emit('saved', '运动记录已添加')
    } else {
      await updateExercise(editingId.value, payload)
      emit('saved', '运动记录已更新')
    }
    dialog.value.close()
    returnFocus?.focus()
  } catch (err) {
    profileMissing.value = err.status === 409
    error.value = profileMissing.value ? '请先建立个人档案，再记录运动。' : err.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <dialog ref="dialog" class="exercise-dialog" aria-labelledby="exercise-form-title" @cancel="onCancel">
    <form novalidate @submit.prevent="save">
      <h2 id="exercise-form-title">{{ editingId === null ? '新增运动记录' : '编辑运动记录' }}</h2>
      <p class="dialog-hint">记录日期、运动类型、时长和主观强度；不会估算热量。</p>
      <fieldset :disabled="busy">
        <div class="form-grid">
          <label>
            <span>运动日期 *</span>
            <input ref="firstField" v-model="form.record_date" type="date" required />
          </label>
          <label>
            <span>运动强度 *</span>
            <select v-model="form.intensity" required>
              <option v-for="option in INTENSITY_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
          <label class="wide">
            <span>运动类型 *</span>
            <input
              v-model="form.exercise_type"
              type="text"
              maxlength="50"
              list="exercise-type-options"
              placeholder="如：快走、跑步、力量训练"
              required
            />
            <datalist id="exercise-type-options">
              <option v-for="item in EXERCISE_SUGGESTIONS" :key="item" :value="item" />
            </datalist>
          </label>
          <label>
            <span>时长（分钟）*</span>
            <input
              v-model="form.duration_minutes"
              type="number"
              min="1"
              :max="MAX_DURATION_MINUTES"
              step="1"
              inputmode="numeric"
              required
            />
          </label>
          <label>
            <span>备注</span>
            <input v-model="form.notes" type="text" :maxlength="MAX_NOTES_LENGTH" placeholder="可选，如：晚饭后快走" />
          </label>
        </div>
      </fieldset>
      <p v-if="error" class="notice failure" role="alert">
        {{ error }}
        <RouterLink v-if="profileMissing" to="/profile" @click="close">前往建立档案</RouterLink>
      </p>
      <div class="dialog-actions">
        <button type="button" class="button secondary" :disabled="busy" @click="close">取消</button>
        <button type="submit" class="button primary" :disabled="busy">
          {{ busy ? '正在保存…' : '保存' }}
        </button>
      </div>
    </form>
  </dialog>
</template>

<style scoped>
.exercise-dialog {
  width: min(540px, calc(100% - 32px));
  max-height: 90vh;
  overflow-y: auto;
  padding: 26px;
  border: 1px solid #dbe5d6;
  border-radius: 14px;
  color: #273e36;
  background: #fff;
}
.exercise-dialog::backdrop { background: #18372b66; }
.exercise-dialog h2 { font-size: 21px; margin-bottom: 8px; }
.dialog-hint { font-size: 12px; color: #7a8779; margin-bottom: 20px; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 17px; }
label { display: flex; flex-direction: column; gap: 7px; font-size: 13px; }
.wide { grid-column: 1 / -1; }
input,
select {
  width: 100%;
  min-width: 0;
  border: 1px solid #cddace;
  border-radius: 7px;
  padding: 10px 12px;
  font: inherit;
  color: #273e36;
  background: #fff;
}
.notice { margin-top: 18px; padding: 11px 14px; border-radius: 8px; font-size: 13px; }
.failure { background: #fff0ec; color: #983b2d; }
.notice a { margin-left: 8px; color: #1f5b49; text-decoration: underline; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 22px; }
@media (max-width: 600px) {
  .form-grid { grid-template-columns: 1fr; }
  .wide { grid-column: auto; }
  .exercise-dialog { padding: 18px; }
}
</style>

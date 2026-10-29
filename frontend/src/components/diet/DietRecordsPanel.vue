<script setup>
import PublicFoodPicker from './PublicFoodPicker.vue'
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { createDiet, deleteDiet, listDiet, updateDiet } from '../../api/diet.js'

import { listFoods } from '../../api/foodLibrary.js'
import { getRecordSummary } from '../../api/nutrition.js'

const props = defineProps({ timeZone: { type: String, required: true } })

const meals = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐' }
const records = ref([]), loading = ref(false), busy = ref(false), error = ref(''), success = ref(''), noProfile = ref(false)
const filters = reactive({ date_from: '', date_to: '' })
const editor = ref(null), confirmation = ref(null), editingId = ref(null), deleting = ref(null), formError = ref('')
const form = reactive({ record_date: '', meal_type: 'breakfast', food_name: '', amount_g: '', calories_kcal: '', notes: '' })
let returnFocus
const daily = ref([]), foods = ref([]), foodLoading = ref(false), foodError = ref(''), original = ref(null)
const mode = ref('manual'), foodId = ref(''), refreshSnapshot = ref(false)
const nutrientFields = [['calories_kcal','热量','kcal','calories_per_100g'],['protein_g','蛋白质','g','protein_g_per_100g'],['fat_g','脂肪','g','fat_g_per_100g'],['carbohydrate_g','碳水化合物','g','carbohydrate_g_per_100g']]
const useSnapshot = computed(() => original.value?.nutrition_mode === 'catalog' && Number(foodId.value) === original.value.food_id && !refreshSnapshot.value)
const selectedFood = computed(() => foods.value.find(food => food.id === Number(foodId.value)))
const preview = computed(() => nutrientFields.map(([key,label,unit,source]) => {
  const per100 = useSnapshot.value ? original.value['snapshot_'+source] : selectedFood.value?.[source]
  const amount = Number(form.amount_g)
  return {key,label,unit,per100, value: per100 == null || !Number.isFinite(amount) || amount <= 0 ? null : per100 * amount / 100}
}))
let loadVersion = 0
const number = value => new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(value)
function validDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const date = new Date(`${value}T00:00:00Z`)
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value && !value.startsWith('0000')
}
function handleError(err, target = error) {
  target.value = err.message
  if (err.code === 'PROFILE_REQUIRED') { noProfile.value = true; records.value = [] }
}
async function load() {
  error.value = ''
  if ((filters.date_from && !validDate(filters.date_from)) || (filters.date_to && !validDate(filters.date_to))) { error.value = '请输入合法日期'; return }
  if (filters.date_from && filters.date_to && filters.date_from > filters.date_to) { error.value = '开始日期不能晚于结束日期'; return }
  const version = ++loadVersion
  loading.value = true
  records.value = []; daily.value = []
  try {
    const [data, summary] = await Promise.all([listDiet({...filters}), getRecordSummary({...filters})])
    if (version !== loadVersion) return
    records.value = data.items; daily.value = summary.items; noProfile.value = false
  } catch (err) { if (version === loadVersion) handleError(err) }
  finally { if (version === loadVersion) loading.value = false }
}
async function resetFilters() { filters.date_from = ''; filters.date_to = ''; await load() }
async function openEditor(record = null) {
  returnFocus = document.activeElement
  editingId.value = record?.id ?? null
  Object.assign(form, record ? { record_date: record.record_date, meal_type: record.meal_type, food_name: record.food_name, amount_g: record.amount_g, calories_kcal: record.calories_kcal ?? '', notes: record.notes } : { record_date: new Intl.DateTimeFormat('en-CA', { timeZone: props.timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()), meal_type: 'breakfast', food_name: '', amount_g: '', calories_kcal: '', notes: '' })
  original.value = record
  mode.value = record?.nutrition_mode || 'manual'; foodId.value = record?.food_id || ''; refreshSnapshot.value = false
  for (const [key] of nutrientFields.slice(1)) form[key] = record?.[key] ?? ''
  formError.value = ''; foodError.value = ''; foods.value = []; foodLoading.value = true
  listFoods().then(result => { foods.value = result.items }).catch(err => { foodError.value = err.message }).finally(() => { foodLoading.value = false })
  editor.value.showModal()
  await nextTick()
  editor.value.querySelector('input').focus()
}
function closeDialog(dialog) { if (busy.value) return; dialog.close(); returnFocus?.focus() }
async function save() {
  formError.value = ''
  const amount = Number(form.amount_g), calories = form.calories_kcal === '' ? null : Number(form.calories_kcal)
  if (!validDate(form.record_date)) { formError.value = '请输入合法的饮食日期'; return }
  if (!Object.hasOwn(meals, form.meal_type)) { formError.value = '请选择有效餐次'; return }
  if (mode.value === 'manual' && (!form.food_name.trim() || form.food_name.trim().length > 100)) { formError.value = '食物名称应为 1～100 个字符'; return }
  if (!Number.isFinite(amount) || amount <= 0) { formError.value = '克重必须大于 0'; return }
  if (mode.value === 'manual' && calories !== null && (!Number.isFinite(calories) || calories < 0)) { formError.value = '热量必须大于等于 0，未知请留空'; return }
  if (mode.value === 'catalog' && (!foodId.value || (!useSnapshot.value && !selectedFood.value))) { formError.value = '请选择有效食物，或保留历史快照'; return }
  const payload = mode.value === 'catalog' ? { nutrition_mode:'catalog', food_id:Number(foodId.value), refresh_snapshot:refreshSnapshot.value, record_date:form.record_date, meal_type:form.meal_type, amount_g:amount, notes:form.notes } : { ...form, nutrition_mode:'manual', food_name:form.food_name.trim(), amount_g:amount, calories_kcal:calories }
  if (mode.value === 'manual') for (const [key,label] of nutrientFields.slice(1)) {
    payload[key] = form[key] === '' ? null : Number(form[key])
    if (payload[key] !== null && (!Number.isFinite(payload[key]) || payload[key]<0)) {formError.value = `${label}必须非负，未知请留空`; return}
  }
  busy.value = true; success.value = ''
  try {
    if (editingId.value === null) await createDiet(payload)
    else await updateDiet(editingId.value, payload)
    editor.value.close(); success.value = '饮食记录已保存'; returnFocus?.focus(); await load()
  } catch (err) { handleError(err, formError) }
  finally { busy.value = false }
}
function askDelete(record) { returnFocus = document.activeElement; deleting.value = record; formError.value = ''; confirmation.value.showModal() }
async function remove() {
  busy.value = true; success.value = ''; formError.value = ''
  try { await deleteDiet(deleting.value.id); confirmation.value.close(); success.value = '饮食记录已删除'; await load() }
  catch (err) { handleError(err, formError) }
  finally { busy.value = false }
}
onMounted(load)
</script>

<template>
  <section class="diet-page">
    <div class="page-heading">
      <div><h2>饮食记录</h2><p>记录每一餐，了解每日已知热量。</p></div>
      <button class="button primary" :disabled="loading || busy || noProfile || !!error" @click="openEditor()">＋ 新增记录</button>
    </div>
    <form class="panel filters" @submit.prevent="load">
      <label>开始日期<input v-model="filters.date_from" type="date" :disabled="loading || busy" /></label>
      <label>结束日期<input v-model="filters.date_to" type="date" :disabled="loading || busy" /></label>
      <button class="button primary" :disabled="loading || busy">查询</button>
      <button type="button" class="button secondary" :disabled="loading || busy" @click="resetFilters">查看全部</button>
    </form>
    <p v-if="success" class="notice" role="status">{{ success }}</p>
    <div v-if="noProfile" class="empty-state"><h2>请先建立个人档案</h2><p>饮食记录需要归属你的本地健康档案。</p><RouterLink class="button primary" to="/profile">前往建立档案</RouterLink><button class="button secondary" :disabled="loading" @click="load">建档后重新检查</button></div>
    <div v-else-if="error" class="notice failure" role="alert">{{ error }} <button class="button secondary" @click="load">重试</button></div>
    <p v-if="loading" class="empty-state" role="status">正在加载饮食记录…</p>
    <template v-else-if="!noProfile && !error">
      <div class="section-heading"><div><h2>每日热量汇总</h2><p>由后端根据当前查询结果汇总；热量为本条食物总热量，未知热量不计为 0。</p></div></div>
      <div v-if="daily.length" class="daily-grid">
        <article v-for="day in daily" :key="day.date" class="panel daily"><h3>{{ day.date }}</h3><p class="calories">{{ day.knownCount ? number(day.known) + ' kcal' : '暂无已知热量' }}</p><p>已知热量 {{ day.knownCount }} 条 · 未填热量 {{ day.unknown }} 条</p></article>
      </div>
      <div class="section-heading"><h2>饮食记录</h2><span>{{ records.length }} 条</span></div>
      <div v-if="!records.length" class="empty-state"><h2>暂无饮食记录</h2><p>当前日期范围内还没有记录，可以调整日期或添加一餐。</p><button class="button primary" @click="openEditor()">新增记录</button></div>
      <div v-else class="record-list">
        <article v-for="record in records" :key="record.id" class="panel record">
          <div class="record-date">{{ record.record_date }}<span>{{ meals[record.meal_type] }}</span></div>
          <div class="record-content"><h3>{{ record.food_name }}</h3><p>{{ number(record.amount_g) }} g · {{ record.calories_kcal === null ? '热量未知' : number(record.calories_kcal) + ' kcal' }}</p><p>模式：{{ record.nutrition_mode === 'catalog' ? '食物库快照' : '手动录入' }}<span v-if="record.is_example"> · 示例数据</span></p><p v-for="[key,label,unit] in nutrientFields.slice(1)" :key="key">{{ label }}：{{ record[key] == null ? '未知' : number(record[key]) + ' ' + unit }}</p><p class="notes">{{ record.notes || '无备注' }}</p></div>
          <div class="actions"><button class="button secondary" :disabled="busy" @click="openEditor(record)">编辑</button><button class="button danger" :disabled="busy" @click="askDelete(record)">删除</button></div>
        </article>
      </div>
    </template>
    <dialog ref="editor" aria-labelledby="diet-form-title" @cancel="busy && $event.preventDefault()">
      <form @submit.prevent="save">
        <h2 id="diet-form-title">{{ editingId === null ? '新增饮食记录' : '编辑饮食记录' }}</h2>
        <fieldset :disabled="busy"><div class="form-grid">
          <label>饮食日期<input v-model="form.record_date" type="date" required /></label>
          <label>餐次<select v-model="form.meal_type" required><option v-for="(label, key) in meals" :key="key" :value="key">{{ label }}</option></select></label>
          <label class="wide">录入模式<select v-model="mode"><option value="manual">手动录入</option><option value="catalog">从食物营养库选择</option></select></label>
          <template v-if="mode === 'catalog'"><PublicFoodPicker class="wide" @selected="f => { if (!foods.some(x => x.id === f.id)) foods.push(f); foodId = f.id }"/>
            <p v-if="foodLoading" class="wide">正在读取食物库…</p><p v-if="foodError" class="wide failure">{{ foodError }}；已有记录仍可使用原快照。</p>
            <label class="wide">选择食物<select v-model="foodId" :disabled="foodLoading"><option value="">请选择</option><option v-if="original?.food_id && !foods.some(f=>f.id===original.food_id)" :value="original.food_id">{{ original.food_name }}（保留历史快照）</option><option v-for="food in foods" :key="food.id" :value="food.id">{{ food.name }}{{ food.is_example ? '（示例）' : '' }}</option></select></label>
            <label v-if="original?.nutrition_mode === 'catalog' && Number(foodId) === original.food_id" class="wide check"><input type="checkbox" v-model="refreshSnapshot" :disabled="!selectedFood" />主动刷新为食物库最新数据（会替换本条历史快照）</label>
            <div class="wide preview"><strong>{{ useSnapshot ? '使用原历史快照' : '使用食物库当前数据' }}</strong><p v-if="useSnapshot ? original.is_example : selectedFood?.is_example">示例数据，仅演示，非真实营养资料。</p><p v-for="item in preview" :key="item.key">{{ item.label }}：每100g {{ item.per100 == null ? '未知' : number(item.per100) + item.unit }} → 本次预览 {{ item.value == null || !Number.isFinite(item.value) ? '未知' : number(item.value) + item.unit }}</p><small>预览仅供核对，保存时由后端重新计算并保留4位小数。</small></div>
          </template>
          <label v-if="mode === 'manual'" class="wide">食物名称<input v-model="form.food_name" required maxlength="100" placeholder="请输入食物名称" /></label>
          <label>食用重量（g）<input v-model="form.amount_g" type="number" step="any" required /></label>
          <label v-if="mode === 'manual'">总热量（kcal，可选）<input v-model="form.calories_kcal" type="number" min="0" step="any" placeholder="未知请留空" /></label>
          <template v-if="mode === 'manual'"><label v-for="[key,label,unit] in nutrientFields.slice(1)" :key="key">{{ label }}总量（{{ unit }}，可选）<input v-model="form[key]" type="number" min="0" step="any" placeholder="未知请留空" /></label><p class="wide">手动模式填写本条摄入总量；修改克重不会自动缩放这些数值，请核对。</p></template>
          <label class="wide">备注<textarea v-model="form.notes" rows="3" /></label>
        </div></fieldset>
        <p v-if="formError" class="notice failure" role="alert">{{ formError }}</p>
        <RouterLink v-if="noProfile" to="/profile" @click="editor.close()">前往建立个人档案</RouterLink>
        <div class="dialog-actions"><button type="button" class="button secondary" :disabled="busy" @click="closeDialog(editor)">取消</button><button class="button primary" :disabled="busy || noProfile">{{ busy ? '正在保存…' : '保存' }}</button></div>
      </form>
    </dialog>
    <dialog ref="confirmation" aria-labelledby="diet-delete-title" @cancel="busy && $event.preventDefault()">
      <h2 id="diet-delete-title">删除饮食记录？</h2><p class="delete-copy">确认删除 {{ deleting?.record_date }} 的「{{ deleting?.food_name }}」？</p>
      <p v-if="formError" class="notice failure" role="alert">{{ formError }}</p>
      <div class="dialog-actions"><button class="button secondary" :disabled="busy" autofocus @click="closeDialog(confirmation)">取消</button><button class="button danger" :disabled="busy" @click="remove">{{ busy ? '正在删除…' : '确认删除' }}</button></div>
    </dialog>
  </section>
</template>

<style scoped>
.check { flex-direction: row; align-items: center; }.check input { width: auto; }.preview { padding: 12px; background:#edf5ef; border-radius:8px; }.preview p { margin:6px 0; font-size:13px; }
.panel { background: white; border: 1px solid #e4e9df; border-radius: 12px; padding: 22px; }
.filters { display: flex; flex-wrap: wrap; gap: 14px; align-items: flex-end; }
label { display: flex; flex-direction: column; gap: 7px; font-size: 13px; }
input, select, textarea { width: 100%; min-width: 0; border: 1px solid #cddace; border-radius: 7px; padding: 10px 12px; font: inherit; color: #273e36; background: #fff; }
.notice { margin-top: 18px; padding: 13px 16px; border-radius: 8px; background: #eaf3ed; font-size: 13px; }
.failure { background: #fff0ec; color: #983b2d; }
.daily-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; }
.daily h3 { font-size: 14px; }.daily p { font-size: 12px; color: #74836d; }.daily .calories { font-size: 23px; color: var(--green); margin: 8px 0; }
.record-list { display: grid; gap: 12px; }.record { display: flex; align-items: center; gap: 24px; }
.record-date { flex-shrink: 0; font-size: 13px; }.record-date span { display: block; color: #a47038; margin-top: 6px; }
.record-content { flex: 1; min-width: 0; overflow-wrap: anywhere; }.record-content h3 { font-size: 16px; }.record-content p { font-size: 13px; margin-top: 6px; }.notes { white-space: pre-wrap; color: #7a8779; }
.actions, .dialog-actions { display: flex; gap: 10px; }.danger { background: #fff1ed; border-color: #ecd1c8; color: #a04431; }
dialog { width: min(560px, calc(100% - 32px)); max-height: 90vh; overflow-y: auto; padding: 26px; border: 1px solid #dbe5d6; border-radius: 14px; color: #273e36; }
dialog::backdrop { background: #18372b66; }dialog h2 { font-size: 21px; margin-bottom: 20px; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 17px; }.wide { grid-column: 1 / -1; }.dialog-actions { justify-content: flex-end; margin-top: 22px; }.delete-copy { overflow-wrap: anywhere; }
@media(max-width: 600px) { .page-heading { flex-wrap: wrap; }.filters label { width: 100%; }.record { flex-wrap: wrap; gap: 12px; }.record-date { width: 100%; }.actions { width: 100%; justify-content: flex-end; }.form-grid { grid-template-columns: 1fr; }.wide { grid-column: auto; }.panel { padding: 17px; } }
</style>

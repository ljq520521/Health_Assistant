<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import FoodNutritionCard from './FoodNutritionCard.vue'
import { archiveFood, createCategory, createFood, deleteCategory, listCategories, listFoods, updateCategory, updateFood } from '../../api/foodLibrary.js'

const props = defineProps({ timeZone: { type: String, required: true } })
const foods = ref([]), categories = ref([]), loading = ref(false), busy = ref(false), error = ref(''), errorCode = ref(''), success = ref('')
const filters = reactive({ q: '', category: '' })
const foodDialog = ref(null), categoryDialog = ref(null), confirmDialog = ref(null)
const foodId = ref(null), foodError = ref(''), categoryError = ref(''), categoryId = ref(null), categoryName = ref('')
const pending = ref(null), confirmError = ref('')
const form = reactive({ name: '', category_id: '', calories_per_100g: '', protein_g_per_100g: '', fat_g_per_100g: '', carbohydrate_g_per_100g: '', source_type: 'user_entered', source_note: '', source_url: '' })
const nutrients = [ ['calories_per_100g', '热量', 'kcal'], ['protein_g_per_100g', '蛋白质', 'g'], ['fat_g_per_100g', '脂肪', 'g'], ['carbohydrate_g_per_100g', '碳水化合物', 'g'] ]
const categoryMap = computed(() => Object.fromEntries(categories.value.map(item => [item.id, item.name])))
const blocked = computed(() => loading.value || busy.value || !!error.value)
let requestVersion = 0
function handleError(err, target) {
  target.value = err.message
  if (err.code === 'PROFILE_REQUIRED') { errorCode.value = err.code; error.value = err.message; foods.value = [] }
}
async function load() {
  const version = ++requestVersion
  loading.value = true; error.value = ''; errorCode.value = ''
  try {
    const params = { q: filters.q.trim(), category_id: filters.category && filters.category !== 'none' ? filters.category : '', uncategorized: filters.category === 'none' }
    const [categoryResult, foodResult] = await Promise.all([listCategories(), listFoods(params)])
    if (version !== requestVersion) return
    categories.value = categoryResult.items; foods.value = foodResult.items
  } catch (err) {
    if (version !== requestVersion) return
    error.value = err.message; errorCode.value = err.code || ''; foods.value = []
  } finally { if (version === requestVersion) loading.value = false }
}
function resetFilters() { filters.q = ''; filters.category = ''; load() }
function openFood(food = null) {
  foodId.value = food?.id ?? null; foodError.value = ''; success.value = ''
  Object.assign(form, { name: food?.name ?? '', category_id: food?.category_id ?? '', source_type: food?.source_type ?? 'user_entered', source_note: food?.source_note ?? '', source_url: food?.source_url ?? '' })
  for (const [key] of nutrients) form[key] = food?.[key] ?? ''
  foodDialog.value.showModal()
}
function close(dialog) { if (!busy.value) dialog.close() }
async function saveFood() {
  foodError.value = ''
  if (!form.name.trim() || form.name.trim().length > 100) { foodError.value = '食物名称应为 1～100 个字符'; return }
  const payload = { ...form, name: form.name.trim(), category_id: form.category_id === '' ? null : Number(form.category_id), source_note: form.source_note.trim(), source_url: form.source_url.trim() }
  for (const [key, label] of nutrients) {
    payload[key] = form[key] === '' ? null : Number(form[key])
    if (payload[key] !== null && (!Number.isFinite(payload[key]) || payload[key] < 0)) { foodError.value = `${label}必须大于等于 0，未知请留空`; return }
  }
  if (payload.source_type === 'referenced' && !payload.source_note && !payload.source_url) { foodError.value = '参考资料必须填写来源说明或链接'; return }
  if (payload.source_url) {
    try { if (!['http:', 'https:'].includes(new URL(payload.source_url).protocol)) throw new Error() }
    catch { foodError.value = '来源链接必须为完整的 http 或 https 地址'; return }
  }
  busy.value = true
  try {
    if (foodId.value === null) await createFood(payload)
    else await updateFood(foodId.value, payload)
    foodDialog.value.close(); success.value = '食物营养信息已保存'; await load()
  } catch (err) { handleError(err, foodError) }
  finally { busy.value = false }
}
function resetCategory() { categoryId.value = null; categoryName.value = ''; categoryError.value = '' }
function manageCategories() { resetCategory(); success.value = ''; categoryDialog.value.showModal() }
function editCategory(item) { categoryId.value = item.id; categoryName.value = item.name; categoryError.value = '' }
async function saveCategory() {
  const name = categoryName.value.trim()
  if (!name || name.length > 50) { categoryError.value = '分类名称应为 1～50 个字符'; return }
  busy.value = true; categoryError.value = ''
  try {
    if (categoryId.value === null) await createCategory({ name })
    else await updateCategory(categoryId.value, { name })
    resetCategory(); success.value = '分类已保存'; await load()
  } catch (err) { handleError(err, categoryError) }
  finally { busy.value = false }
}
function askRemove(kind, item) { pending.value = { kind, item }; confirmError.value = ''; confirmDialog.value.showModal() }
async function remove() {
  busy.value = true; confirmError.value = ''
  try {
    if (pending.value.kind === 'category') {
      await deleteCategory(pending.value.item.id)
      if (String(filters.category) === String(pending.value.item.id)) filters.category = ''
      if (categoryId.value === pending.value.item.id) resetCategory()
      success.value = '分类已删除'
    } else { await archiveFood(pending.value.item.id); success.value = '食物已归档' }
    confirmDialog.value.close(); await load()
  } catch (err) { handleError(err, confirmError) }
  finally { busy.value = false }
}
onMounted(load)
</script>

<template>
  <section class="food-library">
    <div class="library-heading"><div><h2>食物营养库</h2><p>维护每 100g 营养信息。未知请留空，数值 0 表示明确为零。</p></div><div class="actions"><button class="button secondary" :disabled="blocked" @click="manageCategories">管理分类</button><button class="button primary" :disabled="blocked" @click="openFood()">＋ 新增食物</button></div></div>
    <form class="panel filters" @submit.prevent="load">
      <label>食物名称搜索<input v-model="filters.q" maxlength="100" placeholder="输入食物名称" :disabled="loading || busy" /></label>
      <label>食物分类筛选<select v-model="filters.category" :disabled="loading || busy"><option value="">全部分类</option><option value="none">未分类</option><option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option></select></label>
      <button class="button primary" :disabled="loading || busy">查询食物</button><button type="button" class="button secondary" :disabled="loading || busy" @click="resetFilters">重置筛选</button>
    </form>
    <p v-if="success" class="notice" role="status">{{ success }}</p>
    <div v-if="errorCode === 'PROFILE_REQUIRED'" class="empty-state"><h3>请先建立个人档案</h3><p>食物营养资料会保存在你的本地档案下。</p><RouterLink class="button primary" to="/profile">前往建立档案</RouterLink><button class="button secondary" @click="load">重新检查</button></div>
    <div v-else-if="error" class="notice failure" role="alert">{{ errorCode === 'DIET_MIGRATION_REQUIRED' ? '食物库尚未启用，请联系项目维护者完成数据库升级。饮食记录仍可使用。' : error }} <button class="button secondary" @click="load">重试</button></div>
    <p v-if="loading" class="empty-state" role="status">正在加载食物营养库…</p>
    <template v-else-if="!error">
      <p class="count">共 {{ foods.length }} 种食物 · 数值均为每 100g 含量</p>
      <div v-if="!foods.length" class="empty-state"><h3>暂无符合条件的食物</h3><p>可以调整筛选条件，或录入有明确来源的食物资料。</p><button class="button primary" @click="openFood()">新增食物</button></div>
      <div v-else class="food-grid">
        <FoodNutritionCard v-for="food in foods" :key="food.id" :food="food" :category="categoryMap[food.category_id] || '未分类'" :time-zone="timeZone" :busy="busy" @edit="openFood" @archive="askRemove('food', $event)" />
      </div>
    </template>
    <dialog ref="foodDialog" aria-labelledby="food-form-title" @cancel="busy && $event.preventDefault()">
      <form @submit.prevent="saveFood"><h2 id="food-form-title">{{ foodId === null ? '新增食物' : '编辑食物' }}</h2><p class="muted">请输入每 100g 含量，未知项留空。</p>
        <fieldset :disabled="busy"><div class="form-grid">
          <label>食物名称<input v-model="form.name" required maxlength="100" /></label>
          <label>所属分类<select v-model="form.category_id"><option value="">未分类</option><option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option></select></label>
          <label v-for="[key, label, unit] in nutrients" :key="key">{{ label }}（{{ unit }}/100g）<input v-model="form[key]" type="number" min="0" step="any" placeholder="未知请留空" /></label>
          <label class="wide">数据来源<select v-model="form.source_type"><option value="user_entered">用户录入</option><option value="referenced">参考资料</option><option value="example">示例数据（仅演示）</option></select></label>
          <p v-if="form.source_type === 'example'" class="wide example-note">保存后会明确标记为示例数据，不会作为权威资料展示。</p>
          <label class="wide">来源说明<textarea v-model="form.source_note" maxlength="1000" rows="3" placeholder="例如产品包装标签、资料名称；参考资料需填写说明或链接" /></label>
          <label class="wide">来源链接<input v-model="form.source_url" type="url" maxlength="2000" placeholder="https://…（可选）" /></label>
        </div></fieldset>
        <p v-if="foodError" role="alert" class="notice failure">{{ foodError }}</p>
        <div class="dialog-actions"><button type="button" class="button secondary" :disabled="busy" @click="close(foodDialog)">取消</button><button class="button primary" :disabled="busy">{{ busy ? '正在保存…' : '保存食物' }}</button></div>
      </form>
    </dialog>
    <dialog ref="categoryDialog" aria-labelledby="category-title" @cancel="busy && $event.preventDefault()">
      <h2 id="category-title">管理食物分类</h2><form @submit.prevent="saveCategory" class="category-form"><label>分类名称<input v-model="categoryName" required maxlength="50" :disabled="busy" /></label><button class="button primary" :disabled="busy">{{ categoryId === null ? '新增分类' : '保存分类' }}</button><button v-if="categoryId !== null" type="button" class="button secondary" :disabled="busy" @click="resetCategory">取消编辑</button></form>
      <p v-if="categoryError" role="alert" class="notice failure">{{ categoryError }}</p><p v-if="!categories.length" class="muted">暂无分类，可以先创建一个。</p>
      <ul class="category-list"><li v-for="item in categories" :key="item.id"><span>{{ item.name }}</span><div class="actions"><button class="button secondary" :disabled="busy" :aria-label="`编辑分类 ${item.name}`" @click="editCategory(item)">编辑</button><button class="button danger" :disabled="busy" :aria-label="`删除分类 ${item.name}`" @click="askRemove('category', item)">删除</button></div></li></ul>
      <p class="muted">仍有有效食物使用的分类不能删除；归档食物不会被删除。</p><div class="dialog-actions"><button class="button secondary" :disabled="busy" @click="close(categoryDialog)">关闭</button></div>
    </dialog>
    <dialog ref="confirmDialog" aria-labelledby="library-confirm-title" @cancel="busy && $event.preventDefault()">
      <h2 id="library-confirm-title">{{ pending?.kind === 'food' ? '归档食物？' : '删除分类？' }}</h2><p>确认{{ pending?.kind === 'food' ? '归档' : '删除' }}「{{ pending?.item.name }}」？</p><p v-if="pending?.kind === 'food'" class="muted">归档后不再显示在食物库中；原饮食记录会保留。</p><p v-if="confirmError" role="alert" class="notice failure">{{ confirmError }}</p><div class="dialog-actions"><button class="button secondary" :disabled="busy" autofocus @click="close(confirmDialog)">取消</button><button class="button danger" :disabled="busy" @click="remove">{{ busy ? '正在处理…' : '确认' }}</button></div>
    </dialog>
  </section>
</template>

<style scoped>
.library-heading { display:flex; justify-content:space-between; align-items:center; gap:14px; }.library-heading { margin-bottom:20px; flex-wrap:wrap; }.library-heading h2 { font-size:23px; }.library-heading p,.muted,.count { color:#758477; font-size:12px; margin-top:7px; }.panel { padding:22px; background:#fff; border:1px solid #e1e8de; border-radius:12px; }.filters,.actions,.category-form { display:flex; align-items:flex-end; flex-wrap:wrap; gap:10px; }.filters label:first-child { flex:1; }.filters label { min-width:160px; }.actions { align-items:center; }.count { margin:18px 0; }
label { display:flex; flex-direction:column; gap:7px; font-size:13px; }input,select,textarea { width:100%; min-width:0; font:inherit; color:inherit; padding:10px 12px; border:1px solid #cddace; border-radius:7px; background:#fff; }.food-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr)); gap:16px; }.example-note { color:#9a6524; background:#fff5e7; font-size:12px; padding:9px; border-radius:6px; }.danger { background:#fff1ed; border-color:#ecd1c8; color:#a04431; }.notice { margin:14px 0; padding:12px; border-radius:7px; background:#eaf3ed; font-size:13px; }.failure { background:#fff0ec; color:#983b2d; }
dialog { width:min(620px,calc(100% - 32px)); max-height:90vh; overflow-y:auto; padding:24px; border:1px solid #dbe5d6; border-radius:14px; color:#273e36; }dialog::backdrop { background:#18372b66; }dialog h2 { font-size:21px; margin-bottom:14px; }fieldset { border:0; padding:0; margin:18px 0 0; min-width:0; }.form-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }.wide { grid-column:1 / -1; }.dialog-actions { display:flex; justify-content:flex-end; gap:10px; margin-top:22px; }.category-form label { flex:1; }.category-list { list-style:none; padding:0; }.category-list li { display:flex; justify-content:space-between; gap:10px; align-items:center; padding:12px 0; border-bottom:1px solid #edf0e9; }.category-list span { overflow-wrap:anywhere; min-width:0; }
@media(max-width:600px) { .filters label { width:100%; }.form-grid { grid-template-columns:1fr; }.wide { grid-column:auto; }.panel { padding:17px; }.category-list li { flex-wrap:wrap; }.library-heading>.actions { width:100%; } }
</style>

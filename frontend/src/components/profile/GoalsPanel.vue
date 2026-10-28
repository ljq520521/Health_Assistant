<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { createGoal, deleteGoal, listGoals, updateGoal } from '../../api/profile'

const props = defineProps({
  canEdit: { type: Boolean, default: false },
  reloadKey: { type: Number, default: 0 },
})

const goals = ref([])
const loading = ref(true)
const error = ref('')
const notice = ref('')

const dialog = ref(null)
const deleteDialog = ref(null)
const editingId = ref(null)
const deleting = ref(null)
const busy = ref(false)
const dialogError = ref('')

const form = reactive({
  title: '',
  target_value: '',
  current_value: '',
  unit: '',
  due_date: '',
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    goals.value = (await listGoals()).items
  } catch (err) {
    error.value = err.status === 409 ? '请先建立个人档案，再添加健康目标' : err.message
  } finally {
    loading.value = false
  }
}

function fillForm(goal) {
  form.title = goal?.title || ''
  form.target_value = goal?.target_value ?? ''
  form.current_value = goal?.current_value ?? ''
  form.unit = goal?.unit || ''
  form.due_date = goal?.due_date || ''
}

function openCreate() {
  editingId.value = null
  fillForm(null)
  dialogError.value = ''
  notice.value = ''
  dialog.value?.showModal()
}

function openEdit(goal) {
  editingId.value = goal.id
  fillForm(goal)
  dialogError.value = ''
  notice.value = ''
  dialog.value?.showModal()
}

function closeDialog() {
  if (!busy.value) dialog.value?.close()
}

async function submit() {
  dialogError.value = ''
  const title = form.title.trim()
  const unit = form.unit.trim()
  const target = Number(form.target_value)
  const current = form.current_value === '' ? 0 : Number(form.current_value)

  if (!title) {
    dialogError.value = '请填写目标名称'
    return
  }
  if (!Number.isFinite(target) || target <= 0) {
    dialogError.value = '目标值需为大于 0 的数字'
    return
  }
  if (!Number.isFinite(current) || current < 0) {
    dialogError.value = '当前值需为不小于 0 的数字'
    return
  }
  if (!unit) {
    dialogError.value = '请填写单位，例如“分钟”或“次”'
    return
  }

  busy.value = true
  try {
    const payload = {
      title,
      target_value: target,
      current_value: current,
      unit,
      due_date: form.due_date || null,
    }
    if (editingId.value) await updateGoal(editingId.value, payload)
    else await createGoal(payload)
    dialog.value?.close()
    notice.value = '健康目标已保存'
    await load()
  } catch (err) {
    dialogError.value = err.message
  } finally {
    busy.value = false
  }
}

function confirmDelete(goal) {
  deleting.value = goal
  deleteDialog.value?.showModal()
}

async function removeGoal() {
  if (!deleting.value) return
  busy.value = true
  try {
    await deleteGoal(deleting.value.id)
    deleteDialog.value?.close()
    notice.value = '健康目标已删除'
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
    deleting.value = null
  }
}

watch(() => props.reloadKey, load)
onMounted(load)
</script>

<template>
  <section class="goals-panel" aria-labelledby="goals-title">
    <div class="card-heading">
      <div>
        <h2 id="goals-title">健康目标</h2>
        <p>手动累计型目标，系统按当前值 / 目标值计算完成度。</p>
      </div>
      <button v-if="canEdit" class="button primary" @click="openCreate">新增目标</button>
    </div>

    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="loading" role="status">正在读取健康目标…</p>

    <div v-else-if="goals.length === 0" class="empty">
      <h3>还没有健康目标</h3>
      <p>{{ canEdit ? '例如：本周步行 120 分钟，然后每周手动更新当前值。' : '管理员添加目标后，你会在这里看到完成度。' }}</p>
      <button v-if="canEdit" class="button secondary" @click="openCreate">建立第一个目标</button>
    </div>

    <ul v-else class="goal-list">
      <li v-for="goal in goals" :key="goal.id" class="goal-card">
        <div class="goal-top">
          <div>
            <h3>{{ goal.title }}</h3>
            <p class="goal-meta">
              当前 {{ goal.current_value }} / {{ goal.target_value }} {{ goal.unit }}
              <span v-if="goal.due_date">· 截止 {{ goal.due_date }}</span>
            </p>
          </div>
          <span class="goal-percent">{{ goal.progress_percent }}%</span>
        </div>

        <div
          class="progress"
          role="progressbar"
          :aria-valuenow="goal.progress_percent"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`${goal.title}完成度`"
        >
          <span :style="{ width: Math.min(goal.progress_percent, 100) + '%' }"></span>
        </div>

        <div v-if="canEdit" class="goal-actions">
          <button class="button secondary" @click="openEdit(goal)">编辑</button>
          <button class="button secondary danger" @click="confirmDelete(goal)">删除</button>
        </div>
      </li>
    </ul>

    <dialog ref="dialog" aria-labelledby="goal-dialog-title" @cancel="busy && $event.preventDefault()">
      <form @submit.prevent="submit">
        <h2 id="goal-dialog-title">{{ editingId ? '编辑健康目标' : '新增健康目标' }}</h2>
        <p>目标进度由你手动更新；系统不读取其他模块的记录，也不做反向目标。</p>

        <label>
          目标名称
          <input v-model="form.title" maxlength="100" required placeholder="例如：本周步行 120 分钟" :disabled="busy" />
        </label>

        <label>
          单位
          <input v-model="form.unit" maxlength="20" required placeholder="例如：分钟、次、公里" :disabled="busy" />
        </label>

        <div class="dialog-row">
          <label>
            目标值
            <input v-model="form.target_value" type="number" min="0.1" step="any" required :disabled="busy" />
          </label>
          <label>
            当前值
            <input v-model="form.current_value" type="number" min="0" step="any" :disabled="busy" />
          </label>
        </div>

        <label>
          截止日期（可选）
          <input v-model="form.due_date" type="date" :disabled="busy" />
        </label>

        <p v-if="dialogError" class="error" role="alert">{{ dialogError }}</p>

        <div class="dialog-actions">
          <button type="button" class="button secondary" :disabled="busy" @click="closeDialog">取消</button>
          <button class="button primary" :disabled="busy">{{ busy ? '正在保存…' : '保存' }}</button>
        </div>
      </form>
    </dialog>

    <dialog ref="deleteDialog" aria-labelledby="delete-title">
      <h2 id="delete-title">删除健康目标？</h2>
      <p>“{{ deleting?.title }}”删除后无法恢复，历史完成度也不会保留。</p>
      <div class="dialog-actions">
        <button type="button" class="button secondary" :disabled="busy" @click="deleteDialog?.close()">取消</button>
        <button type="button" class="button primary danger-solid" :disabled="busy" @click="removeGoal">
          {{ busy ? '正在删除…' : '确认删除' }}
        </button>
      </div>
    </dialog>
  </section>
</template>

<style scoped>
.goals-panel {
  background: #fff;
  border: 1px solid #e4e9e0;
  border-radius: 13px;
  padding: 26px 28px;
}
.card-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}
.card-heading h2 {
  font-size: 18px;
  font-weight: 600;
}
.card-heading p {
  margin-top: 6px;
  font-size: 12px;
  color: #7a877e;
}
.notice,
.error {
  margin: 10px 0;
  padding: 10px 13px;
  border-radius: 7px;
  font-size: 12px;
}
.notice {
  background: #edf5ef;
  color: #2f6b4f;
}
.error {
  background: #fff0ec;
  color: #983b2d;
}
.empty {
  padding: 40px 20px;
  text-align: center;
  border: 1px dashed #d7e2d0;
  border-radius: 11px;
}
.empty h3 {
  font-size: 16px;
  margin-bottom: 8px;
}
.empty p {
  font-size: 12px;
  color: #7b8975;
  margin-bottom: 16px;
}
.goal-list {
  list-style: none;
  margin: 16px 0 0;
  padding: 0;
  display: grid;
  gap: 12px;
}
.goal-card {
  border: 1px solid #e7ece3;
  border-radius: 10px;
  padding: 16px 18px;
}
.goal-top {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}
.goal-top h3 {
  font-size: 15px;
  font-weight: 600;
}
.goal-meta {
  margin-top: 5px;
  font-size: 11px;
  color: #7c897d;
}
.goal-percent {
  font-size: 18px;
  font-weight: 600;
  color: #2f6b4f;
  white-space: nowrap;
}
.progress {
  margin: 12px 0 10px;
  height: 7px;
  border-radius: 999px;
  background: #eef2ea;
  overflow: hidden;
}
.progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #4f8a6d;
  transition: width 0.3s;
}
.goal-actions {
  display: flex;
  gap: 8px;
}
.goal-actions .button {
  min-height: 30px;
  padding: 4px 12px;
}
.button.danger {
  color: #9a4a36;
  border-color: #e9d4cc;
}
dialog {
  width: min(560px, calc(100% - 32px));
  max-height: 90vh;
  overflow: auto;
  padding: 24px;
  border: 1px solid #dbe5d6;
  border-radius: 14px;
  color: #273e36;
  background: #fff;
}
dialog::backdrop {
  background: #18372b66;
}
dialog h2 {
  font-size: 20px;
  margin-bottom: 8px;
}
dialog p {
  font-size: 12px;
  line-height: 1.7;
  color: #61776a;
  margin-bottom: 14px;
}
dialog label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #52695c;
  margin-bottom: 12px;
}
dialog input {
  width: 100%;
  padding: 9px 11px;
  border: 1px solid #cddace;
  border-radius: 7px;
  font: inherit;
  font-size: 13px;
  color: #273e36;
}
dialog input:focus-visible {
  outline: 2px solid #39735b;
  outline-offset: 1px;
}
.dialog-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}
.danger-solid {
  background: #9a4a36;
  color: #fff;
}
@media (max-width: 640px) {
  .goals-panel {
    padding: 20px;
  }
  .dialog-row {
    grid-template-columns: 1fr;
  }
}
</style>

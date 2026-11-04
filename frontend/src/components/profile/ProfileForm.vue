<script setup>
import { reactive, ref, watch } from 'vue'
import { saveProfile } from '../../api/profile'

const props = defineProps({
  profile: { type: Object, default: null },
  canEdit: { type: Boolean, default: false },
})
const emit = defineEmits(['saved'])

const form = reactive({
  display_name: '',
  height_cm: '',
  weight_kg: '',
  medical_history: '',
  allergies: '',
  medications: '',
  preferences: '',
})
const busy = ref(false)
const error = ref('')
const success = ref('')

function fill(profile) {
  form.display_name = profile?.display_name || ''
  form.height_cm = profile?.height_cm ?? ''
  form.weight_kg = profile?.weight_kg ?? ''
  form.medical_history = profile?.medical_history || ''
  form.allergies = profile?.allergies || ''
  form.medications = profile?.medications || ''
  form.preferences = profile?.preferences || ''
}

watch(() => props.profile, fill, { immediate: true })

function optionalNumber(value, label) {
  if (value === '' || value === null || value === undefined) return null
  const number = Number(value)
  if (!Number.isFinite(number) || number <= 0) {
    throw new Error(`${label}需为大于 0 的数字，未填写请留空`)
  }
  return number
}

async function submit() {
  error.value = ''
  success.value = ''
  if (!form.display_name.trim()) {
    error.value = '请填写昵称'
    return
  }
  let height
  let weight
  try {
    height = optionalNumber(form.height_cm, '身高')
    weight = optionalNumber(form.weight_kg, '体重')
  } catch (err) {
    error.value = err.message
    return
  }

  busy.value = true
  try {
    const saved = await saveProfile({
      display_name: form.display_name.trim(),
      height_cm: height,
      weight_kg: weight,
      medical_history: form.medical_history,
      allergies: form.allergies,
      medications: form.medications,
      preferences: form.preferences,
    })
    emit('saved', saved)
    success.value = '档案已保存'
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="profile-card" aria-labelledby="profile-title">
    <div class="card-heading">
      <div>
        <h2 id="profile-title">{{ profile ? '健康档案' : '建立个人档案' }}</h2>
        <p>档案只保存在本机，供饮食、运动、睡眠与生理期模块统一归属。</p>
      </div>
      <span class="soft-badge">{{ profile ? '已建档' : '待建档' }}</span>
    </div>

    <p v-if="!canEdit" class="readonly-note" role="note">
      当前为只读账户，档案由管理员维护；你仍可在“账户与隐私”中修改自己的密码与隐私设置。
    </p>
    <p v-if="profile?.sensitive_masked" class="masked-note" role="note">
      敏感字段已按隐私设置隐藏；管理员可查看完整内容。
    </p>

    <form @submit.prevent="submit">
      <fieldset :disabled="!canEdit || busy">
        <label class="field">
          昵称
          <input v-model="form.display_name" maxlength="50" required placeholder="例如：小林" />
        </label>

        <div class="field-row">
          <label class="field">
            身高（cm）
            <input v-model="form.height_cm" type="number" step="0.1" min="0.1" placeholder="可留空" />
          </label>
          <label class="field">
            体重（kg）
            <input v-model="form.weight_kg" type="number" step="0.1" min="0.1" placeholder="可留空" />
          </label>
        </div>

        <label class="field">
          既往病史
          <textarea v-model="form.medical_history" rows="2" maxlength="2000" placeholder="没有可不填"></textarea>
        </label>
        <label class="field">
          过敏史
          <textarea v-model="form.allergies" rows="2" maxlength="2000" placeholder="例如：花粉、海鲜"></textarea>
        </label>
        <label class="field">
          用药记录
          <textarea v-model="form.medications" rows="2" maxlength="2000" placeholder="长期或近期用药"></textarea>
        </label>
        <label class="field">
          生活偏好
          <textarea
            v-model="form.preferences"
            rows="3"
            maxlength="2000"
            placeholder="饮食禁忌、运动偏好、作息习惯等"
          ></textarea>
        </label>
      </fieldset>

      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <p v-if="success" class="success" role="status">{{ success }}</p>

      <div v-if="canEdit" class="actions">
        <button class="button primary" :disabled="busy">
          {{ busy ? '正在保存…' : profile ? '保存档案' : '建立档案' }}
        </button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.profile-card {
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
  margin-bottom: 18px;
}
.card-heading h2 {
  font-size: 18px;
  font-weight: 600;
}
.card-heading p {
  margin-top: 6px;
  font-size: 12px;
  color: #7a877e;
  line-height: 1.7;
}
.soft-badge {
  padding: 4px 10px;
  border: 1px solid #dce5d8;
  border-radius: 999px;
  color: #5d7566;
  font-size: 11px;
  white-space: nowrap;
}
fieldset {
  border: 0;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #52695c;
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
input,
textarea {
  width: 100%;
  padding: 9px 11px;
  border: 1px solid #cddace;
  border-radius: 7px;
  font: inherit;
  font-size: 13px;
  color: #273e36;
  background: #fff;
  resize: vertical;
}
input:focus-visible,
textarea:focus-visible {
  outline: 2px solid #39735b;
  outline-offset: 1px;
}
input:disabled,
textarea:disabled {
  background: #f5f8f4;
  color: #7d8b81;
}
.readonly-note,
.masked-note {
  margin-bottom: 14px;
  padding: 10px 13px;
  border-radius: 7px;
  font-size: 12px;
  line-height: 1.7;
}
.readonly-note {
  background: #f4f7f2;
  color: #647a6c;
}
.masked-note {
  background: #fbf4e8;
  color: #8a6a32;
}
.error,
.success {
  margin-top: 14px;
  padding: 10px 13px;
  border-radius: 7px;
  font-size: 12px;
}
.error {
  background: #fff0ec;
  color: #983b2d;
}
.success {
  background: #edf5ef;
  color: #2f6b4f;
}
.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}
@media (max-width: 640px) {
  .profile-card {
    padding: 20px;
  }
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>

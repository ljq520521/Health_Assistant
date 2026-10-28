<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import {
  changePassword,
  listUsers,
  registerAccount,
  setUserStatus,
  updatePrivacy,
} from '../../api/profile'

const props = defineProps({
  me: { type: Object, required: true },
  isAdmin: { type: Boolean, default: false },
})
const emit = defineEmits(['updated', 'logout'])

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordBusy = ref(false)
const passwordError = ref('')
const passwordSuccess = ref('')

const privacy = reactive({
  consent_health_data: true,
  mask_sensitive: false,
  analytics_consent: false,
})
const privacyBusy = ref(false)
const privacyError = ref('')
const privacySuccess = ref('')

const users = ref([])
const usersLoading = ref(false)
const usersError = ref('')
const createUsername = ref('')
const createPassword = ref('')
const createBusy = ref(false)
const createError = ref('')
const createSuccess = ref('')

const roleText = (role) => (role === 'admin' ? '管理员' : '只读账户')
const statusText = (status) => (status === 'active' ? '正常' : '已停用')

watch(
  () => props.me,
  (value) => {
    if (!value) return
    privacy.consent_health_data = Boolean(value.consent_health_data)
    privacy.mask_sensitive = Boolean(value.mask_sensitive)
    privacy.analytics_consent = Boolean(value.analytics_consent)
  },
  { immediate: true },
)

async function submitPassword() {
  passwordError.value = ''
  passwordSuccess.value = ''
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = '两次输入的新密码不一致'
    return
  }
  if (!/[A-Za-z]/.test(newPassword.value) || !/\d/.test(newPassword.value)) {
    passwordError.value = '新密码需同时包含字母和数字'
    return
  }
  passwordBusy.value = true
  try {
    const result = await changePassword({
      current_password: currentPassword.value,
      new_password: newPassword.value,
    })
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    passwordSuccess.value = '密码已修改，其他设备上的登录状态已失效'
    emit('updated', result.user)
  } catch (err) {
    passwordError.value = err.message
  } finally {
    passwordBusy.value = false
  }
}

async function savePrivacy() {
  privacyError.value = ''
  privacySuccess.value = ''
  privacyBusy.value = true
  try {
    const user = await updatePrivacy({
      consent_health_data: privacy.consent_health_data,
      mask_sensitive: privacy.mask_sensitive,
      analytics_consent: privacy.analytics_consent,
    })
    privacySuccess.value = '隐私设置已保存'
    emit('updated', user)
  } catch (err) {
    privacyError.value = err.message
  } finally {
    privacyBusy.value = false
  }
}

async function loadUsers() {
  if (!props.isAdmin) return
  usersLoading.value = true
  usersError.value = ''
  try {
    users.value = (await listUsers()).items
  } catch (err) {
    usersError.value = err.message
  } finally {
    usersLoading.value = false
  }
}

async function createAccount() {
  createError.value = ''
  createSuccess.value = ''
  if (!/^[A-Za-z0-9_]{3,32}$/.test(createUsername.value)) {
    createError.value = '用户名需为 3–32 位字母、数字或下划线'
    return
  }
  createBusy.value = true
  try {
    await registerAccount({ username: createUsername.value, password: createPassword.value })
    createSuccess.value = '只读账户已创建'
    createUsername.value = ''
    createPassword.value = ''
    await loadUsers()
  } catch (err) {
    createError.value = err.message
  } finally {
    createBusy.value = false
  }
}

async function toggleStatus(user) {
  usersError.value = ''
  try {
    await setUserStatus(user.id, user.status === 'active' ? 'disabled' : 'active')
    await loadUsers()
  } catch (err) {
    usersError.value = err.message
  }
}

watch(() => props.isAdmin, (value) => value && loadUsers())
onMounted(loadUsers)
</script>

<template>
  <div class="account-stack">
    <section class="panel" aria-labelledby="account-title">
      <div class="panel-heading">
        <div>
          <h2 id="account-title">账户与安全</h2>
          <p>本地账户只用于保护这台电脑上的健康数据。</p>
        </div>
        <span class="soft-badge">{{ roleText(me.role) }}</span>
      </div>

      <dl class="account-facts">
        <div><dt>用户名</dt><dd>{{ me.username }}</dd></div>
        <div><dt>状态</dt><dd>{{ statusText(me.status) }}</dd></div>
        <div><dt>上次登录</dt><dd>{{ me.last_login_at || '本次为首次登录' }}</dd></div>
        <div><dt>创建时间</dt><dd>{{ me.created_at }}</dd></div>
      </dl>
    </section>

    <section class="panel" aria-labelledby="password-title">
      <div class="panel-heading">
        <div>
          <h2 id="password-title">修改密码</h2>
          <p>修改后，之前签发的登录令牌会立即失效。</p>
        </div>
      </div>

      <form @submit.prevent="submitPassword">
        <label class="field">
          当前密码
          <input v-model="currentPassword" type="password" autocomplete="current-password" required :disabled="passwordBusy" />
        </label>
        <div class="field-row">
          <label class="field">
            新密码
            <input v-model="newPassword" type="password" autocomplete="new-password" minlength="8" maxlength="128" required :disabled="passwordBusy" />
          </label>
          <label class="field">
            确认新密码
            <input v-model="confirmPassword" type="password" autocomplete="new-password" minlength="8" maxlength="128" required :disabled="passwordBusy" />
          </label>
        </div>
        <p v-if="passwordError" class="error" role="alert">{{ passwordError }}</p>
        <p v-if="passwordSuccess" class="success" role="status">{{ passwordSuccess }}</p>
        <div class="actions">
          <button class="button primary" :disabled="passwordBusy">
            {{ passwordBusy ? '正在修改…' : '修改密码' }}
          </button>
        </div>
      </form>
    </section>

    <section class="panel" aria-labelledby="privacy-title">
      <div class="panel-heading">
        <div>
          <h2 id="privacy-title">数据授权与隐私开关</h2>
          <p>设置只保存在本机，不会上传到任何服务器。</p>
        </div>
      </div>

      <form @submit.prevent="savePrivacy">
        <label class="switch-row">
          <input v-model="privacy.consent_health_data" type="checkbox" :disabled="privacyBusy" />
          <span>
            <strong>授权处理健康数据</strong>
            <small>关闭后，本账户访问档案与目标接口会返回 403；可随时重新开启。</small>
          </span>
        </label>
        <label class="switch-row" :class="{ disabled: isAdmin }">
          <input v-model="privacy.mask_sensitive" type="checkbox" :disabled="privacyBusy || isAdmin" />
          <span>
            <strong>隐藏敏感字段</strong>
            <small>对只读账户隐藏既往病史、过敏史与用药记录；管理员始终查看完整档案。</small>
          </span>
        </label>
        <label class="switch-row">
          <input v-model="privacy.analytics_consent" type="checkbox" :disabled="privacyBusy" />
          <span>
            <strong>匿名使用统计</strong>
            <small>仅保存偏好；当前版本没有任何上传或统计逻辑。</small>
          </span>
        </label>

        <p v-if="privacyError" class="error" role="alert">{{ privacyError }}</p>
        <p v-if="privacySuccess" class="success" role="status">{{ privacySuccess }}</p>
        <div class="actions">
          <button class="button primary" :disabled="privacyBusy">
            {{ privacyBusy ? '正在保存…' : '保存隐私设置' }}
          </button>
        </div>
      </form>
    </section>

    <section v-if="isAdmin" class="panel" aria-labelledby="users-title">
      <div class="panel-heading">
        <div>
          <h2 id="users-title">账号管理</h2>
          <p>首个账户为管理员；新建账户默认为只读，只能查看档案与目标。</p>
        </div>
        <button class="button secondary" :disabled="usersLoading" @click="loadUsers">刷新</button>
      </div>

      <form class="create-account" @submit.prevent="createAccount">
        <h3>新增只读账户</h3>
        <div class="create-row">
          <input
            v-model="createUsername"
            placeholder="用户名（3–32 位字母、数字或下划线）"
            maxlength="32"
            :disabled="createBusy"
          />
          <input
            v-model="createPassword"
            type="password"
            placeholder="初始密码（至少 8 位，含字母和数字）"
            minlength="8"
            maxlength="128"
            autocomplete="new-password"
            :disabled="createBusy"
          />
          <button class="button primary" :disabled="createBusy">
            {{ createBusy ? '正在创建…' : '创建' }}
          </button>
        </div>
        <p v-if="createError" class="error" role="alert">{{ createError }}</p>
        <p v-if="createSuccess" class="success" role="status">{{ createSuccess }}</p>
      </form>

      <p v-if="usersError" class="error" role="alert">{{ usersError }}</p>
      <p v-if="usersLoading" role="status">正在读取账号…</p>

      <ul v-else class="user-list">
        <li v-for="user in users" :key="user.id">
          <div>
            <strong>{{ user.username }}</strong>
            <span class="user-meta">{{ roleText(user.role) }} · {{ statusText(user.status) }}</span>
          </div>
          <button
            v-if="user.id !== me.id"
            class="button secondary"
            :disabled="user.role === 'admin'"
            @click="toggleStatus(user)"
          >
            {{ user.status === 'active' ? '停用' : '启用' }}
          </button>
          <span v-else class="user-meta">当前账号</span>
        </li>
      </ul>

    </section>

    <div class="logout-row">
      <button class="button secondary" @click="emit('logout')">退出登录</button>
    </div>
  </div>
</template>

<style scoped>
.account-stack {
  display: grid;
  gap: 14px;
}
.panel {
  background: #fff;
  border: 1px solid #e4e9e0;
  border-radius: 13px;
  padding: 24px 26px;
}
.panel-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}
.panel-heading h2 {
  font-size: 17px;
  font-weight: 600;
}
.panel-heading p {
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
.account-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 22px;
  margin: 0;
}
.account-facts div {
  padding: 10px 12px;
  background: #f7f9f5;
  border-radius: 8px;
}
.account-facts dt {
  font-size: 11px;
  color: #7d8b81;
}
.account-facts dd {
  margin: 4px 0 0;
  font-size: 13px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #52695c;
  margin-bottom: 12px;
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
input[type='password'] {
  width: 100%;
  padding: 9px 11px;
  border: 1px solid #cddace;
  border-radius: 7px;
  font: inherit;
  font-size: 13px;
}
input[type='password']:focus-visible {
  outline: 2px solid #39735b;
  outline-offset: 1px;
}
.switch-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 11px 12px;
  border: 1px solid #e7ece3;
  border-radius: 9px;
  margin-bottom: 10px;
  cursor: pointer;
}
.switch-row.disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
.switch-row input {
  margin-top: 3px;
  width: 16px;
  height: 16px;
  accent-color: #2f6b4f;
}
.switch-row strong {
  display: block;
  font-size: 13px;
  font-weight: 600;
}
.switch-row small {
  display: block;
  margin-top: 3px;
  font-size: 11px;
  color: #7a877e;
  line-height: 1.6;
}
.error,
.success {
  margin: 10px 0;
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
  margin-top: 12px;
}
.user-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.user-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  padding: 11px 13px;
  border: 1px solid #e7ece3;
  border-radius: 9px;
}
.user-meta {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: #7d8b81;
}
.create-account {
  margin-bottom: 16px;
  padding: 12px 13px;
  border: 1px dashed #d7e2d0;
  border-radius: 9px;
}
.create-account h3 {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}
.create-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
}
.create-row input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #cddace;
  border-radius: 7px;
  font: inherit;
  font-size: 12px;
}
.create-row input:focus-visible {
  outline: 2px solid #39735b;
  outline-offset: 1px;
}
.logout-row {
  display: flex;
  justify-content: flex-end;
}
@media (max-width: 640px) {
  .panel {
    padding: 20px;
  }
  .field-row,
  .account-facts,
  .create-row {
    grid-template-columns: 1fr;
  }
}
</style>

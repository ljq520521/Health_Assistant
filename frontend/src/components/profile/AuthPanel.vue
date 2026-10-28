<script setup>
import { computed, ref } from 'vue'
import { login, registerAccount } from '../../api/profile'

const props = defineProps({ hasAccounts: { type: Boolean, required: true } })
const emit = defineEmits(['authenticated'])

const mode = ref(props.hasAccounts ? 'login' : 'register')
const username = ref('')
const password = ref('')
const confirm = ref('')
const busy = ref(false)
const error = ref('')

const title = computed(() => (props.hasAccounts ? '登录本地账户' : '创建管理员账户'))
const hint = computed(() =>
  props.hasAccounts
    ? '登录后可维护健康档案、健康目标与隐私设置。'
    : '这是本机第一个账户，自动获得管理员权限，之后可创建只读账户。',
)

async function submit() {
  error.value = ''
  if (mode.value === 'register' && password.value !== confirm.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  busy.value = true
  try {
    if (mode.value === 'register') {
      await registerAccount({ username: username.value, password: password.value })
    }
    const result = await login({ username: username.value, password: password.value })
    emit('authenticated', result.user)
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="auth-card" aria-labelledby="auth-title">
    <p class="eyebrow">LOCAL ACCOUNT</p>
    <h2 id="auth-title">{{ title }}</h2>
    <p class="auth-hint">{{ hint }}</p>

    <form class="auth-form" @submit.prevent="submit">
      <label>
        用户名
        <input
          v-model="username"
          name="username"
          autocomplete="username"
          minlength="3"
          maxlength="32"
          pattern="[A-Za-z0-9_]{3,32}"
          placeholder="3–32 位字母、数字或下划线"
          required
          :disabled="busy"
        />
      </label>
      <label>
        密码
        <input
          v-model="password"
          type="password"
          name="password"
          :autocomplete="mode === 'register' ? 'new-password' : 'current-password'"
          minlength="8"
          maxlength="128"
          placeholder="至少 8 位，需包含字母和数字"
          required
          :disabled="busy"
        />
      </label>
      <label v-if="mode === 'register'">
        确认密码
        <input
          v-model="confirm"
          type="password"
          name="confirm"
          autocomplete="new-password"
          minlength="8"
          maxlength="128"
          required
          :disabled="busy"
        />
      </label>

      <p v-if="error" class="auth-error" role="alert">{{ error }}</p>

      <div class="auth-actions">
        <button class="button primary" :disabled="busy">
          {{ busy ? '正在处理…' : mode === 'register' ? '创建账户并登录' : '登录' }}
        </button>
      </div>
    </form>

    <p class="auth-footnote">
      账户仅保存在本机数据库中；密码以加盐哈希存储，不会明文保存。
    </p>
  </section>
</template>

<style scoped>
.auth-card {
  max-width: 520px;
  margin: 34px auto 0;
  padding: 30px 32px;
  background: #fff;
  border: 1px solid #e2e8dd;
  border-radius: 14px;
}
.auth-card h2 {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 8px;
}
.auth-hint {
  font-size: 12px;
  color: #7a877e;
  line-height: 1.8;
  margin-bottom: 20px;
}
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}
label {
  display: flex;
  flex-direction: column;
  gap: 7px;
  font-size: 12px;
  color: #52695c;
}
input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cddace;
  border-radius: 7px;
  font: inherit;
  font-size: 13px;
  color: #273e36;
  background: #fff;
}
input:focus-visible {
  outline: 2px solid #39735b;
  outline-offset: 1px;
}
input:disabled {
  background: #f5f8f4;
}
.auth-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 4px;
}
.auth-error {
  padding: 10px 12px;
  background: #fff0ec;
  color: #983b2d;
  border-radius: 7px;
  font-size: 12px;
}
.auth-footnote {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid #edf0e9;
  font-size: 11px;
  color: #83907d;
}
</style>

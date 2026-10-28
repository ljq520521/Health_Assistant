<script setup>
import { computed, onMounted, ref } from 'vue'
import { modules } from '../data/modules'
import AuthPanel from '../components/profile/AuthPanel.vue'
import ProfileForm from '../components/profile/ProfileForm.vue'
import GoalsPanel from '../components/profile/GoalsPanel.vue'
import AccountPanel from '../components/profile/AccountPanel.vue'
import {
  getMe,
  getProfile,
  getSetup,
  getToken,
  logout,
  setToken,
} from '../api/profile'

const module = modules.find((item) => item.code === 'profile')

const hasAccounts = ref(true)
const me = ref(null)
const profile = ref(null)
const loading = ref(true)
const error = ref('')
const active = ref('profile')
const reloadKey = ref(0)
const consentBlocked = ref(false)

const isAdmin = computed(() => me.value?.role === 'admin')
const canEdit = computed(() => isAdmin.value && !consentBlocked.value)

async function loadProfile() {
  consentBlocked.value = false
  try {
    profile.value = await getProfile()
  } catch (err) {
    if (err.status === 404) {
      profile.value = null
    } else if (err.status === 403) {
      consentBlocked.value = true
      profile.value = null
    } else {
      throw err
    }
  }
}

async function bootstrap() {
  loading.value = true
  error.value = ''
  try {
    hasAccounts.value = (await getSetup()).has_accounts
  } catch (err) {
    error.value = err.message
    loading.value = false
    return
  }

  if (getToken()) {
    try {
      me.value = await getMe()
      await loadProfile()
    } catch (err) {
      if (err.status === 401 || err.status === 403) {
        setToken('')
        me.value = null
      } else {
        error.value = err.message
      }
    }
  }
  loading.value = false
}

async function onAuthenticated(user) {
  me.value = user
  active.value = 'profile'
  error.value = ''
  try {
    await loadProfile()
  } catch (err) {
    error.value = err.message
  }
}

function onProfileSaved(saved) {
  profile.value = saved
  reloadKey.value += 1
}

async function onAccountUpdated(user) {
  me.value = user
  try {
    await loadProfile()
  } catch (err) {
    error.value = err.message
  }
}

function onLogout() {
  logout()
  me.value = null
  profile.value = null
  consentBlocked.value = false
  active.value = 'profile'
  getSetup()
    .then((result) => {
      hasAccounts.value = result.has_accounts
    })
    .catch(() => {})
}

onMounted(bootstrap)
</script>

<template>
  <section v-if="module" class="module-overview" :class="module.color">
    <RouterLink class="back-link" to="/">← 返回总览</RouterLink>

    <div class="page-heading">
      <div class="heading-copy">
        <p class="eyebrow">{{ module.english }}</p>
        <h1>{{ module.name }}</h1>
        <p>{{ module.description }}</p>
      </div>
      <span class="outline-badge">{{ module.owner }} 负责</span>
    </div>

    <p v-if="loading" role="status">正在检查登录状态…</p>

    <div v-else-if="error" class="page-error" role="alert">
      {{ error }}
      <button class="button secondary" @click="bootstrap">重新检查</button>
    </div>

    <AuthPanel
      v-else-if="!me"
      :has-accounts="hasAccounts"
      @authenticated="onAuthenticated"
    />

    <template v-else>
      <div class="profile-tabs" role="group" aria-label="用户与基础功能分区">
        <button
          class="button"
          :class="active === 'profile' ? 'primary' : 'secondary'"
          :aria-pressed="active === 'profile'"
          @click="active = 'profile'"
        >
          健康档案
        </button>
        <button
          class="button"
          :class="active === 'goals' ? 'primary' : 'secondary'"
          :aria-pressed="active === 'goals'"
          @click="active = 'goals'"
        >
          健康目标
        </button>
        <button
          class="button"
          :class="active === 'account' ? 'primary' : 'secondary'"
          :aria-pressed="active === 'account'"
          @click="active = 'account'"
        >
          账户与隐私
        </button>
        <span class="who">{{ me.username }} · {{ isAdmin ? '管理员' : '只读账户' }}</span>
      </div>

      <div v-if="consentBlocked && active !== 'account'" class="consent-panel" role="alert">
        <h2>尚未授权处理健康数据</h2>
        <p>关闭“授权处理健康数据”后，档案与健康目标接口会返回 403。你可以随时在账户设置中重新开启。</p>
        <button class="button primary" @click="active = 'account'">前往账户与隐私</button>
      </div>

      <ProfileForm
        v-else-if="active === 'profile'"
        :profile="profile"
        :can-edit="canEdit"
        @saved="onProfileSaved"
      />

      <GoalsPanel
        v-else-if="active === 'goals'"
        :can-edit="canEdit"
        :reload-key="reloadKey"
      />

      <AccountPanel
        v-else
        :me="me"
        :is-admin="isAdmin"
        @updated="onAccountUpdated"
        @logout="onLogout"
      />
    </template>
  </section>
</template>

<style scoped>
.heading-copy {
  min-width: 0;
  flex: 1;
}
.profile-tabs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 22px;
  padding-bottom: 16px;
  border-bottom: 1px solid #dfe7db;
}
.who {
  margin-left: auto;
  font-size: 11px;
  color: #7d8b81;
}
.page-error {
  padding: 16px;
  background: #fff0ec;
  color: #983b2d;
  border-radius: 9px;
  font-size: 13px;
}
.page-error .button {
  margin-left: 10px;
}
.consent-panel {
  padding: 34px 28px;
  background: #fff;
  border: 1px solid #e4e9e0;
  border-radius: 13px;
}
.consent-panel h2 {
  font-size: 18px;
  margin-bottom: 10px;
}
.consent-panel p {
  font-size: 12px;
  color: #7a877e;
  line-height: 1.8;
  margin-bottom: 18px;
}
@media (max-width: 640px) {
  .who {
    width: 100%;
    margin-left: 0;
  }
}
</style>

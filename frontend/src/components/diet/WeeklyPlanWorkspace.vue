<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import * as api from '../../api/weeklyPlans.js'
import { localParts } from './waterTime.js'
import { buildWeeklyInput, createLatestRequest, createLifecycleRefresh, feedbackChoices, feedbackState, mealLabels, messageText } from './weeklyPlanUI.js'
import WeeklyPlanItems from './WeeklyPlanItems.vue'
import WeeklyPlanStats from './WeeklyPlanStats.vue'

const props = defineProps({ timeZone: { type: String, required: true } })
const tab = ref('generate'), context = ref(null), preview = ref(null), plan = ref(null), plans = ref([]), plansTotal = ref(0)
const loading = ref(false), busy = ref(false), error = ref(''), errorCode = ref(''), errorStatus = ref(0), notice = ref('')
const form = reactive({ start_date: localParts(new Date(), props.timeZone).day, portions: 1, ratios: { breakfast: '', lunch: '', dinner: '' }, selected_goal_ids: [] })
const mapping = reactive({ allergy: [], preference: [], acknowledged: false })
const feedbackDraft = ref(null), feedbackHistory = ref(null), versions = ref(null), confirmation = ref(null), modal = ref(null)
const sequence = createLatestRequest(), detailSequence = createLatestRequest()
let timer = null, lastRefresh = 0, disposed = false, refreshFlight = null, refreshAgain = false, previousFocus = null
const canWrite = computed(() => context.value?.can_write === true)
const canSave = computed(() => canWrite.value && preview.value?.can_save === true && !loading.value && !busy.value)
const allergyRules = computed(() => (context.value?.rules || []).filter(rule => ['allergy', 'forbidden'].includes(rule.rule_type)))
const preferenceRules = computed(() => (context.value?.rules || []).filter(rule => ['like', 'dislike'].includes(rule.rule_type)))
const selectedPlan = computed(() => plans.value.find(item => item.id === plan.value?.id))
const hasDialog = computed(() => !!(feedbackDraft.value || feedbackHistory.value || versions.value || confirmation.value))

function showError(caught) {
  error.value = caught.message || '操作失败，请重试'; errorCode.value = caught.code || ''; errorStatus.value = caught.status || 0
  if ([401, 403].includes(caught.status)) {
    sequence.invalidate(); detailSequence.invalidate(); loading.value = false
    context.value = null; preview.value = null; plan.value = null; plans.value = []; plansTotal.value = 0
    feedbackDraft.value = null; feedbackHistory.value = null; versions.value = null; confirmation.value = null
  }
}
function clearError() { error.value = ''; errorCode.value = ''; errorStatus.value = 0 }
function contextChanged(previous, current) {
  return previous && (previous.profile_fingerprint !== current.profile_fingerprint || previous.rules_fingerprint !== current.rules_fingerprint)
}
function acceptContext(current) {
  if (contextChanged(context.value, current)) {
    mapping.allergy = []; mapping.preference = []; mapping.acknowledged = false
    notice.value = '个人资料或饮食规则已更新，请重新核对文字与结构化规则的对应关系。已保存的计划与反馈仍保留。'
  }
  context.value = current
}
async function performRefresh() {
  const token = sequence.begin()
  loading.value = true; clearError(); lastRefresh = Date.now()
  const conditions = structuredClone({ start_date: form.start_date, portions: form.portions, ratios: { ...form.ratios }, selected_goal_ids: [...form.selected_goal_ids] })
  try {
    const current = await api.getWeeklyContext(conditions.start_date, conditions.selected_goal_ids)
    if (!sequence.current(token) || disposed) return
    acceptContext(current); preview.value = null
    if (current.blockers?.length || (current.confirmation_required && !current.confirmation_valid)) return
    const next = await api.previewWeeklyPlan(buildWeeklyInput(conditions, current.context_hash))
    if (sequence.current(token) && !disposed) preview.value = next
  } catch (caught) { if (sequence.current(token) && !disposed) { preview.value = null; showError(caught) } }
  finally { if (sequence.current(token) && !disposed) loading.value = false }
}
async function refreshPreview() {
  if (refreshFlight) { refreshAgain = true; sequence.invalidate(); return refreshFlight }
  refreshFlight = (async () => {
    do { refreshAgain = false; await performRefresh() } while (refreshAgain && !disposed)
  })()
  try { await refreshFlight } finally { refreshFlight = null }
}
function scheduleRefresh(delay = 350) {
  sequence.invalidate(); clearTimeout(timer); preview.value = null
  if (!form.start_date) { loading.value = false; return }
  timer = setTimeout(refreshPreview, delay)
}
async function loadPlans(more = false) {
  const result = await api.listWeeklyPlans(more ? plans.value.length : 0)
  plans.value = more ? [...plans.value, ...(result.items || [])] : result.items || []
  plansTotal.value = result.total ?? plans.value.length
}
async function loadPlan(id) {
  const token = detailSequence.begin()
  const result = await api.getWeeklyPlan(id)
  if (detailSequence.current(token) && !disposed) plan.value = result
}
async function act(work) {
  if (busy.value) return
  busy.value = true; clearError(); notice.value = ''
  try { await work() } catch (caught) { showError(caught) }
  finally { busy.value = false; lifecycle.resume() }
}
async function refreshVisibleData() {
  if (disposed) return
  scheduleRefresh(0)
  if (plan.value) {
    try { await loadPlan(plan.value.id) } catch (caught) { if (!disposed) showError(caught) }
  }
}
const lifecycle = createLifecycleRefresh({ getLastRefresh: () => lastRefresh, isBusy: () => busy.value, isVisible: () => document.visibilityState === 'visible', refresh: refreshVisibleData })
const lifecycleRefresh = () => lifecycle.request()
async function confirmMapping() {
  await act(async () => {
    await api.confirmWeeklyContext({ profile_fingerprint: context.value.profile_fingerprint, rules_fingerprint: context.value.rules_fingerprint, allergy_rule_ids: [...mapping.allergy], preference_rule_ids: [...mapping.preference] })
    mapping.acknowledged = false
    await refreshPreview()
    notice.value = '已保存本次文字与规则的确认关系；后续资料变化需要重新核对。'
  })
}
async function changeTab(next) {
  tab.value = next
  if (next !== 'generate') await act(async () => { await loadPlans(); if (!plan.value && plans.value.length) await loadPlan(plans.value[0].id) })
}
async function selectPlan(id) { await act(async () => { await loadPlan(Number(id)); versions.value = null; feedbackHistory.value = null }) }
function askSave() { if (canSave.value) confirmation.value = { kind: 'save', context_hash: context.value.context_hash } }
async function commitSave() {
  const approved = confirmation.value
  await act(async () => {
    const current = await api.getWeeklyContext(form.start_date, form.selected_goal_ids)
    if (current.context_hash !== approved.context_hash || current.blockers?.length) {
      confirmation.value = null; acceptContext(current); await refreshPreview()
      throw new Error('资料已变化，已重新生成预览。请核对后再次确认保存。')
    }
    const result = await api.saveWeeklyPlan(buildWeeklyInput(form, current.context_hash))
    confirmation.value = null; await loadPlan(result.id || result.plan_id); await loadPlans(); tab.value = 'daily'
    notice.value = '一周计划已保存。反馈不会自动记入实际饮食摄入。'
  })
}
async function askRefresh() {
  await act(async () => {
    await loadPlan(plan.value.id)
    const input = { expected_context_hash: plan.value.current_context_hash, expected_plan_revision: plan.value.revision }
    const result = await api.previewWeeklyRefresh(plan.value.id, input)
    confirmation.value = { kind: 'refresh', planId: plan.value.id, input, preview: result }
  })
}
async function commitRefresh() {
  const approved = confirmation.value
  await act(async () => {
    await api.refreshWeeklyPlan(approved.planId, approved.input)
    confirmation.value = null; await loadPlan(approved.planId); await loadPlans()
    notice.value = '已刷新允许调整的未来食谱；完成记录、历史版本与反馈保留。'
  })
}
function editFeedback(item) {
  feedbackDraft.value = { item, status: item.feedback?.status || 'pending', note: item.feedback?.note || '', reason: item.feedback?.reason || '' }
}
async function submitFeedback() {
  const draft = feedbackDraft.value
  await act(async () => {
    try {
      await api.saveWeeklyFeedback(draft.item.id, { expected_revision: draft.item.feedback?.revision ?? 0, status: draft.status, note: draft.note, reason: draft.reason })
    } catch (caught) {
      if (caught.status === 409) { await loadPlan(plan.value.id); caught.message += '；已重新读取计划。请关闭反馈窗口，核对最新状态后重新填写。' }
      throw caught
    }
    feedbackDraft.value = null; await loadPlan(plan.value.id); await loadPlans(); notice.value = '反馈已保存，统计已更新。'
  })
}
async function showFeedbackHistory(item) { await act(async () => { feedbackHistory.value = { item, entries: (await api.getWeeklyFeedbackHistory(item.id)).items || [] } }) }
async function showVersions() { await act(async () => { versions.value = (await api.getWeeklyPlanVersions(plan.value.id)).items || [] }) }
function closeDialog() { if (!busy.value) { feedbackDraft.value = null; feedbackHistory.value = null; versions.value = null; confirmation.value = null } }
function trapDialogTab(event) {
  const controls = [...modal.value.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), summary, a[href]')].filter(node => node.getClientRects().length)
  const first = controls[0], last = controls.at(-1)
  if (!first) { event.preventDefault(); modal.value.focus(); return }
  if (event.shiftKey && (document.activeElement === first || document.activeElement === modal.value)) { event.preventDefault(); last.focus() }
  if (!event.shiftKey && (document.activeElement === last || document.activeElement === modal.value)) { event.preventDefault(); first.focus() }
}
watch(hasDialog, async value => {
  if (value) { previousFocus = document.activeElement; await nextTick(); modal.value?.focus() }
  else if (previousFocus?.isConnected) previousFocus.focus()
})
watch(() => [form.start_date, form.portions, ...Object.values(form.ratios), ...form.selected_goal_ids], () => scheduleRefresh())
onMounted(() => { refreshPreview(); window.addEventListener('focus', lifecycleRefresh); document.addEventListener('visibilitychange', lifecycleRefresh) })
onBeforeUnmount(() => { disposed = true; clearTimeout(timer); lifecycle.dispose(); sequence.invalidate(); detailSequence.invalidate(); window.removeEventListener('focus', lifecycleRefresh); document.removeEventListener('visibilitychange', lifecycleRefresh) })
</script>

<template>
  <section class="weekly-workspace" aria-label="一周个性化食谱计划">
    <div class="recipe-heading"><div><h2>把建议变成一周安排</h2><p class="recipe-note">复用已保存的营养目标、库存和禁忌规则。缺少资料时明确提示，不推断医学建议。</p></div><span class="weekly-label">本地规则推荐</span></div>
    <p class="recipe-note weekly-profile-scope"><strong>共享档案说明：</strong>当前为本机共享单档案（profile_id=1），账号角色控制访问权限，不代表多用户档案隔离。</p>
    <nav class="weekly-tabs" aria-label="周计划功能"><button v-for="[key, label] in [['generate','一周食谱'],['daily','每日反馈'],['history','历史计划']]" :key="key" class="btn" :class="{'btn-primary':tab===key}" :aria-pressed="tab===key" :disabled="busy" @click="changeTab(key)">{{ label }}</button></nav>
    <div v-if="error" class="recipe-error" role="alert">{{ error }} <RouterLink v-if="[401,403].includes(errorStatus) || errorCode==='PROFILE_REQUIRED' || errorCode==='DIET_PROFILE_REQUIRED'" to="/profile">前往个人档案检查登录与授权</RouterLink><button class="btn" :disabled="busy || loading" @click="refreshPreview">重新检查资料</button></div>
    <p v-if="notice" class="recipe-notice" role="status">{{ notice }}</p>
    <p v-if="context && !canWrite" class="recipe-notice">当前账号只有查看权限，或尚未完成健康数据授权。保存计划、确认规则与反馈操作不可用；请在个人档案页面核对权限。</p>
    <template v-if="tab==='generate'">
      <form class="recipe-panel" @submit.prevent="refreshPreview"><fieldset :disabled="busy">
        <div class="recipe-grid"><label>计划开始日期<input v-model="form.start_date" type="date" required></label><label>每餐用餐份数<input v-model.number="form.portions" type="number" min="0.0001" max="10000" step="any" required></label></div>
        <details><summary>每餐目标比例（可选，不默认分配）</summary><div class="recipe-grid"><label v-for="(label, meal) in mealLabels" :key="meal">{{ label }}占每日目标（%）<input v-model.number="form.ratios[meal]" type="number" min="0.01" max="100" step="any" placeholder="留空则不参与目标比较"></label></div></details>
        <p class="recipe-note">营养目标读取既有设置，不自动假设热量目标。健康目标文字仅作为你选择的参考依据，不自动转换为营养数值。</p>
        <fieldset v-if="context?.shared_goals?.length" class="weekly-goals"><legend>选择与本次饮食安排有关的健康目标</legend><label v-for="goal in context.shared_goals" :key="goal.id" class="weekly-check"><input v-model="form.selected_goal_ids" type="checkbox" :value="goal.id"><span>{{ goal.title }}<small>{{ goal.current_value ?? '未记录' }} / {{ goal.target_value ?? '未设置' }} {{ goal.unit || '' }}<template v-if="goal.due_date"> · {{ goal.due_date }}</template></small></span></label></fieldset>
        <p v-else class="recipe-note">没有可选的共享健康目标；不会创建默认目标。</p>
        <button class="btn" :disabled="loading">{{ loading ? '正在核对资料和生成预览…' : '重新检查并生成预览' }}</button>
      </fieldset></form>
      <section v-if="context" class="recipe-panel" aria-label="档案与禁忌确认">
        <div class="recipe-heading"><h3>本次使用的个人资料</h3><span class="weekly-label">{{ context.confirmation_valid ? '文字与规则已确认' : '请核对结构化规则' }}</span></div>
        <div class="recipe-grid"><div><strong>档案过敏信息</strong><p class="weekly-raw">{{ context.profile?.allergies || '未填写' }}</p></div><div><strong>档案饮食偏好</strong><p class="weekly-raw">{{ context.profile?.preferences || '未填写' }}</p></div></div>
        <p class="recipe-note">自由文本不能直接作为安全禁忌。请先在“成分与偏好”维护对应的真实规则，再逐项确认。系统不会从文字猜测规则，也不会把课程数据批准当作过敏安全核验。</p>
        <form v-if="context.confirmation_required && !context.confirmation_valid" @submit.prevent="confirmMapping"><fieldset :disabled="busy || !canWrite"><div class="recipe-grid">
          <fieldset><legend>对应的过敏 / 禁用规则</legend><label v-for="rule in allergyRules" :key="rule.id" class="weekly-check"><input v-model="mapping.allergy" type="checkbox" :value="rule.id" :disabled="rule.valid===false"><span>{{ rule.target_name }} · {{ rule.rule_type==='allergy'?'过敏':'禁用' }}{{ rule.valid===false?'（已失效，请维护）':'' }}</span></label><p v-if="!allergyRules.length" class="recipe-note">尚无可用规则，请先维护；不会自动忽略已填写的过敏信息。</p></fieldset>
          <fieldset><legend>对应的喜欢 / 不喜欢规则</legend><label v-for="rule in preferenceRules" :key="rule.id" class="weekly-check"><input v-model="mapping.preference" type="checkbox" :value="rule.id" :disabled="rule.valid===false"><span>{{ rule.target_name }} · {{ rule.rule_type==='like'?'喜欢':'不喜欢' }}{{ rule.valid===false?'（已失效，请维护）':'' }}</span></label><p v-if="!preferenceRules.length" class="recipe-note">尚无偏好规则，请按实际情况维护。</p></fieldset>
        </div><label class="weekly-check"><input v-model="mapping.acknowledged" type="checkbox"><span>我已核对上述文字，并确认选中的实际规则完整对应本次饮食信息；本次确认不代表食物过敏原已全面核验。</span></label><button class="btn btn-primary" :disabled="!mapping.acknowledged">确认文字与规则对应关系</button></fieldset></form>
        <ul v-if="context.blockers?.length" class="recipe-error"><li v-for="(item, i) in context.blockers" :key="i">{{ messageText(item) }}</li></ul>
        <ul v-if="context.warnings?.length" class="recipe-note"><li v-for="(item, i) in context.warnings" :key="i">{{ messageText(item) }}</li></ul>
        <details><summary>当前结构化规则</summary><ul><li v-for="rule in context.rules" :key="rule.id">{{ rule.target_name }} · {{ ({allergy:'过敏',forbidden:'禁用',like:'喜欢',dislike:'不喜欢'})[rule.rule_type] || rule.rule_type }}{{ rule.valid===false?'（已失效）':'' }}</li></ul><p v-if="!context.rules?.length" class="recipe-note">暂无结构化规则。</p></details>
        <details><summary>资料版本与已采用的目标</summary><p class="recipe-note">档案更新时间：{{ context.profile_updated_at || '未提供' }}</p><ul><li v-for="(goal, i) in context.effective_goals" :key="i">{{ goal.title || goal.date || goal.effective_from || '已保存营养目标' }}<span v-if="goal.calories_kcal != null"> · 热量 {{ goal.calories_kcal }} kcal</span><span v-else> · 热量目标未设置</span></li></ul><p v-if="!context.effective_goals?.length" class="recipe-note">未提供有效营养目标。</p></details>
      </section>
      <section v-if="preview" aria-live="polite"><div class="recipe-heading"><h3>7 天食谱预览</h3><button class="btn btn-primary" :disabled="!canSave" @click="askSave">确认并保存本周计划</button></div><p class="recipe-note">当前只是预览。食谱有限时明确标注重复；无候选时保留空餐次。保存后可重新查看和填写反馈。</p><ul v-if="preview.warnings?.length" class="recipe-note"><li v-for="(warning,i) in preview.warnings" :key="i">{{ messageText(warning) }}</li></ul><WeeklyPlanItems :items="preview.items"/></section>
    </template>
    <template v-else>
      <div class="recipe-panel"><label>选择已保存计划<select :value="plan?.id || ''" :disabled="busy" @change="selectPlan($event.target.value)"><option value="" disabled>请选择计划</option><option v-for="item in plans" :key="item.id" :value="item.id">{{ item.start_date }} 开始 · 计划 #{{ item.id }} · 版本 {{ item.revision }}</option></select></label><button v-if="plans.length<plansTotal" class="btn" :disabled="busy" @click="act(()=>loadPlans(true))">加载更早的计划（已加载 {{ plans.length }}/{{ plansTotal }}）</button><p v-if="!plans.length" class="recipe-note">还没有已保存的计划。请先在“一周食谱”生成并确认保存。</p></div>
      <section v-if="plan">
        <div class="recipe-heading"><h3>{{ plan.start_date || selectedPlan?.start_date }} 的一周计划</h3><span class="weekly-label">版本 {{ plan.revision }}</span></div>
        <p v-if="plan.context_changed || plan.hard_changed" class="recipe-notice" role="status">个人资料已更新，建议刷新未来食谱。{{ plan.hard_changed ? '禁忌相关条件已变化，失效候选不能继续作为有效建议。' : '' }}历史计划与已完成反馈保留。</p>
        <ul v-if="plan.blockers?.length" class="recipe-error"><li v-for="(item,i) in plan.blockers" :key="i">{{ messageText(item) }}</li></ul>
        <div class="recipe-row"><button v-if="plan.can_write" class="btn" :disabled="busy" @click="askRefresh">预览未来食谱刷新</button><button class="btn" :disabled="busy" @click="showVersions">查看历史版本</button><button class="btn" :disabled="busy" @click="selectPlan(plan.id)">检查资料与计划状态</button></div>
        <p class="recipe-note">刷新前会展示预览并要求确认。历史日期、已完成事项及已有反馈由服务端保护，不会因新建议消失。</p>
        <WeeklyPlanStats v-if="plan.stats" :stats="plan.stats"/>
        <WeeklyPlanItems :items="plan.items" feedback :can-write="plan.can_write && tab==='daily'" :busy="busy" @feedback="editFeedback" @history="showFeedbackHistory"/>
      </section>
    </template>

    <div v-if="hasDialog" class="weekly-overlay" @keydown.esc="closeDialog" @keydown.tab="trapDialogTab"><section ref="modal" class="weekly-dialog" role="dialog" aria-modal="true" aria-label="周计划确认与详情" tabindex="-1"><button class="btn weekly-close" :disabled="busy" @click="closeDialog">关闭</button>
      <template v-if="confirmation?.kind==='save'"><h3>保存本次一周安排？</h3><p>将保存预览中的 21 个餐次及本次采用的档案版本。不会写入实际摄入记录或扣减库存。</p><button class="btn btn-primary" :disabled="busy || loading" @click="commitSave">确认保存计划</button></template>
      <template v-if="confirmation?.kind==='refresh'"><h3>核对未来食谱刷新</h3><p>以下为刷新预览。确认后才会保存新版本；历史与已完成反馈保留。</p><p>保留 {{ confirmation.preview.preserved_count }} 项 · 刷新 {{ confirmation.preview.refreshed_count }} 项</p><WeeklyPlanItems :items="confirmation.preview.items"/><button class="btn btn-primary" :disabled="busy || confirmation.preview.can_save===false" @click="commitRefresh">确认刷新未来食谱</button></template>
      <form v-if="feedbackDraft" @submit.prevent="submitFeedback"><h3>{{ feedbackDraft.item.date }} · {{ mealLabels[feedbackDraft.item.meal_type] }}反馈</h3><p>{{ feedbackDraft.item.recipe?.name || '无候选餐次' }}</p><fieldset :disabled="busy"><label>执行状态<select v-model="feedbackDraft.status"><option v-for="[key,state] in feedbackChoices(feedbackDraft.item)" :key="key" :value="key">{{ state.icon }} {{ state.label }}</option></select></label><label>原因（可选）<input v-model="feedbackDraft.reason" maxlength="500"></label><label>备注（可选）<textarea v-model="feedbackDraft.note" maxlength="1000" rows="3"></textarea></label><p class="recipe-note">这里只记录执行反馈，不自动记为饮食摄入。部分完成单独统计。</p><button class="btn btn-primary">保存反馈</button></fieldset></form>
      <template v-if="feedbackHistory"><h3>反馈修改历史</h3><p>{{ feedbackHistory.item.date }} · {{ mealLabels[feedbackHistory.item.meal_type] }}</p><ol><li v-for="(entry,i) in feedbackHistory.entries" :key="entry.id || i"><strong>{{ feedbackState(entry.status).icon }} {{ feedbackState(entry.status).label }}</strong> · {{ entry.created_at || entry.updated_at }} · 修订 {{ entry.revision }}<p v-if="entry.reason">原因：{{ entry.reason }}</p><p v-if="entry.note">备注：{{ entry.note }}</p></li></ol><p v-if="!feedbackHistory.entries.length">尚无反馈修改记录。</p></template>
      <template v-if="versions"><h3>历史计划版本</h3><p class="recipe-note">只读保存时的安排和来源；历史建议不代表当前有效建议。</p><details v-for="(version,i) in versions" :key="version.revision || i"><summary>版本 {{ version.revision }} · {{ version.created_at }}</summary><WeeklyPlanItems :items="version.items || version.snapshot?.items || []"/><p v-if="!(version.items || version.snapshot?.items)?.length" class="recipe-note">{{ version.reason || version.change_reason || '此版本没有可展示的餐次快照。' }}</p></details><p v-if="!versions.length">暂无历史版本。</p></template>
      <p v-if="error" class="recipe-error" role="alert">{{ error }}</p>
    </section></div>
  </section>
</template>

<style scoped>
.weekly-workspace{min-width:0}.weekly-tabs{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}.weekly-label{font-size:12px;padding:7px 10px;background:#eaf3eb;color:#356349;border-radius:6px}.weekly-raw{white-space:pre-wrap;line-height:1.7;font-size:14px;overflow-wrap:anywhere}.weekly-workspace strong,.weekly-workspace legend{font-size:14px}.weekly-workspace details{margin:14px 0}.weekly-workspace summary{font-size:13px;min-height:32px;line-height:1.7}.recipe-workspace .weekly-check{display:flex;flex-direction:row;align-items:flex-start;gap:9px;line-height:1.7}.weekly-check input{margin-top:4px;flex-shrink:0;accent-color:#246b58}.weekly-check span{min-width:0;overflow-wrap:anywhere}.weekly-check small{display:block;color:#64796d}.weekly-goals{margin:16px 0}.weekly-overlay{position:fixed;inset:0;background:#173b2866;z-index:60;display:flex;align-items:center;justify-content:center;padding:15px}.weekly-dialog{box-sizing:border-box;width:min(1000px,100%);max-height:90dvh;overflow:auto;background:#fff;border:1px solid #cddace;border-radius:12px;padding:24px;color:#273e36;overflow-wrap:anywhere;outline:0}.weekly-close{display:block;margin-left:auto}.weekly-dialog>h3{margin-top:12px}.weekly-dialog>p{line-height:1.7;font-size:14px}.weekly-dialog textarea{box-sizing:border-box}@media(max-width:390px){.weekly-overlay{padding:8px}.weekly-dialog{padding:14px}.weekly-tabs .btn{padding:9px 12px}}
</style>

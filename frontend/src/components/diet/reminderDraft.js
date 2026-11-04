import { computed, reactive, ref } from 'vue'
const defaults = { enabled:false, mode:'interval', fixed_times:[], interval_minutes:60, active_start:'09:00', active_end:'18:00', pause_when_goal_met:true }
const clone = value => JSON.parse(JSON.stringify(value))
export function normalizeFixedTimes(times) {
  if (!Array.isArray(times) || !times.length) throw Error('请至少添加一个固定提醒时间')
  if (times.some(time => typeof time !== 'string' || !/^([01]\d|2[0-3]):[0-5]\d$/.test(time))) throw Error('请填写合法的固定提醒时间（HH:mm）')
  return [...new Set(times)].sort()
}
// Draft state is deliberately independent from the drinking-record query lifecycle.
export function useReminderDraft(api) {
  const settings = reactive(clone(defaults)), fixedTimes = ref([]), loaded = ref(false), loading = ref(false)
  const baseline = ref(null)
  const snapshot = () => ({ settings:clone(settings), fixedTimes:clone(fixedTimes.value) })
  const hasDuplicates = computed(() => new Set(fixedTimes.value.filter(Boolean)).size !== fixedTimes.value.filter(Boolean).length)
  const dirty = computed(() => loaded.value && JSON.stringify(snapshot()) !== JSON.stringify(baseline.value))
  function accept(value) {
    for (const key of Object.keys(defaults)) settings[key] = clone(value[key])
    fixedTimes.value = [...value.fixed_times]
    baseline.value = snapshot(); loaded.value = true
  }
  async function load() { loading.value = true; try { accept(await api.get()) } finally { loading.value = false } }
  function cancel() { if (baseline.value) { Object.assign(settings, clone(baseline.value.settings)); fixedTimes.value = clone(baseline.value.fixedTimes) } }
  async function save() {
    const value = { ...clone(settings), fixed_times:settings.mode === 'fixed_times' ? normalizeFixedTimes(fixedTimes.value) : [], interval_minutes:Number(settings.interval_minutes) }
    // Rejection leaves the draft intact. The caller disables editing while saving.
    accept(await api.save(value))
  }
  return { settings, fixedTimes, hasDuplicates, loaded, loading, dirty, load, save, cancel }
}

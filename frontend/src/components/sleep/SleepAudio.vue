<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { apiBase, json, request } from '../../api/sleep'
import SleepDialog from './SleepDialog.vue'
import { SoundPlayer } from './audio'

const items = ref([]), error = ref(''), busy = ref(false), active = ref(null), filter = ref('all')
const volume = ref(0.3), timer = ref(30), remaining = ref(0), editor = ref(false), deleting = ref(null)
const form = reactive({ title: '', category: 'meditation', url: '', mode: 'upload', file: null, id: null, favorite: false })
const shown = computed(() => items.value.filter(item => filter.value === 'all' || (filter.value === 'favorite' ? item.favorite : item.category === filter.value)))
let stopAt = 0
const player = new SoundPlayer(message => { active.value = null; stopAt = 0; if (message) error.value = message })
async function load() { try { items.value = (await request('/sleep/content')).items } catch (e) { error.value = e.message } }
function stop() { player.stop(); active.value = null; stopAt = 0; remaining.value = 0 }
function resetTimer() { stopAt = active.value && Number(timer.value) ? Date.now() + Number(timer.value) * 60000 : 0; remaining.value = Number(timer.value) * 60 }
async function play(item) {
  if (active.value?.id === item.id) { stop(); return }
  busy.value = true; error.value = ''
  try {
    await player.play(item, item.source_type === 'upload' ? `${apiBase}${item.source}` : item.source)
    active.value = item; resetTimer()
  } catch (e) { stop(); error.value = e.message || '音频播放失败' } finally { busy.value = false }
}
async function favorite(item) {
  error.value = ''
  try { await request(`/sleep/content/${item.id}`, json('PUT', { title: item.title, category: item.category, favorite: !item.favorite })); await load() }
  catch (e) { error.value = e.message }
}
function edit(item = null) {
  Object.assign(form, { title: item?.title || '', category: item?.category || 'meditation', url: '', mode: 'upload', file: null, id: item?.id || null, favorite: item?.favorite || false })
  error.value = ''; editor.value = true
}
async function save() {
  busy.value = true; error.value = ''
  try {
    if (form.id) await request(`/sleep/content/${form.id}`, json('PUT', { title: form.title, category: form.category, favorite: form.favorite }))
    else if (form.mode === 'url') await request('/sleep/content', json('POST', { title: form.title, category: form.category, url: form.url }))
    else {
      if (!form.file) throw new Error('请选择音频文件')
      if (form.file.size > 20 * 1024 * 1024) throw new Error('音频不能超过 20 MB')
      const extension = form.file.name.split('.').pop().toLowerCase()
      const media = { mp3: 'audio/mpeg', wav: 'audio/wav', ogg: 'audio/ogg', m4a: 'audio/mp4' }[extension]
      if (!media) throw new Error('请选择 MP3、WAV、OGG 或 M4A 文件')
      await request(`/sleep/content/upload?${new URLSearchParams({ title: form.title, category: form.category })}`, { method: 'POST', body: form.file, headers: { 'Content-Type': media } })
    }
    editor.value = false; await load()
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function remove() {
  busy.value = true; error.value = ''
  try { await request(`/sleep/content/${deleting.value.id}`, { method: 'DELETE' }); if (active.value?.id === deleting.value.id) stop(); deleting.value = null; await load() }
  catch (e) { error.value = e.message } finally { busy.value = false }
}
const ticker = setInterval(() => { if (stopAt) { remaining.value = Math.max(0, Math.ceil((stopAt - Date.now()) / 1000)); if (!remaining.value) stop() } }, 1000)
onMounted(load)
onUnmounted(() => { clearInterval(ticker); player.dispose() })
</script>

<template>
  <section class="sleep-panel"><div class="sleep-section-title"><div><h2>给夜晚一点留白</h2><p>白噪音与冥想音景 · 也可以添加自己的音频</p></div><button class="button primary" @click="edit()">＋ 添加音频</button></div>
    <div class="sleep-audio-toolbar"><div class="sleep-segment"><button v-for="option in [['all','全部'],['noise','白噪音'],['meditation','冥想'],['favorite','收藏']]" :key="option[0]" :class="{ active: filter === option[0] }" @click="filter = option[0]">{{ option[1] }}</button></div><label>定时停止<select v-model="timer" @change="resetTimer"><option :value="0">持续播放</option><option v-for="value in [5,15,30,60]" :key="value" :value="value">{{ value }} 分钟</option></select></label></div>
    <p v-if="error && !editor && !deleting" class="sleep-error" role="alert">{{ error }}</p><div v-if="!shown.length" class="sleep-empty">此分类还没有音频。添加一段喜欢的声音吧。</div>
    <div class="sleep-audio-grid"><article v-for="item in shown" :key="item.id" class="sleep-audio-card" :class="{ playing: active?.id === item.id }"><div class="sleep-audio-art" :class="item.category"><span>{{ item.category === 'noise' ? '≋' : '☾' }}</span><button class="sleep-favorite" :aria-label="`${item.favorite ? '取消收藏' : '收藏'} ${item.title}`" :aria-pressed="item.favorite" @click="favorite(item)">{{ item.favorite ? '★' : '☆' }}</button></div><div class="sleep-audio-body"><h3>{{ item.title }}</h3><p>{{ item.source_type === 'generated' ? '内置循环音景' : item.source_type === 'upload' ? '本地音频' : '外部音频链接' }}</p><div class="sleep-actions"><button class="button secondary" :disabled="busy" @click="play(item)">{{ active?.id === item.id ? '■ 停止' : '▶ 播放' }}</button><button class="sleep-text-button" :aria-label="`编辑 ${item.title}`" @click="edit(item)">编辑</button><button class="sleep-text-button" :aria-label="`删除 ${item.title}`" @click="deleting = item; error = ''">删除</button></div></div></article></div>
    <div class="sleep-player"><div><strong>{{ active ? `正在播放：${active.title}` : '选一段声音，慢慢放松。' }}</strong><p>{{ active && stopAt ? `${Math.ceil(remaining / 60)} 分钟后停止` : '离开此模块会停止播放' }}</p></div><label>音量<input v-model="volume" type="range" min="0" max="1" step="0.01" @input="player.setVolume(volume)" /></label><button v-if="active" class="button secondary" @click="stop">停止播放</button></div>
  </section>
  <SleepDialog v-if="editor" :title="form.id ? '编辑音频' : '添加助眠音频'" :busy="busy" @close="editor = false"><form class="sleep-form" @submit.prevent="save"><label>标题<input v-model="form.title" required maxlength="100" /></label><label>分类<select v-model="form.category"><option value="noise">白噪音</option><option value="meditation">冥想</option></select></label><template v-if="!form.id"><label>来源<select v-model="form.mode"><option value="upload">上传本地文件</option><option value="url">音频直链</option></select></label><label v-if="form.mode === 'upload'">音频文件（最多 20 MB）<input type="file" accept=".mp3,.wav,.ogg,.m4a" required @change="form.file = $event.target.files[0]" /></label><label v-else>HTTP / HTTPS 音频直链<input v-model="form.url" type="url" required placeholder="https://example.com/meditation.mp3" /></label><p class="sleep-muted">外部链接由浏览器直接播放，需链接可访问且指向音频文件。</p></template><p v-if="error" class="sleep-error" role="alert">{{ error }}</p><div class="sleep-form-footer"><button type="button" class="button secondary" :disabled="busy" @click="editor = false">取消</button><button class="button primary" :disabled="busy">{{ busy ? '保存中…' : '保存音频' }}</button></div></form></SleepDialog>
  <SleepDialog v-if="deleting" title="删除这段音频？" :busy="busy" @close="deleting = null"><p>{{ deleting.title }} 将从音频库移除，上传的文件也将删除。</p><p v-if="error" class="sleep-error" role="alert">{{ error }}</p><div class="sleep-form-footer"><button class="button secondary" :disabled="busy" @click="deleting = null">取消</button><button class="button sleep-danger" :disabled="busy" @click="remove">确认删除</button></div></SleepDialog>
</template>

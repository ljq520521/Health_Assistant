<script setup>
import { onMounted,onBeforeUnmount,reactive,ref,watch } from 'vue'
import { listWater,saveWater,deleteWater,waterSummary,getWaterReminder,saveWaterReminder } from '../../api/water.js'
import { getGoals,saveGoals } from '../../api/nutrition.js'
import {measurement,percentText} from './metricPresentation.js'
import { useReminderDraft } from './reminderDraft.js'
import { timeZoneLabel,dateTimeText } from './displayTime.js'
import { localInput,localParts,toUTC } from './waterTime.js'
const props=defineProps({timeZone:{type:String,required:true}}),emit=defineEmits(['changed'])
const today=()=>localParts(new Date(),props.timeZone).day
const filters=reactive({date_from:today(),date_to:today()})
const records=ref([]),summary=ref(null),loading=ref(false),busy=ref(false),error=ref(''),code=ref(''),success=ref(''),recordDialog=ref(null),editId=ref(null)
const form=reactive({drank_at:'',amount_ml:'',notes:''})
const deleteDialog=ref(null),pendingDelete=ref(null),goalLoading=ref(false),goalLoaded=ref(false)
const goals=reactive({effective_from:today(),water_ml:''})
const draft=useReminderDraft({get:getWaterReminder,save:saveWaterReminder})
const {settings,fixedTimes,hasDuplicates,loaded:reminderLoaded,loading:reminderLoading,dirty:reminderDirty}=draft
const reminderError=ref(''),permission=ref(typeof Notification==='undefined'?'unsupported':Notification.permission)
async function loadReminder(){reminderError.value='';try{await draft.load()}catch(err){reminderError.value=err.message}}
const leaveDialog=ref(null);let resolveLeave
function confirmLeave(){if(busy.value)return false;if(!reminderDirty.value)return true;return new Promise(resolve=>{resolveLeave=resolve;leaveDialog.value.showModal()})}
function finishLeave(leave){leaveDialog.value?.close();resolveLeave?.(leave);resolveLeave=null}
function beforeUnload(event){if(reminderDirty.value){event.preventDefault();event.returnValue=''}}
watch(reminderDirty,value=>{if(value)window.addEventListener('beforeunload',beforeUnload);else window.removeEventListener('beforeunload',beforeUnload)})
const format=value=>new Intl.NumberFormat('zh-CN',{maximumFractionDigits:2}).format(value)
let version=0,goalVersion=0,alive=true,dayTimer
function failure(err){error.value=err.message;code.value=err.code||''}
async function refresh(){
  if(filters.date_from&&filters.date_to&&filters.date_from>filters.date_to){error.value='开始日期不能晚于结束日期';return}
  const token=++version;loading.value=true;error.value='';code.value=''
  try{
    const [rows,total]=await Promise.all([listWater({...filters}),waterSummary(today())])
    if(token!==version)return
    records.value=rows.items;summary.value=total
  }catch(err){if(token===version)failure(err)}finally{if(token===version)loading.value=false}
}
async function loadGoal(){const token=++goalVersion;goalLoading.value=true;goalLoaded.value=false;try{const result=await getGoals(goals.effective_from);if(token===goalVersion){goals.water_ml=result.goal?.water_ml??'';goalLoaded.value=true}}catch(err){if(token===goalVersion)failure(err)}finally{if(token===goalVersion)goalLoading.value=false}}
function open(row=null){
  editId.value=row?.id??null
  Object.assign(form,{drank_at:localInput(row?new Date(row.drank_at):new Date(),props.timeZone),amount_ml:row?.amount_ml??'',notes:row?.notes??''})
  error.value='';recordDialog.value.showModal()
}
async function action(work,message){
  if(busy.value)return
  busy.value=true;error.value='';success.value=''
  try{await work();success.value=message;await refresh();emit('changed')}catch(err){failure(err)}finally{busy.value=false}
}
async function submit(){
  const amount=Number(form.amount_ml)
  if(!Number.isInteger(amount)||amount<=0||amount>1000000){error.value='饮水量必须是 1～1000000 的整数（ml）';return}
  await action(async()=>{await saveWater({drank_at:toUTC(form.drank_at,props.timeZone),amount_ml:amount,notes:form.notes},editId.value);recordDialog.value.close()},'饮水记录已保存')
}
function remove(row){pendingDelete.value=row;deleteDialog.value.showModal()}
async function confirmDelete(){await action(async()=>{await deleteWater(pendingDelete.value.id);deleteDialog.value.close();pendingDelete.value=null},'饮水记录已删除')}
async function saveGoal(){
  if(goalLoading.value||!goalLoaded.value)return
  const value=goals.water_ml===''?null:Number(goals.water_ml)
  if(value!==null&&(!Number.isFinite(value)||value<=0)){error.value='饮水目标必须为正数，或留空表示未设置';return}
  await action(()=>saveGoals({effective_from:goals.effective_from,water_ml:value}),'饮水目标已保存，其他营养目标保留')
}
async function saveReminder(){
  if(!reminderLoaded.value)return
  await action(()=>draft.save(),'提醒设置已保存')
}
function cancelReminder(){draft.cancel();error.value='';success.value='已取消修改，恢复为已保存的提醒设置'}
async function requestPermission(){
  if(!window.Notification){permission.value='unsupported';return}
  // Only this explicit user action may open the browser permission prompt.
  if(Notification.permission==='default'){
    try{permission.value=await Notification.requestPermission()}catch{permission.value='unavailable'}
  }else permission.value=Notification.permission
}
async function updateDay(){if(alive&&document.visibilityState==='visible'&&summary.value?.date!==today())try{summary.value=await waterSummary(today())}catch(err){failure(err)}}
onMounted(async()=>{dayTimer=setInterval(updateDay,30000);document.addEventListener('visibilitychange',updateDay);await Promise.all([refresh(),loadReminder()]);if(alive&&!error.value)await loadGoal()})
onBeforeUnmount(()=>{resolveLeave?.(false);alive=false;++version;++goalVersion;clearInterval(dayTimer);document.removeEventListener('visibilitychange',updateDay);window.removeEventListener('beforeunload',beforeUnload)})
defineExpose({open,confirmLeave})
</script>
<template><section class="water-panel">
  <div class="heading"><div><h2>饮水管理</h2><p>记录饮水，按自己的计划提醒。时间按 {{ timeZoneLabel(timeZone) }} 显示。</p></div><button class="button primary" :disabled="loading||busy||!summary" @click="open()">新增饮水记录</button></div>
  <p v-if="success" class="notice" role="status">{{ success }}</p><div v-if="error&&!recordDialog?.open" class="notice error" role="alert">{{ error }} <RouterLink v-if="code==='PROFILE_REQUIRED'" to="/profile">前往建立档案</RouterLink> <button class="button secondary" @click="refresh">重试</button></div>
  <p v-if="loading" role="status">正在加载饮水记录…</p>
  <template v-if="summary"><div class="cards"><article class="panel"><h3>今日已记录饮水量</h3><strong>{{ summary.data_status==='no_records'?'当天没有记录':measurement(summary.total_ml,'ml') }}</strong><p>{{ summary.date }} · {{ summary.record_count }} 条记录</p><p v-if="summary.data_status==='no_records'">今日暂无饮水记录，不代表实际没有饮水。</p><template v-if="summary.target_ml!==null"><p>今日目标 {{ format(summary.target_ml) }} ml · 达成率 {{ summary.data_status==='no_records'?'当天没有记录，暂不展示比例':percentText(summary.achievement_percent) }}</p><progress v-if="summary.data_status!=='no_records'" :value="summary.progress_percent" max="100" aria-label="今日饮水目标进度" /><p>按已记录饮水量计算，达成率可超过100%。</p></template><p v-else>尚未设置饮水目标，可在右侧设置。</p></article>
  <form class="panel" @submit.prevent="saveGoal"><h3>每日饮水目标</h3><label>生效日期<input type="date" required v-model="goals.effective_from" @change="loadGoal" :disabled="busy" /></label><label>饮水目标（ml，可留空）<input type="number" min="0.0001" step="any" v-model="goals.water_ml" :disabled="busy||goalLoading||!goalLoaded" /></label><p>从所选日期起生效，直到下一目标版本；修改过去日期会影响对应历史进度。其他营养目标保持不变。</p><button class="button primary" :disabled="busy||goalLoading||!goalLoaded">保存饮水目标</button></form></div>
  <p class="filter-hint">日期筛选仅影响下方饮水记录列表，上方始终显示今日进度。</p>
  <form class="panel filters" @submit.prevent="refresh"><label>饮水开始日期<input type="date" v-model="filters.date_from" :disabled="loading" /></label><label>饮水结束日期<input type="date" v-model="filters.date_to" :disabled="loading" /></label><button class="button primary" :disabled="loading">查询饮水记录</button><button type="button" class="button secondary" :disabled="loading" @click="filters.date_from='';filters.date_to='';refresh()">查看全部饮水</button></form>
  <div class="panel table-wrap"><h3>饮水记录</h3><p v-if="!records.length">所选范围暂无饮水记录。</p><table v-else class="desktop-water"><thead><tr><th>饮水时间</th><th>饮水量</th><th>备注</th><th>操作</th></tr></thead><tbody><tr v-for="row in records" :key="row.id"><td>{{ dateTimeText(row.drank_at,timeZone) }}</td><td>{{ format(row.amount_ml) }} ml</td><td class="notes">{{ row.notes||'—' }}</td><td><div class="actions"><button class="button secondary" :disabled="busy" @click="open(row)">编辑</button><button class="button secondary" :disabled="busy" @click="remove(row)">删除</button></div></td></tr></tbody></table><div v-if="records.length" class="mobile-water"><article v-for="row in records" :key="row.id" class="water-record-card"><h4>{{ dateTimeText(row.drank_at,timeZone) }}</h4><strong>{{measurement(row.amount_ml,'ml')}}</strong><p>{{row.notes||'未填写备注'}}</p><div class="actions"><button class="button secondary" :disabled="busy" :aria-label="'编辑饮水记录 '+row.id" @click="open(row)">编辑</button><button class="button secondary" :disabled="busy" :aria-label="'删除饮水记录 '+row.id" @click="remove(row)">删除</button></div></article></div></div>
  <form class="panel reminder-settings" @submit.prevent="saveReminder"><h3>饮水提醒设置</h3><p class="draft-warning">关闭或刷新浏览器时，未保存的提醒设置可能丢失，请先保存。</p><p v-if="reminderDirty" role="status" class="notice">有未保存更改；查询饮水记录不会清空这些修改。</p><p v-if="reminderLoading" role="status">正在加载提醒设置…</p><p v-if="reminderError" role="alert" class="notice error">{{reminderError}} <button type="button" class="button secondary" @click="loadReminder">重新加载提醒设置</button></p><fieldset :disabled="busy||reminderLoading||!reminderLoaded"><label class="check"><input type="checkbox" v-model="settings.enabled" :disabled="busy" />开启页面内提醒</label><div class="filters"><label>提醒模式<select v-model="settings.mode" :disabled="busy"><option value="interval">间隔提醒</option><option value="fixed_times">固定时间提醒</option></select></label><label>每日开始时间<input type="time" required v-model="settings.active_start" :disabled="busy" /></label><label>每日结束时间<input type="time" required v-model="settings.active_end" :disabled="busy" /></label><label v-if="settings.mode==='interval'">间隔（分钟）<input type="number" min="1" max="1440" step="1" required v-model="settings.interval_minutes" :disabled="busy" /></label></div><section v-if="settings.mode==='fixed_times'" class="fixed-times" aria-label="固定提醒时间"><h4>固定提醒时间</h4><p>按 HH:mm 填写，每个时间只提醒一次。保存时自动按时间排序并合并重复项。</p><p v-if="!fixedTimes.length" role="status">请添加至少一个提醒时间。</p><div v-for="(time,index) in fixedTimes" :key="index" class="fixed-time-row"><label>提醒时间 {{index+1}}<input type="time" step="60" required v-model="fixedTimes[index]" :min="settings.active_start" :max="settings.active_end" /></label><button type="button" class="button secondary" :aria-label="'删除提醒时间 '+(index+1)" @click="fixedTimes.splice(index,1)">删除</button></div><p v-if="hasDuplicates" role="status" class="notice">存在重复时间，保存时将合并为一项，不会重复提醒。</p><button type="button" class="button secondary" @click="fixedTimes.push('')">添加提醒时间</button></section><label class="check"><input type="checkbox" v-model="settings.pause_when_goal_met" :disabled="busy" />达到已记录饮水目标后暂停提醒</label><button class="button primary" :disabled="busy||!reminderLoaded">保存提醒设置</button><button type="button" class="button secondary" :disabled="busy||!reminderDirty" @click="cancelReminder">取消修改</button></fieldset><p>提醒只在饮食页面内运行，切换页签仍有效。离开页面或关闭浏览器后停止；后台标签页及系统休眠可能延迟提醒，错过的时间不会集中补发。间隔从每日开始时间起算，不支持跨午夜。</p><div class="actions"><button type="button" class="button secondary" :disabled="permission!=='default'" @click="requestPermission">申请浏览器通知权限</button><span>{{ {default:'尚未授权',granted:'已允许浏览器通知',denied:'通知权限已拒绝，页面内提醒仍可用',unsupported:'浏览器不支持通知，页面内提醒仍可用',unavailable:'无法申请通知权限，页面内提醒仍可用'}[permission] }}</span></div><p>通知授权仅在点击按钮后申请。去重标识保存在当前浏览器；清除网站数据后会重置。稍后提醒延后10分钟，仍受每日窗口和目标暂停设置限制。</p></form>
  </template>
  <dialog ref="recordDialog" @cancel="busy&&$event.preventDefault()"><form @submit.prevent="submit"><h3>{{ editId?'编辑饮水记录':'新增饮水记录' }}</h3><p v-if="error" role="alert" class="notice error">{{ error }}</p><label>饮水时间（{{ timeZoneLabel(timeZone) }}）<input type="datetime-local" required v-model="form.drank_at" :disabled="busy" /></label><label>饮水量（ml）<input type="number" min="1" max="1000000" step="1" required v-model="form.amount_ml" :disabled="busy" /></label><label>备注<textarea maxlength="2000" rows="3" v-model="form.notes" :disabled="busy" /></label><div class="actions"><button class="button primary" :disabled="busy">{{ busy?'正在保存…':'保存饮水记录' }}</button><button type="button" class="button secondary" :disabled="busy" @click="recordDialog.close()">取消</button></div></form></dialog>
<dialog ref="leaveDialog" aria-labelledby="reminder-leave-title" @cancel.prevent="finishLeave(false)"><h3 id="reminder-leave-title">有未保存的提醒设置</h3><p>离开将放弃这些更改，不会自动保存。</p><div class="actions"><button class="button secondary" @click="finishLeave(false)">继续编辑</button><button class="button primary" @click="finishLeave(true)">放弃修改并离开</button></div></dialog>
<dialog ref="deleteDialog" aria-labelledby="water-delete-title" @cancel="busy&&$event.preventDefault()"><h3 id="water-delete-title">确认删除饮水记录</h3><p>将删除这条 {{ pendingDelete?.amount_ml }} ml 饮水记录。</p><p v-if="error" role="alert" class="notice error">{{ error }}</p><div class="actions"><button class="button secondary" :disabled="busy" @click="deleteDialog.close()">取消删除</button><button class="button primary" :disabled="busy" @click="confirmDelete">确认删除</button></div></dialog>
</section></template>
<style scoped>
.panel p.draft-warning{padding:12px;border-left:4px solid #b8862b;border-radius:6px;background:#fff4df;color:#79521c;font-weight:600}

.filter-hint{font-size:13px;line-height:1.7;color:#64796d;margin-bottom:12px}.fixed-times{margin:16px 0;padding:14px;border:1px solid #dfe8df;border-radius:10px}.fixed-time-row{display:flex;align-items:flex-end;gap:10px;margin-bottom:12px}.fixed-time-row label{flex:1;min-width:0;margin:0}.fixed-time-row .button{min-height:44px;flex-shrink:0}.fixed-times input{width:100%;box-sizing:border-box}

.mobile-water{display:none}.water-record-card{padding:16px 0;border-bottom:1px solid #dfe8df;overflow-wrap:anywhere}.water-record-card h4{font-size:14px;margin-bottom:10px}.water-record-card strong{color:#246b58;font-size:20px}.water-record-card .actions .button{min-height:44px;flex:1}@media(max-width:650px){.desktop-water{display:none}.mobile-water{display:block}}
fieldset{border:0;padding:0;min-width:0}.heading,.actions,.filters{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.heading{justify-content:space-between;margin-bottom:18px}.heading h2{font-size:23px}.heading p,.panel p{font-size:13px;line-height:1.7;color:#64796d;margin:10px 0}.panel{background:white;border:1px solid #dfe8df;border-radius:12px;padding:22px;margin-bottom:18px}.cards{display:grid;grid-template-columns:1fr 1fr;gap:18px}.cards strong{display:block;font-size:32px;color:#246b58;margin:22px 0}.cards small{font-size:15px}h3{margin-bottom:14px}label{display:flex;flex-direction:column;gap:7px;font-size:13px;margin:12px 0}input,select,textarea{font:inherit;color:inherit;border:1px solid #cddace;border-radius:7px;padding:10px;max-width:100%;min-width:0}progress{width:100%;accent-color:#246b58;height:16px}.filters{align-items:flex-end}.check{flex-direction:row;align-items:center}.notice{background:#edf5ef;padding:14px;border-radius:8px;margin:12px 0}.error{background:#fff0ec;color:#a04431}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px;min-width:540px}th,td{text-align:left;padding:12px;border-bottom:1px solid #e4ece5}.notes{max-width:260px;overflow-wrap:anywhere;white-space:pre-wrap}dialog{border:1px solid #cddace;border-radius:14px;padding:26px;width:min(480px,calc(100% - 32px));max-height:90vh;overflow:auto;margin:auto}dialog::backdrop{background:#16392a66}.actions span{font-size:12px}@media(max-width:650px){.cards{grid-template-columns:1fr;gap:0}.panel{padding:16px}.filters label{width:100%}.heading .button{width:100%}dialog{padding:18px}}
</style>

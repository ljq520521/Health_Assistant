<script setup>
import { onMounted,onBeforeUnmount,ref } from 'vue'
import { getWaterReminder,waterSummary } from '../../api/water.js'
import { getToken } from '../../api/profile.js'
import { localParts } from './waterTime.js'
import { takeReminder,notifyIfAllowed,snoozeReminder,clearSnooze,startReminderChecks } from './waterReminder.js'
const props=defineProps({timeZone:{type:String,required:true}}),emit=defineEmits(['record'])
const notice=ref(false),error=ref('')
let stopped=false,busy=false,stop=()=>{}
async function check(){
  if(stopped||busy||document.visibilityState!=='visible'||!getToken())return
  busy=true
  try {
    const settings=await getWaterReminder()
    if(stopped)return
    if(!settings.enabled){notice.value=false;clearSnooze(localStorage);error.value='';return}
    const now=new Date(),day=localParts(now,props.timeZone).day
    const summary=settings.pause_when_goal_met?await waterSummary(day):null
    if(stopped||document.visibilityState!=='visible')return
    if(settings.pause_when_goal_met&&summary.goal_met)notice.value=false
    const claim=()=>{
      if(stopped)return
      const due=takeReminder(settings,summary,new Date(),props.timeZone,localStorage)
      if(due){notice.value=true;notifyIfAllowed(window.Notification,'可以记录一次饮水。提醒不会自动新增记录。')}
    }
    if(navigator.locks)await navigator.locks.request('diet-water-reminder',claim)
    else claim()
    error.value=''
  } catch(err){if(!stopped && !['PROFILE_REQUIRED','WATER_MIGRATION_REQUIRED'].includes(err.code))error.value='提醒暂不可用：'+err.message}
  finally{busy=false}
}
function snooze(){try{snoozeReminder(new Date(),props.timeZone,localStorage);notice.value=false}catch{error.value='无法保存稍后提醒，请检查浏览器本地存储权限'}}
function record(){notice.value=false;emit('record')}
onMounted(()=>{stop=startReminderChecks(check,{document,setInterval,clearInterval})})
onBeforeUnmount(()=>{stopped=true;stop();notice.value=false})
defineExpose({check})
</script>
<template><aside v-if="notice" class="water-reminder" role="status" aria-live="polite"><div><strong>饮水提醒</strong><p>可以记录一次饮水；请按自己的需要安排。</p></div><div class="actions"><button class="button primary" @click="record">去记录</button><button class="button secondary" @click="snooze">稍后提醒（10分钟）</button><button class="button secondary" @click="notice=false">关闭</button></div></aside><p v-if="error" role="status" class="error">{{ error }}</p></template>
<style scoped>.water-reminder{padding:18px;border:1px solid #7cab92;border-radius:12px;background:#edf7ef;margin-bottom:20px;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}.water-reminder p{font-size:13px;margin-top:8px}.actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.error{color:#a04431;font-size:13px;margin:12px 0}</style>

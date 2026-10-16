<script setup>
import { reactive, ref } from 'vue'
import { getGoals, getGoalHistory, saveGoals } from '../../api/nutrition.js'
const props=defineProps({timeZone:{type:String,required:true}})
const emit=defineEmits(['saved'])
const dialog=ref(null), date=ref(''), busy=ref(false), loading=ref(false), error=ref(''), history=ref([]), base=ref({})
const loaded=ref(false)
const form=reactive({calories_kcal:'',protein_g:'',fat_g:'',carbohydrate_g:''})
const fields=[['calories_kcal','热量','kcal'],['protein_g','蛋白质','g'],['fat_g','脂肪','g'],['carbohydrate_g','碳水化合物','g']]
let version=0
async function load(){
  if(!date.value)return
  const token=++version; loading.value=true;loaded.value=false;error.value=''
  try{const response=await getGoals(date.value);if(token!==version)return;const goal=response.goal;for(const [key] of fields)form[key]=goal?.[key]??'';base.value={...form};loaded.value=true}
  catch(err){if(token===version)error.value=err.message}
  finally{if(token===version)loading.value=false}
}
async function open(){date.value=new Intl.DateTimeFormat('en-CA',{timeZone:props.timeZone,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());history.value=[];dialog.value.showModal();await load();try{history.value=(await getGoalHistory()).items}catch(err){error.value=err.message}}
function close(){if(!busy.value){++version;dialog.value.close()}}
async function save(){
  if(loading.value||busy.value||!loaded.value)return
  error.value='';const payload={effective_from:date.value}
  for(const [key,label] of fields){const value=form[key]===''?null:Number(form[key]);if(value!==null&&(!Number.isFinite(value)||value<=0)){error.value=`${label}目标必须为正数，未设置请留空`;return}const previous=base.value[key]===''?null:Number(base.value[key]);if(value!==previous)payload[key]=value}
  if(Object.keys(payload).length===1){error.value='尚未修改任何目标';return}
  busy.value=true
  try{await saveGoals(payload);dialog.value.close();emit('saved')}
  catch(err){error.value=err.message}finally{busy.value=false}
}
defineExpose({open})
</script>
<template><dialog ref="dialog" aria-labelledby="goal-title" @cancel="busy&&$event.preventDefault()"><form @submit.prevent="save">
  <h2 id="goal-title">设置每日营养目标</h2><p>目标由你自行设置；不会按身体信息推算。修改从生效日期起影响统计，直到下一个目标版本。</p>
  <label>生效日期<input type="date" v-model="date" required :disabled="busy||loading" @change="load" /></label>
  <p v-if="loading" role="status">正在读取该日目标…</p>
  <fieldset :disabled="busy||loading"><label v-for="[key,label,unit] in fields" :key="key">{{ label }}目标（{{ unit }}/日）<input type="number" step="any" min="0" v-model="form[key]" placeholder="未设置请留空" /></label></fieldset>
  <p>只保存你修改的项目；清空表示取消该项目标。其他营养目标与预留饮水目标保持不变。</p>
  <details><summary>目标版本历史（{{ history.length }}）</summary><ul><li v-for="goal in history" :key="goal.id"><button type="button" :disabled="busy||loading" @click="date=goal.effective_from;load()">{{ goal.effective_from }} 起生效</button></li></ul></details>
  <p v-if="error" class="error" role="alert">{{ error }}</p><div class="actions"><button type="button" class="button secondary" :disabled="busy" @click="close">取消</button><button class="button primary" :disabled="busy||loading||!loaded">{{ busy?'正在保存…':'保存目标' }}</button></div>
</form></dialog></template>
<style scoped>dialog{width:min(550px,calc(100% - 32px));max-height:90vh;overflow:auto;padding:24px;border:1px solid #dbe5d6;border-radius:14px;color:#273e36}dialog::backdrop{background:#18372b66}h2{font-size:21px}p{font-size:12px;line-height:1.7;margin:12px 0;color:#61776a}label{display:flex;flex-direction:column;gap:7px;font-size:13px}input{width:100%;padding:10px;border:1px solid #cddace;border-radius:7px;font:inherit}fieldset{border:0;padding:16px 0;display:grid;grid-template-columns:1fr 1fr;gap:14px}.actions{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}.error{color:#a04431;background:#fff0ec;padding:10px}li{padding:5px}li button{border:0;background:#edf4ef;color:#246b58;padding:6px}@media(max-width:600px){fieldset{grid-template-columns:1fr}}</style>

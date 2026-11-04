<script setup>
import {timeZoneLabel,dateTimeText} from './displayTime.js'
import {computed,onMounted,onBeforeUnmount,ref} from 'vue'
import {getReport} from '../../api/reports.js'
import {localParts} from './waterTime.js'
import {metrics,periodLabels,statuses,format,compact,chartsFor,overviewLines} from './reportPresentation.js'
import {reportCopy,demoReportNotice} from './reportCopy.js'
import {intakeText,goalText,ratioText,waterMetric,completenessText} from './metricPresentation.js'
import {useReportDownloads,attemptDownload,DOWNLOAD_NOTICE} from './reportDownloads.js'
import ReportChart from './ReportChart.vue'
const props=defineProps({timeZone:{type:String,required:true},demo:{type:Object,default:null}})
const period=ref('day'),date=ref(localParts(new Date(),props.timeZone).day),data=ref(null),loading=ref(false),exporting=ref(false),error=ref(''),code=ref(''),notice=ref('')
const charts=computed(()=>data.value?chartsFor(data.value):[]),dirty=computed(()=>data.value&&(data.value.period!==period.value||data.value.selected_date!==date.value))
const copy=computed(()=>data.value?reportCopy(data.value):null),demoNotice=computed(()=>demoReportNotice(props.demo))
const downloads=useReportDownloads(),downloadFiles=downloads.files
let requestId=0,alive=true
async function load(){const id=++requestId;loading.value=true;error.value='';code.value='';notice.value='';data.value=null;try{const result=await getReport(period.value,date.value);if(alive&&id===requestId)data.value=result}catch(e){if(alive&&id===requestId){error.value=e.message;code.value=e.code||''}}finally{if(alive&&id===requestId)loading.value=false}}
async function exportFile(chart=null){
  if(!data.value||exporting.value)return
  exporting.value=true;error.value='';notice.value=''
  const snapshot=data.value
  try{
    const exporter=await import('./reportExport.js')
    if(!alive)return
    const file=chart ? await exporter.exportChartPNG(snapshot,chart,{demo:props.demo}) : await exporter.exportReportPDF(snapshot,{demo:props.demo})
    if(!alive)return
    const entry=downloads.replace(chart?'png':'pdf',file)
    const requested=attemptDownload(entry)
    notice.value=DOWNLOAD_NOTICE+(requested?'。':'；自动下载未能发起，请点击下方“下载文件”重试。')
  }catch(e){if(alive)error.value='文件生成失败：'+e.message}
  finally{if(alive)exporting.value=false}
}
onMounted(load);onBeforeUnmount(()=>{alive=false;requestId++;downloads.dispose()})
</script>
<template><section class="diet-report">
<div class="report-heading"><div><h2>饮食报告</h2><p>汇总已录入数据，了解记录情况与自设目标。</p></div><button class="button primary" :disabled="!data||loading||exporting" @click="exportFile()">{{exporting?'正在生成…':'导出当前报告 PDF'}}</button></div>
<form class="report-filter" @submit.prevent="load"><label>报告周期<select v-model="period" :disabled="loading||exporting"><option v-for="(label,key) in periodLabels" :key="key" :value="key">{{label}}</option></select></label><label>报告日期<input v-model="date" type="date" required :max="localParts(new Date(),timeZone).day" :disabled="loading||exporting"></label><button class="button primary" :disabled="loading||exporting">生成报告</button></form>
<p class="report-note">周一至周日为一周，月报按自然月；当前周期截至今天。PDF 使用设备中文字体绘制为高清图片，文字不可选中搜索；不会向服务器上传导出内容。</p>
<p v-if="loading" role="status">正在读取报告…</p><div v-if="error" class="report-error" role="alert">{{error}} <RouterLink v-if="code==='PROFILE_REQUIRED'" to="/profile">前往建档</RouterLink></div><p v-if="notice" role="status" class="report-notice">{{notice}}</p>
<section v-if="downloadFiles.pdf||downloadFiles.png" class="report-downloads" aria-label="已生成文件">
  <h3>已生成文件</h3>
  <p class="report-note">以下链接对应生成时的数据快照，文件名包含日期范围。可重复下载；更改查询条件不会更新这些文件，请重新导出。同类文件再次生成成功或离开报告页签后，旧链接会释放。</p>
  <div v-for="file in [downloadFiles.pdf,downloadFiles.png].filter(Boolean)" :key="file.kind" class="download-item">
    <span>{{file.name}}</span>
    <a class="button secondary" :href="file.url" :download="file.name" :aria-label="'下载文件 '+file.kind.toUpperCase()+'：'+file.name" @click="notice=DOWNLOAD_NOTICE+'。'">下载文件（{{file.kind.toUpperCase()}}）</a>
  </div>
</section>
<article v-if="data" class="report-body"><p v-if="demoNotice" class="report-notice">{{demoNotice}}；此标记也会加入PDF和PNG导出。</p>
<div class="report-heading"><div><h3>{{periodLabels[data.period]}} · {{data.date_from}} 至 {{data.date_to}}</h3><p class="report-note">{{timeZoneLabel(data.time_zone)}} · 统计 {{data.period_days}} 天 · 自然周期 {{data.period_from}} 至 {{data.period_to}}</p></div><span v-if="data.is_partial_period" class="report-badge">部分周期 / 当前周期进行中</span></div>
<p v-if="dirty" class="report-notice">条件已改变，请点击“生成报告”刷新。导出使用当前显示的报告及日期范围。</p>
<p v-if="!data.overview.record_count&&!data.water.record_count" class="report-notice">此区间暂无饮食和饮水记录，不代表实际没有摄入。仍可查看自设目标与数据完整性提示。</p>
<div class="report-cards"><div class="report-card"><h4>已记录饮食</h4><strong>{{data.overview.record_count}} 条</strong><p>有记录 {{data.overview.recorded_days}} 天 / {{data.period_days}} 天</p><p>按日期餐次去重 {{data.overview.recorded_meal_slots}} 个时段</p></div><div class="report-card" v-for="[key,label,unit] in metrics" :key="key"><h4>{{label}}已知累计</h4><strong>{{intakeText(data.nutrition.total.nutrients[key],unit,data.period_days)}}</strong><p>{{completenessText(data.nutrition.total.nutrients[key],data.period_days)}}</p><p>已知 {{data.nutrition.total.nutrients[key].known_count}} 条 · 未知 {{data.nutrition.total.nutrients[key].unknown_count}} 条</p></div><div class="report-card"><h4>已记录饮水累计</h4><strong>{{intakeText(waterMetric(data.water),'ml',data.period_days)}}</strong><p>{{data.water.record_count}} 条 · 有记录 {{data.water.recorded_days}} 天</p><p>{{completenessText(data.water,data.period_days)}}</p></div></div>
<section class="report-section"><h3>已知热量平均值</h3><p>{{overviewLines(data)[2]}}</p><p>{{overviewLines(data)[3]}}</p><p class="report-note">{{data.averages.note}}</p></section>
<section class="report-section"><h3>营养目标与饮水目标</h3><div class="report-cards"><div v-for="[key,label,unit] in metrics" :key="key" class="report-goal"><h4>{{label}}</h4><p>区间目标 {{goalText(data.nutrition.total.nutrients[key],unit,data.period_days)}}</p><p>已知记录 / 自设目标：{{ratioText(data.nutrition.total.nutrients[key],data.period_days)}}</p><progress v-if="data.nutrition.total.nutrients[key].achievement_percent!=null" :value="Math.min(100,data.nutrition.total.nutrients[key].achievement_percent)" max="100" :aria-label="label+'记录目标比例'"></progress><p class="report-note">{{data.nutrition.total.nutrients[key].target_missing_days}} 天未设置目标；{{completenessText(data.nutrition.total.nutrients[key],data.period_days)}}。比例允许超过100%，不用于健康判断。</p></div><div class="report-goal"><h4>饮水</h4><p>区间目标 {{goalText(waterMetric(data.water),'ml',data.period_days)}}</p><p>已记录量 / 自设目标：{{ratioText(waterMetric(data.water),data.period_days)}}</p><progress v-if="data.water.achievement_percent!=null" :value="Math.min(100,data.water.achievement_percent)" max="100" aria-label="饮水记录目标比例"></progress><p class="report-note">{{data.water.target_missing_days}} 天未设置目标；{{data.water.missing_days}} 天无记录。不推断实际饮水不足。</p></div></div></section>
<section class="report-section"><h3>每日趋势与餐次分布</h3><div class="report-charts"><div v-for="chart in charts" :key="chart.id" class="report-chart-card"><ReportChart :chart="chart"/><button class="button secondary" :disabled="exporting||loading" @click="exportFile(chart)">导出{{chart.title}} PNG</button></div></div></section>
<section class="report-section"><h3>饮食分析建议</h3><p class="report-note">以下为记录规则提示，不是医学诊断。</p><ul><li v-for="(s,index) in data.suggestions" :key="s.rule_id"><p>{{copy.suggestions[index].text}}</p><details><summary>查看依据</summary><ul><li v-for="(line,i) in copy.suggestions[index].evidence" :key="i">{{line}}</li></ul></details><details><summary>开发调试信息（规则与原始依据）</summary><p>规则编号：{{s.rule_id}}</p><pre>{{JSON.stringify(s.evidence,null,2)}}</pre></details></li></ul></section>
<section class="report-section"><h3>数据完整性说明</h3><ul><li v-for="note in copy.notes" :key="note">{{note}}</li></ul></section>
<details class="report-section"><summary>查看每日数据与目标明细</summary><div class="report-table"><table><thead><tr><th>日期</th><th>饮食记录</th><th v-for="[,label,unit] in metrics" :key="label">{{label}}（{{unit}}）<br>已知 / 目标 / 比例</th><th>饮水（ml）<br>已记录 / 目标 / 比例</th></tr></thead><tbody><tr v-for="(d,index) in data.nutrition.daily" :key="d.actual_from"><th>{{d.actual_from}}</th><td>{{d.record_count}} 条</td><td v-for="[key,,unit] in metrics" :key="key">{{intakeText(d.nutrients[key],unit)}} / {{goalText(d.nutrients[key],unit)}} / {{ratioText(d.nutrients[key])}}<small>{{statuses[d.nutrients[key].data_status]}}</small></td><td>{{intakeText(waterMetric(data.water.daily[index]),'ml')}} / {{goalText(waterMetric(data.water.daily[index]),'ml')}} / {{ratioText(waterMetric(data.water.daily[index]))}}<small>{{statuses[data.water.daily[index].data_status]}}；目标生效 {{data.water.daily[index].goal_effective_from||'未设置'}}</small></td></tr></tbody></table></div></details>
<p class="report-note">生成时间：{{dateTimeText(data.generated_at,data.time_zone)}}（{{timeZoneLabel(data.time_zone)}}）。导出基于此刻显示的报告数据。</p><details class="report-section"><summary>开发调试信息（报告版本与原始说明）</summary><p>{{data.generated_at}} · {{data.schema_version}}</p><pre>{{JSON.stringify(data.completeness_notes,null,2)}}</pre></details>
</article></section></template>
<style scoped>
.report-downloads{padding:16px;border:1px solid #cddbcf;border-radius:10px;background:#f0f6f0;margin:16px 0}.report-downloads h3{font-size:16px}.download-item{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:10px 0}.download-item span{font-size:13px;min-width:0;overflow-wrap:anywhere;flex:1 1 240px}.download-item a{min-height:44px;max-width:100%;white-space:normal}

.diet-report{color:#294638}.report-heading{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:18px}.report-heading h2{font-size:25px}.report-heading h3{font-size:19px}.report-heading p{font-size:13px;color:#61776b;margin-top:8px}.report-filter{display:flex;gap:14px;align-items:end;flex-wrap:wrap;margin:16px 0}.report-filter label{display:grid;gap:8px;font-size:13px}.report-filter input,.report-filter select{padding:10px;border:1px solid #cddbcf;border-radius:7px;background:white;color:inherit;font:inherit}.report-section{background:white;border:1px solid #e0e8df;border-radius:12px;padding:20px;margin:18px 0;line-height:1.7}.report-section h3{font-size:18px;margin-bottom:12px}.report-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.report-card{padding:18px;border-radius:12px;background:white;border:1px solid #e0e8df;min-width:0}.report-card h4,.report-goal h4{font-size:14px;margin:0 0 10px}.report-card strong{font-size:22px;color:#246b58;overflow-wrap:anywhere}.report-card p,.report-goal p{font-size:12px;color:#61776b;margin-top:8px}.report-goal{padding:12px;background:#f4f8f2;border-radius:8px}.report-charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.report-chart-card{min-width:0;border:1px solid #e5ece3;border-radius:9px;padding:8px}.report-chart-card .button{margin:8px;font-size:12px}.report-note{font-size:12px;line-height:1.7;color:#61776b;margin:10px 0}.report-notice,.report-error{padding:14px;border-radius:8px;background:#fff4df;line-height:1.7;margin:12px 0}.report-error{background:#fff0ec;color:#9b3c29}.report-badge{background:#fff0d1;padding:8px;border-radius:6px;font-size:12px}.report-section li{margin:10px 0}.report-section pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.report-section summary{cursor:pointer}.report-table{overflow:auto;margin-top:15px}table{width:100%;min-width:850px;border-collapse:collapse;font-size:12px}td,th{padding:12px;text-align:left;border-bottom:1px solid #e5ece3}small{display:block;color:#6e7f73;margin-top:6px}progress{width:100%;height:10px;accent-color:#246b58}@media(max-width:700px){.report-charts{grid-template-columns:1fr}.report-section{padding:14px}.report-filter label{width:100%}.report-cards{grid-template-columns:1fr}}
</style>

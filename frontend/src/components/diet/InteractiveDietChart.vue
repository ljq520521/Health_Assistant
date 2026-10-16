<script setup>
import {computed,onMounted,onBeforeUnmount,ref,watch} from 'vue'
import {chartGeometry,pointDescription,shortDate} from './chartPresentation.js'
import {numberText} from './metricPresentation.js'
const props=defineProps({chart:{type:Object,required:true}})
const host=ref(null),width=ref(320),selected=ref(null)
const graph=computed(()=>chartGeometry(props.chart,width.value))
const current=computed(()=>selected.value===null?null:graph.value.points[selected.value])
watch(()=>props.chart,()=>{selected.value=null})
let observer
onMounted(()=>{observer=new ResizeObserver(entries=>{width.value=entries[0].contentRect.width});observer.observe(host.value)})
onBeforeUnmount(()=>observer?.disconnect())
</script>
<template><figure ref="host" class="interactive-chart">
  <figcaption>{{chart.title}}（{{chart.unit}}）</figcaption>
  <svg :viewBox="`0 0 ${graph.width} 225`" height="225" role="group" :aria-label="chart.title+'，可点击数据点查看详情'">
    <g v-for="tick in graph.ticks" :key="tick.value"><line :x1="graph.left" :x2="graph.right" :y1="tick.y" :y2="tick.y" stroke="#dfe9e1"/><text :x="graph.left-8" :y="tick.y+4" text-anchor="end">{{numberText(tick.value)}}</text></g>
    <template v-if="chart.kind==='line'">
      <polyline v-for="(segment,i) in graph.segments" :key="i" :points="segment.map(p=>`${p.x},${p.y}`).join(' ')" fill="none" stroke="#246b58" stroke-width="2"/>
      <g v-for="p in graph.points" :key="p.label" role="button" tabindex="0" :aria-label="pointDescription(p,chart.unit)" :aria-pressed="selected===p.index" @click="selected=p.index" @keydown.enter.prevent="selected=p.index" @keydown.space.prevent="selected=p.index">
        <circle :cx="p.x" :cy="p.y??graph.bottom" r="12" fill="transparent"/>
        <circle :cx="p.x" :cy="p.y??graph.bottom" :r="selected===p.index?6:4" :fill="p.value==null?'white':p.status==='partial'?'#ac701b':'#246b58'" :stroke="p.value==null?'#7b8980':'white'" stroke-width="2"/>
        <title>{{pointDescription(p,chart.unit)}}</title>
      </g>
      <text :x="graph.left" y="212">{{shortDate(graph.points[0]?.label||'')}}</text><text v-if="graph.points.length>1" :x="graph.right" y="212" text-anchor="end">{{shortDate(graph.points.at(-1)?.label||'')}}</text>
    </template>
    <template v-else><g v-for="p in graph.points" :key="p.label" role="button" tabindex="0" :aria-label="pointDescription(p,chart.unit)" @click="selected=p.index" @keydown.enter.prevent="selected=p.index" @keydown.space.prevent="selected=p.index"><rect :x="p.x-12" :y="p.y??graph.bottom" width="24" :height="p.y==null?0:graph.bottom-p.y" fill="#3d846e" rx="3"/><rect :x="p.x-16" y="30" width="32" height="155" fill="transparent"/><text :x="p.x" :y="(p.y??graph.bottom)-8" text-anchor="middle">{{numberText(p.value)}}</text><text :x="p.x" y="212" text-anchor="middle">{{p.label}}</text></g></template>
    <text v-if="chart.points.every(p=>p.value==null)" :x="graph.width/2" y="110" text-anchor="middle">暂无可绘制的已知数据</text>
  </svg>
  <p v-if="chart.kind==='line'" class="legend"><span class="known-dot">●</span> 绿色：已知数据　<span class="partial-dot">●</span> 橙色：数据不完整　○ 空心：未知或无记录（不是0）</p>
  <label>查看{{chart.title}}数据<select v-model="selected"><option :value="null">点击图中数据点，或选择日期 / 类别</option><option v-for="p in graph.points" :key="p.label" :value="p.index">{{p.label}}</option></select></label>
  <p class="point-detail" role="status">{{current?pointDescription(current,chart.unit):'尚未选择数据点；可触屏点击或使用上方选择框查看。'}}</p>
  <p class="chart-note">{{chart.note}}</p>
</figure></template>
<style scoped>
.known-dot{color:#246b58}.partial-dot{color:#ac701b}.interactive-chart{margin:0;min-width:0}figcaption{font-size:14px;font-weight:600;color:#246b58;line-height:1.6}svg{width:100%;height:225px;display:block}svg text{font-size:12px;fill:#536e60}svg g[role=button]{cursor:pointer}svg g[role=button]:focus{outline:2px solid #b77a22}.legend,.chart-note{font-size:12px;line-height:1.7;color:#61776b;margin:8px 0}label{display:grid;gap:8px;font-size:13px}select{width:100%;min-width:0;padding:10px;border:1px solid #cddace;border-radius:7px;background:white;font:inherit;color:inherit}.point-detail{font-size:14px;line-height:1.7;padding:12px;background:#edf5ef;border-radius:8px;overflow-wrap:anywhere;margin:10px 0}
</style>

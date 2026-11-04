<script setup>
import {computed} from 'vue'
import InteractiveDietChart from './InteractiveDietChart.vue'
const props=defineProps({daily:{type:Array,required:true},metric:{type:String,required:true},label:{type:String,required:true},unit:{type:String,required:true}})
const chart=computed(()=>({id:props.metric,title:`每日${props.label}已知摄入趋势`,unit:props.unit,kind:'line',points:props.daily.map(d=>({label:d.actual_from,value:d.nutrients[props.metric].known_sum,status:d.nutrients[props.metric].data_status})),note:'趋势始终展示每日数据；未知或无记录处断线，真实0保留在零刻度。'}))
</script>
<template><InteractiveDietChart :chart="chart"/></template>

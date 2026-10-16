<script setup>
import {nutritionFields} from './recipeUI.js'
import {measurement} from './metricPresentation.js'
defineProps({data:{type:Object,required:true}})
</script>
<template><dl class="recipe-nutrition"><div v-for="[k,label,unit] in nutritionFields" :key="k"><dt>{{label}}</dt><dd>{{measurement(data[k].total,unit)}}<small v-if="!data[k].complete">数据不完整；已知部分 {{measurement(data[k].known_sum,unit)}}，未知 {{data[k].unknown_count}} 项</small></dd></div></dl></template>
<style scoped>.recipe-nutrition{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:12px 0}dt{font-size:12px;color:#62796d}dd{overflow-wrap:anywhere;margin:6px 0;color:#246b58}small{display:block;font-size:12px;color:#85632b;margin-top:6px;line-height:1.5}</style>

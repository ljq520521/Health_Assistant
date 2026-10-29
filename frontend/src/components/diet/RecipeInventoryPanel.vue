<script setup>
import PublicFoodPicker from './PublicFoodPicker.vue'
import { ref,onMounted } from 'vue'
import { recipeRequest as request,writeRecipeResource as save,removeRecipeResource as remove } from '../../api/recipes'
import { useRecipeAction } from './recipeUI'
const {busy,error,success,run}=useRecipeAction()
const items=ref([]),foods=ref([]),editing=ref(null),pending=ref(null)
const form=ref({food_id:'',quantity_g:0,notes:''})
async function load(){const [a,b]=await Promise.all([request('/inventory-items'),request('/foods')]);items.value=a.items;foods.value=b.items}
function reset(){editing.value=null;form.value={food_id:'',quantity_g:0,notes:''}}
function edit(r){editing.value=r.id;form.value={food_id:r.food_id,quantity_g:r.quantity_g,notes:r.notes,revision:r.revision}}
async function submit(){await run(async()=>{await save('/inventory-items',form.value,editing.value);reset();await load()},'库存已保存')}
async function confirmDelete(){await run(async()=>{await remove('/inventory-items',pending.value.id);pending.value=null;reset();await load()},'库存条目已删除')}
onMounted(()=>run(load))
</script>
<template><section>
<h2>食材库存</h2><p class="recipe-note">统一以克记录可用量。未登记库存时不参与库存评分；登记部分库存后，其余所需食材视为暂无可用库存。推荐不会自动扣减库存。</p>
<p v-if="error" role="alert" class="recipe-error">{{error}}</p><p v-if="success" role="status">{{success}}</p><p v-if="busy">正在处理…</p>
<PublicFoodPicker @selected="f => { if (!foods.some(x => x.id === f.id)) foods.push(f); form.food_id=f.id }"/><form class="recipe-panel" @submit.prevent="submit"><fieldset :disabled="busy"><h3>{{editing?'编辑库存':'登记库存'}}</h3><div class="recipe-row">
<label>食物<select v-model="form.food_id" required><option disabled value="">选择食物库食物</option><option v-for="f in foods" :key="f.id" :value="f.id">{{f.name}}</option></select></label>
<label>可用重量（g）<input v-model.number="form.quantity_g" type="number" min="0" max="1000000000" step="any" required></label><label>备注<input v-model="form.notes" maxlength="1000"></label>
<button class="btn btn-primary" type="submit">保存库存</button><button v-if="editing" class="btn" type="button" @click="reset">取消编辑</button></div></fieldset></form>
<p v-if="!busy&&!items.length">尚未登记库存。</p><article v-for="i in items" :key="i.id" class="recipe-panel"><h3>{{i.food_name}} <span v-if="i.food_archived_at">（食物已归档）</span></h3><p>{{i.quantity_g}} g · {{i.notes||'无备注'}}</p><div class="recipe-row"><button class="btn" :disabled="busy||!!i.food_archived_at" @click="edit(i)">编辑</button><button class="btn" :disabled="busy" @click="pending=i">删除</button></div></article>
<div v-if="pending" role="alertdialog" aria-label="确认删除库存" class="recipe-notice">确定删除 {{pending.food_name}} 的库存条目？<button class="btn" :disabled="busy" @click="confirmDelete">确认删除</button><button class="btn" :disabled="busy" @click="pending=null">取消</button></div>
</section></template>

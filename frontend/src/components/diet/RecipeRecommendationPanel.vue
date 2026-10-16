<script setup>
import { ref,onMounted,computed } from 'vue'
import { recipeRequest,previewRecipes } from '../../api/recipes.js'
import { useRecipeAction,nutritionFields,displayNumber,preparationText } from './recipeUI.js'
import { localParts } from './waterTime.js'
import RecipeNutrition from './RecipeNutrition.vue'
import {measurement,percentText,percentInText} from './metricPresentation.js'
import RecipeSource from './RecipeSource.vue'
const props=defineProps({timeZone:{type:String,required:true}})
const {busy,error,code,run}=useRecipeAction()
const categories=ref([]),result=ref(null)
const form=ref({date:localParts(new Date(),props.timeZone).day,portions:1,ratio:'',category_id:'',minutes:'',include_examples:false})
const dimensionNames={nutrition:'营养匹配',inventory:'库存匹配',preference:'偏好匹配'}
const statusNames={target_unset:'目标未设置',ratio_unset:'未设置目标占比',target_not_computable:'目标太小，无法计算',nutrition_unknown:'营养未知，未参与此项评分',computed:'已计算'}
function payload(){return {date:form.value.date,portions:form.value.portions,target_ratio:form.value.ratio===''?null:form.value.ratio/100,category_id:form.value.category_id||null,max_preparation_minutes:form.value.minutes===''?null:form.value.minutes,include_examples:form.value.include_examples,limit:10}}
const changed=computed(()=>result.value&&JSON.stringify(payload())!==JSON.stringify(result.value.conditions))
const percent=value=>value==null?'未计算':percentText(value*100)
const quantity=value=>value>0&&value<.01?'< 0.01':displayNumber(value)
async function load(){await run(async()=>{categories.value=(await recipeRequest('/recipe-categories')).items})}
async function submit(){result.value=null;await run(async()=>{result.value=await previewRecipes(payload())})}
onMounted(load)
</script>
<template><section aria-label="本地食谱推荐">
<div class="recipe-heading"><div><h2>为这一餐寻找食谱</h2><p class="recipe-note">根据已保存食谱、库存和个人规则，在本地筛选与排序。</p></div><span class="recipe-badge">本地规则推荐</span></div>
<p class="recipe-notice">推荐分用于产品排序，不是医学健康评分。请按实际食物标签核对配料与交叉接触信息，推荐不能保证绝对过敏安全。</p>
<form class="recipe-panel" @submit.prevent="submit"><fieldset :disabled="busy"><div class="recipe-grid">
<label>推荐日期<input v-model="form.date" type="date" required></label>
<label>用餐份数<input v-model.number="form.portions" type="number" min="0.0001" max="10000" step="any" required></label>
<label>本次占每日目标（%，可留空）<input v-model.number="form.ratio" type="number" min="0.01" max="100" step="any" placeholder="由你设置，不默认分配"></label>
<label>食谱分类<select v-model="form.category_id"><option value="">全部分类</option><option v-for="c in categories" :key="c.id" :value="c.id">{{c.name}}</option></select></label>
<label>最长制作时间（分钟，可留空）<input v-model.number="form.minutes" type="number" min="0" max="100000" step="1" placeholder="不限制"></label>
<label class="recipe-check"><input v-model="form.include_examples" type="checkbox">包含示例食谱（仅用于演示）</label>
</div><p class="recipe-note">比较的是所选份数的总营养与“当日目标 × 占比”；不自动按人数放大个人目标，也不扣除已记录摄入。目标请在“营养摄入分析”中设置。制作时间未知的食谱不会通过时间上限筛选。</p><button class="btn btn-primary" type="submit">{{busy?'正在筛选…':'获取推荐'}}</button></fieldset></form>
<div v-if="error" class="recipe-error" role="alert">{{error}} <RouterLink v-if="code==='PROFILE_REQUIRED'" to="/profile">前往建档</RouterLink><button class="btn" :disabled="busy" @click="load">重新加载分类</button></div>
<p v-if="!result&&!busy&&!error" class="recipe-note">设置条件后点击“获取推荐”。没有库存或偏好时，对应维度不会参与评分。</p>
<section v-if="result" aria-live="polite">
<p v-if="changed" class="recipe-notice">条件已修改，下方仍为上次查询结果；请重新获取推荐。</p>
<p class="recipe-note">查询日期 {{result.conditions.date}} · {{result.conditions.portions}} 份 · 每日目标占比 {{percent(result.conditions.target_ratio)}} · 目标生效日 {{result.goal?.effective_from||'尚未设置'}} · 符合条件 {{result.eligible_count}} 道，最多展示 10 道</p>
<ul class="recipe-notice"><li v-for="w in result.warnings" :key="w">{{w}}</li></ul>
<div v-if="!result.items.length" class="recipe-panel"><h3>暂无符合条件的食谱</h3><p>{{result.excluded.length?'请查看下方排除原因，调整筛选条件或完善食材资料。禁忌过滤不会因高分而跳过。':'食谱库中没有有效食谱，请先在食谱库创建食谱。'}}</p></div>
<article v-for="item in result.items" :key="item.recipe.id" class="recipe-panel recommendation-card">
<div class="recipe-heading"><div><h3>{{item.recipe.name}}</h3><p class="recipe-note">{{item.portions}} 份 · {{preparationText(item.recipe.preparation_minutes)}} <span v-if="item.recipe.is_example" class="recipe-badge">示例数据</span></p></div><div class="ranking-score"><span>{{item.score==null?'暂无评分':displayNumber(item.score)}}</span><small>推荐排序分 / 100</small></div></div>
<p class="brief-reason">{{Object.keys(dimensionNames).filter(k=>item.scores[k]!=null).length ? '本次依据'+Object.keys(dimensionNames).filter(k=>item.scores[k]!=null).map(k=>dimensionNames[k]).join('、')+'排序。' : '当前条件不足，暂无可参与评分的维度。'}}</p>
<RecipeNutrition :data="item.nutrition"/>
<p v-if="!item.composition_verified" class="recipe-notice">部分成分/过敏原信息未知、不完整或核对已过期，食用前请核对实际配料。</p>
<p v-if="item.nutrition_completeness<1" class="recipe-notice">营养数据完整度 {{percent(item.nutrition_completeness)}}；统计数据不完整，未知不等于0，也不表示营养不足。</p>
<p class="shortage-summary">{{item.ingredients.some(i=>i.registered)?'按已登记库存：'+item.ingredients.filter(i=>i.shortage_g>0).length+'种食材还缺少用量。':'尚未登记本食谱食材的可用库存；缺料按系统已登记信息估算。'}}</p>
<details class="ingredient-details"><summary>查看所需食材与缺料（{{item.ingredients.length}}种）</summary><ul class="ingredient-list"><li v-for="i in item.ingredients" :key="i.food_id"><strong>{{i.name}}</strong><dl><div><dt>需要</dt><dd>{{quantity(i.required_g)}} g</dd></div><div><dt>已有</dt><dd>{{i.registered?quantity(i.available_g)+' g':'未登记'}}</dd></div><div :class="{'shortage':i.shortage_g>0}"><dt>还缺</dt><dd>{{quantity(i.shortage_g)}} g</dd></div></dl></li></ul></details>
<details class="score-details"><summary>评分如何计算</summary>
<p class="recipe-note">推荐分仅用于排序，不是健康评分。</p>
<div class="score-grid"><div v-for="(label,key) in dimensionNames" :key="key"><span>{{label}}</span><strong>{{item.scores[key]==null?'未参与':displayNumber(item.scores[key])+' 分'}}</strong><small>实际权重 {{percent(item.weights[key])}}</small></div></div>
<p class="recipe-note">加权基础分 {{item.base_score==null?'未计算':displayNumber(item.base_score)}} · 数据完整性独立扣分 {{displayNumber(item.data_penalty)}}。相同排序分按缺料种类数、食谱 ID 排序。</p>
<p class="recipe-note">营养数据完整度 {{percent(item.nutrition_completeness)}}；目标相关完整度 {{percent(item.target_nutrition_completeness)}}。字段齐全不代表资料经过权威验证。</p>
<ul><li v-for="reason in item.reasons" :key="reason">{{percentInText(reason)}}</li></ul>
<ul><li v-for="[key,label,unit] in nutritionFields" :key="key">{{label}}：{{measurement(item.metrics[key].actual,unit)}} / 本次目标 {{measurement(item.metrics[key].target,unit,statusNames[item.metrics[key].status]||'目标未设置')}} · {{statusNames[item.metrics[key].status]}}<span v-if="item.metrics[key].score!=null"> · {{displayNumber(item.metrics[key].score)}} 分</span></li></ul>
</details>
<details><summary>制作步骤与来源</summary><ol><li v-for="(step,index) in item.recipe.steps" :key="index">{{step}}</li></ol><RecipeSource :recipe="item.recipe"/></details>
</article>
<details v-if="result.excluded.length" class="recipe-panel" :open="!result.items.length"><summary>查看 {{result.excluded.length}} 道食谱的排除原因</summary><ul><li v-for="e in result.excluded" :key="e.recipe_id">{{e.name}}：{{e.reason}}</li></ul></details>
<p class="recipe-note">本次查询不会扣减库存或自动新增饮食记录。</p><details><summary>开发调试信息（推荐算法版本）</summary><p>{{result.algorithm_version}}</p></details>
</section></section></template>
<style scoped>
.recommendation-card{min-width:0;overflow-wrap:anywhere}.brief-reason,.shortage-summary{font-size:13px;line-height:1.7;margin:10px 0}.ingredient-list{list-style:none;padding:0}.ingredient-list li{padding:12px 0;border-bottom:1px solid #dfe8df}.ingredient-list strong{display:block;font-size:14px;overflow-wrap:anywhere}.ingredient-list dl{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:10px 0 0}.ingredient-list dt{font-size:12px;color:#64796d}.ingredient-list dd{margin:5px 0 0;font-size:14px;overflow-wrap:anywhere}.ingredient-list .shortage{color:#94541d;font-weight:600}details{margin-top:12px}summary{cursor:pointer;min-height:32px;line-height:1.7}.recommendation-card :deep(.recipe-notice){padding:12px;font-size:13px;line-height:1.6}

.ranking-score{text-align:right;color:#246b58}.ranking-score span{font-size:32px;font-weight:600}.ranking-score small{display:block;font-size:12px}.score-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.score-grid>div{background:#f1f6f1;padding:14px;border-radius:8px}.score-grid span,.score-grid small,.score-grid strong{display:block}.score-grid span,.score-grid small{font-size:12px;color:#64796d}.score-grid strong{margin:8px 0}.recipe-workspace label.recipe-check{flex-direction:row;align-items:center;gap:10px}@media(max-width:500px){.score-grid{grid-template-columns:1fr}.ranking-score{text-align:left}}
</style>

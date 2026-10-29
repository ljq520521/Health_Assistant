<script setup>
import PublicFoodPicker from './PublicFoodPicker.vue'
import {preparationText} from './recipeUI.js'
import {onMounted,reactive,ref} from 'vue'
import {listFoods} from '../../api/foodLibrary.js'
import {recipeRequest,writeRecipeResource,removeRecipeResource,listRecipes,getRecipe,refreshRecipe} from '../../api/recipes.js'
import {useRecipeAction,nutritionFields} from './recipeUI.js'
import RecipeNutrition from './RecipeNutrition.vue'
import RecipeSource from './RecipeSource.vue'
const {busy,error,code,success,run}=useRecipeAction()
const recipes=ref([]),foods=ref([]),categories=ref([]),dialog=ref(null),confirmDialog=ref(null),selected=ref(null),id=ref(null),stepText=ref(''),categoryName=ref(''),categoryEdit=ref('')
const filters=reactive({q:'',category_id:''}),form=reactive({})
async function load(){const [r,f,c]=await Promise.all([listRecipes(filters),listFoods(),recipeRequest('/recipe-categories')]);recipes.value=r.items;foods.value=f.items;categories.value=c.items}
async function open(recipe=null){await run(async()=>{
  const r=recipe?await getRecipe(recipe.id):null;id.value=r?.id??null
  Object.assign(form,{name:r?.name??'',category_id:r?.category_id??'',description:r?.description??'',servings:r?.servings??1,preparation_minutes:r?.preparation_minutes??'',nutrition_mode:r?.nutrition_mode??'calculated',source_type:r?.source_type??'user_entered',source_note:r?.source_note??'',source_url:r?.source_url??'',revision:r?.revision,ingredients:r?r.ingredients.map(i=>({food_id:i.food_id,amount_g:i.amount_g})):[]})
  for(const [k] of nutritionFields)form['manual_'+k]=r?.['manual_'+k]??''
  stepText.value=r?r.steps.join('\n'):'';dialog.value.showModal()
})}
async function save(){await run(async()=>{
  const payload={...form,category_id:form.category_id===''?null:Number(form.category_id),servings:Number(form.servings),preparation_minutes:form.preparation_minutes===''?null:Number(form.preparation_minutes),ingredients:form.ingredients.map(i=>({food_id:Number(i.food_id),amount_g:Number(i.amount_g)})),steps:stepText.value.split('\n').map(s=>s.trim()).filter(Boolean)}
  for(const [k] of nutritionFields)payload['manual_'+k]=form.nutrition_mode==='calculated'||form['manual_'+k]===''?null:Number(form['manual_'+k])
  if(!id.value)delete payload.revision
  await writeRecipeResource('/recipes',payload,id.value);dialog.value.close();await load()
},'食谱已保存')}
function categoryChange(){categoryName.value=categories.value.find(c=>c.id===Number(categoryEdit.value))?.name??''}
async function saveCategory(){await run(async()=>{await writeRecipeResource('/recipe-categories',{name:categoryName.value},categoryEdit.value);categoryName.value='';categoryEdit.value='';await load()},'分类已保存')}
function confirm(kind,item){selected.value={kind,item};confirmDialog.value.showModal()}
async function perform(){await run(async()=>{
  const {kind,item}=selected.value
  if(kind==='refresh')await refreshRecipe(item.id,item.revision)
  else await removeRecipeResource(kind==='category'?'/recipe-categories':'/recipes',item.id)
  confirmDialog.value.close();await load()
},'操作已完成')}
onMounted(()=>run(load))
</script>
<template><section><div class="recipe-heading"><h2>食谱库</h2><button class="button primary" :disabled="busy||code==='RECIPES_MIGRATION_REQUIRED'||code==='PROFILE_REQUIRED'" @click="open()">新增食谱</button></div><p class="recipe-note">所有食材关联食物营养库。库存与营养均使用克重；不会自动生成真实营养信息。</p>
<p v-if="error" class="recipe-error" role="alert">{{error}} <RouterLink v-if="code==='PROFILE_REQUIRED'" to="/profile">前往建档</RouterLink><button class="button secondary" @click="run(load)">重试</button></p><p v-if="success" class="recipe-notice" role="status">{{success}}</p><p v-if="busy" role="status">正在处理…</p>
<form class="recipe-panel recipe-row" @submit.prevent="run(load)"><label>食谱名称搜索<input v-model="filters.q" maxlength="100" /></label><label>食谱分类筛选<select v-model="filters.category_id"><option value="">全部分类</option><option v-for="c in categories" :key="c.id" :value="c.id">{{c.name}}</option></select></label><button class="button primary" :disabled="busy">查询食谱</button></form>
<details class="recipe-panel"><summary>管理食谱分类</summary><form class="recipe-row" @submit.prevent="saveCategory"><label>选择编辑分类<select v-model="categoryEdit" @change="categoryChange"><option value="">新增分类</option><option v-for="c in categories" :key="c.id" :value="c.id">{{c.name}}</option></select></label><label>分类名称<input required maxlength="50" v-model="categoryName" /></label><button class="button primary" :disabled="busy">保存分类</button><button type="button" class="button secondary" :disabled="busy||!categoryEdit" @click="confirm('category',{id:categoryEdit})">删除分类</button></form></details>
<p v-if="!busy&&!recipes.length">暂无匹配食谱，请先维护食物库，再创建食谱。</p>
<article class="recipe-panel" v-for="r in recipes" :key="r.id"><div class="recipe-heading"><h3>{{r.name}}</h3><span v-if="r.is_example" class="recipe-badge">示例数据</span></div><p>{{r.description}}</p><p class="recipe-note">{{r.servings}}份 · {{preparationText(r.preparation_minutes)}} · {{r.nutrition_mode==='manual'?'用户手动营养':'食材快照计算'}}</p><h4>每份营养</h4><RecipeNutrition :data="r.per_serving"/><p v-if="r.snapshot_outdated" class="recipe-notice">食物资料已变化；当前仍使用原营养快照，可选择更新为食物库最新营养。</p><details><summary>食材、制作步骤及来源</summary><ul><li v-for="i in r.ingredients" :key="i.id">{{i.food_name_snapshot}}：{{i.amount_g}} g <span v-if="i.food_archived_at">（已归档，需更换食材后才能推荐）</span></li></ul><ol><li v-for="(s,index) in r.steps" :key="index">{{s}}</li></ol><RecipeSource :recipe="r"/><h4>整份食谱营养</h4><RecipeNutrition :data="r.nutrition"/></details><details><summary>开发调试信息（食谱版本）</summary><p>食谱版本 {{r.revision}}</p></details><div class="recipe-row recipe-actions"><button class="button secondary" :disabled="busy" :aria-label="'编辑食谱 '+r.name" @click="open(r)">编辑</button><button class="button secondary" :disabled="busy" :aria-label="'更新为食物库最新营养：'+r.name" @click="confirm('refresh',r)">更新为食物库最新营养</button><button class="button secondary" :disabled="busy" :aria-label="'归档食谱 '+r.name" @click="confirm('archive',r)">归档</button></div></article>
<dialog ref="dialog" class="recipe-dialog" @cancel="busy&&$event.preventDefault()"><form @submit.prevent="save"><h3>{{id?'编辑食谱':'新增食谱'}}</h3><p v-if="error" class="recipe-error" role="alert">{{error}}</p><fieldset :disabled="busy"><div class="recipe-grid"><label>食谱名称<input required maxlength="100" v-model="form.name"/></label><label>食谱分类<select v-model="form.category_id"><option value="">未分类</option><option v-for="c in categories" :key="c.id" :value="c.id">{{c.name}}</option></select></label><label>食谱份数<input type="number" min="0.0001" max="1000000000" step="any" required v-model="form.servings"/></label><label>制作分钟数<input type="number" min="0" max="100000" step="1" v-model="form.preparation_minutes"/></label></div><label>食谱说明<textarea maxlength="2000" v-model="form.description"/></label><h4>食材及整份克重</h4><PublicFoodPicker @selected="f => { if (!foods.some(x => x.id === f.id)) foods.push(f); form.ingredients.push({food_id:f.id,amount_g:100}) }"/><p v-if="!foods.length">没有有效食物，请先在食物营养库新增。</p><div class="recipe-row" v-for="(i,index) in form.ingredients" :key="index"><label>食材{{index+1}}<select required v-model="i.food_id"><option value="">请选择</option><option v-if="i.food_id&&!foods.some(f=>f.id===i.food_id)" :value="i.food_id">已归档食材 #{{i.food_id}}</option><option v-for="f in foods" :key="f.id" :value="f.id">{{f.name}}</option></select></label><label>克重{{index+1}}<input type="number" min="0.0001" max="1000000000" step="any" required v-model="i.amount_g"/></label><button type="button" class="button secondary" @click="form.ingredients.splice(index,1)">移除此食材</button></div><button type="button" class="button secondary" @click="form.ingredients.push({food_id:'',amount_g:''})">添加食材</button><label>制作步骤（每行一步）<textarea required rows="4" v-model="stepText"/></label><label>营养来源模式<select v-model="form.nutrition_mode"><option value="calculated">按食材营养快照计算</option><option value="manual">手动填写整份总量</option></select></label><div v-if="form.nutrition_mode==='manual'" class="recipe-grid"><label v-for="[k,label,unit] in nutritionFields" :key="k">整份{{label}}（{{unit}}，未知留空）<input type="number" min="0" max="1000000000" step="any" v-model="form['manual_'+k]"/></label></div><label>数据来源<select v-model="form.source_type"><option value="user_entered">用户录入</option><option value="referenced">参考资料</option><option value="example">示例数据</option></select></label><label>来源说明<textarea maxlength="2000" :required="form.nutrition_mode==='manual'" v-model="form.source_note"/></label><label>来源链接<input type="url" maxlength="2000" v-model="form.source_url"/></label></fieldset><p class="recipe-note">保存时由后端计算营养。相同食材改重量保留旧快照，更新为食物库最新营养需单独确认。</p><div class="recipe-row"><button class="button primary" :disabled="busy">保存食谱</button><button type="button" class="button secondary" :disabled="busy" @click="dialog.close()">取消</button></div></form></dialog>
<dialog ref="confirmDialog" class="recipe-dialog"><h3>确认操作</h3><p>{{selected?.kind==='refresh'?'确认将此食谱更新为食物库最新营养？仅更新此食谱的营养快照，不会自动影响已有历史饮食记录。':selected?.kind==='category'?'删除此食谱分类？有效食谱引用时会拒绝删除。':'归档后食谱不再参与推荐。确认归档？'}}</p><p v-if="error" class="recipe-error">{{error}}</p><div class="recipe-row"><button class="button primary" :disabled="busy" @click="perform">确认</button><button class="button secondary" :disabled="busy" @click="confirmDialog.close()">取消</button></div></dialog>
</section></template>

<style scoped>
.recipe-actions{margin-top:12px}.recipe-actions .button{min-height:44px;max-width:100%;white-space:normal;overflow-wrap:anywhere}summary{cursor:pointer;line-height:1.7;margin:10px 0}
</style>

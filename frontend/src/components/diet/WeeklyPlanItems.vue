<script setup>
import { computed } from 'vue'
import RecipeNutrition from './RecipeNutrition.vue'
import RecipeSource from './RecipeSource.vue'
import { displayNumber } from './recipeUI.js'
import { feedbackState, groupPlanDays, mealLabels, messageText } from './weeklyPlanUI.js'
const props = defineProps({ items: { type: Array, default: () => [] }, feedback: Boolean, canWrite: Boolean, busy: Boolean })
defineEmits(['feedback', 'history'])
const days = computed(() => groupPlanDays(props.items))
</script>
<template>
  <div class="weekly-days">
    <section v-for="day in days" :key="day.date" class="weekly-day">
      <h3>{{ day.date }}</h3>
      <div class="weekly-meals">
        <article v-for="item in day.items" :key="item.id || item.meal_type" class="weekly-meal">
          <div class="weekly-meal-heading"><h4>{{ mealLabels[item.meal_type] || item.meal_type }}</h4><span v-if="item.repeated" class="weekly-tag">食谱重复安排</span></div>
          <h5>{{ item.recipe?.name || '暂无符合条件的食谱' }}</h5>
          <p v-if="!item.recipe" class="recipe-note">没有候选时保留空餐次，不编造食谱，也不计为执行失败。</p>
          <p v-if="item.recipe && item.usable === false" class="recipe-error">当前资料下此建议已失效，请刷新未来食谱；历史记录仍保留。</p>
          <ul v-if="item.reasons?.length" class="weekly-reasons"><li v-for="(reason, i) in item.reasons" :key="i">{{ messageText(reason) }}</li></ul>
          <details v-if="item.recipe"><summary>食材、营养估算与来源</summary>
            <RecipeNutrition v-if="item.nutrition?.calories_kcal" :data="item.nutrition"/>
            <ul class="weekly-ingredients"><li v-for="(ingredient, i) in item.ingredients" :key="ingredient.food_key || ingredient.food_id || i"><strong>{{ ingredient.name }}</strong> {{ displayNumber(ingredient.required_g ?? ingredient.quantity_g) }} g<span v-if="ingredient.shortage_g > 0"> · 按登记库存缺 {{ displayNumber(ingredient.shortage_g) }} g</span><span v-if="ingredient.registered === false"> · 库存未登记</span></li></ul>
            <ol v-if="item.recipe.steps?.length"><li v-for="(step, i) in item.recipe.steps" :key="i">{{ typeof step === 'string' ? step : step.instruction || step.description }}</li></ol>
            <RecipeSource :recipe="item.recipe"/>
          </details>
          <div v-if="feedback" class="weekly-feedback">
            <span class="weekly-status" :class="feedbackState(item.feedback?.status).tone">{{ feedbackState(item.feedback?.status).icon }} {{ feedbackState(item.feedback?.status).label }}</span>
            <p v-if="item.feedback?.reason" class="recipe-note">原因：{{ item.feedback.reason }}</p><p v-if="item.feedback?.note" class="recipe-note">备注：{{ item.feedback.note }}</p>
            <div class="recipe-row"><button v-if="canWrite" class="btn" :disabled="busy" @click="$emit('feedback', item)">填写 / 修改反馈</button><button class="btn" :disabled="busy" @click="$emit('history', item)">反馈历史</button></div>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>
<style scoped>
.weekly-day{margin:20px 0}.weekly-day>h3{border-left:4px solid #246b58;padding-left:10px}.weekly-meals{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.weekly-meal{min-width:0;background:white;border:1px solid #dce7dd;border-radius:10px;padding:16px;overflow-wrap:anywhere}.weekly-meal-heading{display:flex;gap:8px;flex-wrap:wrap;align-items:center;justify-content:space-between}.weekly-meal h4{font-size:14px;margin:0}.weekly-meal h5{font-size:16px;line-height:1.5;margin:14px 0}.weekly-tag{font-size:11px;border-radius:5px;padding:4px 6px;background:#eef3ed;color:#60745e}.weekly-reasons,.weekly-ingredients{font-size:12px;padding-left:18px}.weekly-meal summary{font-size:13px;min-height:32px;line-height:1.7}.weekly-feedback{border-top:1px solid #e2ebe2;margin-top:16px;padding-top:12px}.weekly-status{display:inline-block;font-size:12px;padding:6px 10px;border-radius:6px}.success{background:#dcf0df;color:#185b2e}.danger{background:#ffe4df;color:#983629}.partial{background:#fff0d5;color:#845616}.neutral{background:#e7ece8;color:#526358}@media(max-width:1000px){.weekly-meals{grid-template-columns:1fr}.weekly-meal{padding:14px}}
</style>

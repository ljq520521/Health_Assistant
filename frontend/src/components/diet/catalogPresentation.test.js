import test from 'node:test'
import assert from 'node:assert/strict'
import { recipeSource } from './recipeSource.js'
import { foodSource } from './foodPresentation.js'
import { isDevelopmentDemo } from './demoContext.js'

test('public reference approval retains untried and allergen limits, independent of environment', () => {
  const recipe={origin:'public',editable:false,recipe_key:'team:recipe:1'}
  const before=structuredClone(recipe), result=recipeSource(recipe)
  assert.match(result.label,/课程演示数据已获团队批准/)
  assert.match(result.review,/过敏原未全面核验/)
  assert.match(result.trial,/未经实际试做/)
  assert.deepEqual(recipe,before)
  assert.equal(isDevelopmentDemo(null),false)
})
test('public cached foods show source approval without granting approval to edited private copies', () => {
  const publicFood={origin:'public',editable:false,food_key:'usda:fdc:1',source_type:'referenced',source_url:'https://fdc.nal.usda.gov/food-details/1/nutrients'}
  assert.match(foodSource(publicFood).review,/成分与过敏原未完整核验/)
  assert.doesNotMatch(foodSource({...publicFood,origin:'private',editable:true}).review,/已获团队批准/)
  assert.doesNotMatch(recipeSource({origin:'private',editable:true,recipe_key:'team:recipe:1',source_note:'团队自编、AI辅助、未经实际试做'}).review,/已获团队批准/)
})

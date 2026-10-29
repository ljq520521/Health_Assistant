import { request } from './foodLibrary.js'
export const listCatalog = (kind, filters = {}) => request(`/catalog/${kind}?${new URLSearchParams(filters)}`)
export const referenceFood = food_key => request('/catalog/food-references', { method: 'POST', body: JSON.stringify({ food_key }) })
export const copyPublicRecipe = recipe_key => request('/catalog/recipe-copies', { method: 'POST', body: JSON.stringify({ recipe_key }) })

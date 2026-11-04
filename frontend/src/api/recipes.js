import { request } from './foodLibrary.js'
export const recipeRequest = request
export const writeRecipeResource = (path,data,id) => request(path+(id?'/'+id:''),{method:id?'PUT':'POST',body:JSON.stringify(data)})
export const removeRecipeResource = (path,id) => request(path+'/'+id,{method:'DELETE'})
export const listRecipes = filters => request('/recipes?'+new URLSearchParams(Object.entries(filters).filter(([,v])=>v!==''&&v!=null)))
export const getRecipe = id => request('/recipes/'+id)
export const refreshRecipe = (id,revision) => request(`/recipes/${id}/refresh-nutrition`,{method:'POST',body:JSON.stringify({revision})})
export const previewRecipes = data => request('/recipe-recommendations/preview',{method:'POST',body:JSON.stringify(data)})

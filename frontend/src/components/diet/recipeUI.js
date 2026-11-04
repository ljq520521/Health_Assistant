import { ref } from 'vue'
export const nutritionFields=[['calories_kcal','热量','kcal'],['protein_g','蛋白质','g'],['fat_g','脂肪','g'],['carbohydrate_g','碳水化合物','g']]
export const displayNumber = x => x==null?'未知':new Intl.NumberFormat('zh-CN',{maximumFractionDigits:2}).format(x)
export const preparationText = minutes => minutes == null ? '制作时间未填写' : `制作时间 ${displayNumber(minutes)} 分钟`
export function useRecipeAction(){
  const busy=ref(false),error=ref(''),code=ref(''),success=ref('')
  async function run(work,message=''){
    if(busy.value)return false
    busy.value=true;error.value='';code.value='';success.value=''
    try{await work();success.value=message;return true}
    catch(e){error.value=e.message;code.value=e.code||'';return false}
    finally{busy.value=false}
  }
  return {busy,error,code,success,run}
}

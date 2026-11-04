import { request } from './foodLibrary.js'
export const listWater = filters => request('/water-records?'+new URLSearchParams(Object.entries(filters).filter(([,v])=>v)))
export const saveWater = (data,id) => request('/water-records'+(id?'/'+id:''),{method:id?'PUT':'POST',body:JSON.stringify(data)})
export const deleteWater = id => request('/water-records/'+id,{method:'DELETE'})
export const waterSummary = date => request('/water-summary?'+new URLSearchParams({date}))
export const getWaterReminder = () => request('/water-reminder-settings')
export const saveWaterReminder = data => request('/water-reminder-settings',{method:'PUT',body:JSON.stringify(data)})

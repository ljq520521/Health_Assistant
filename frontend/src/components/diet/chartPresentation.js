import {measurement,statusText} from './metricPresentation.js'
export function chartGeometry(chart,width=320) {
  const w=Math.max(220,Math.min(640,width)),left=58,right=w-18,top=38,bottom=180
  const values=chart.points.filter(p=>p.value!=null).map(p=>p.value)
  const peak=Math.max(1,...values), magnitude=10**Math.floor(Math.log10(peak))
  const max=Math.ceil(peak/magnitude)*magnitude
  const points=chart.points.map((p,index)=>({...p,index,x:left+(chart.points.length<2?(right-left)/2:index/(chart.points.length-1)*(right-left)),y:p.value==null?null:bottom-p.value/max*(bottom-top)}))
  const segments=[];let line=[]
  for(const p of points){if(p.value==null){if(line.length)segments.push(line);line=[]}else line.push(p)}
  if(line.length)segments.push(line)
  return {width:w,left,right,bottom,points,segments,ticks:[0,max/2,max].map(value=>({value,y:bottom-value/max*(bottom-top)}))}
}
export function pointDescription(point,unit) {
  const value=measurement(point.value,unit,point.status==='no_records'?'当天没有记录':'营养数据未知')
  const state=statusText[point.status]||'数据状态未提供'
  return `${point.label}：${value}${value===state?'':'；'+state}`
}
export const shortDate = label => /^\d{4}-\d{2}-\d{2}$/.test(label) ? label.slice(5).replace('-','/') : label

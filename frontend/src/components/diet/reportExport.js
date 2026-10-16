import {timeZoneLabel} from './displayTime.js'
import {intakeText,goalText,ratioText,waterMetric,completenessText} from './metricPresentation.js'
import {reportCopy,demoReportNotice} from './reportCopy.js'
import {imagePagesPDF} from './reportPdf.js'
import {metrics,periodLabels,statuses,format,compact,reportName,chartsFor,geometry,overviewLines} from './reportPresentation.js'
const font='"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif'
function canvas(width,height){const c=document.createElement('canvas');c.width=width;c.height=height;const ctx=c.getContext('2d');if(!ctx)throw new Error('当前浏览器不支持 Canvas 导出');ctx.fillStyle='#fff';ctx.fillRect(0,0,width,height);return {canvas:c,ctx}}
function text(ctx,value,x,y,size=24,color='#294638',bold=false){ctx.font=`${bold?'600 ':''}${size}px ${font}`;ctx.fillStyle=color;ctx.fillText(String(value),x,y)}
export function wrap(ctx,value,width){const lines=[];for(const paragraph of String(value).split('\n')){let line='';for(const char of paragraph){if(line&&ctx.measureText(line+char).width>width){lines.push(line);line=char}else line+=char}lines.push(line)}return lines}
function blob(c,type='image/png'){return new Promise((resolve,reject)=>c.toBlob(value=>value?resolve(value):reject(new Error('图片编码失败，请重试')),type,.96))}
async function fontsReady(){if(document.fonts){let timer;try{await Promise.race([document.fonts.ready,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('字体加载超时，请稍后重试')),15000)})])}finally{clearTimeout(timer)}}}
export function drawChart(ctx,chart,x,y,width){
  const g=geometry(chart),factor=width/640
  ctx.save();ctx.translate(x,y);ctx.scale(factor,factor);ctx.fillStyle='#fff';ctx.fillRect(0,0,640,285)
  text(ctx,chart.title+'（'+chart.unit+'）',16,23,15,'#214f40',true)
  ctx.strokeStyle='#95ac9e';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(70,48);ctx.lineTo(70,190);ctx.lineTo(575,190);ctx.stroke()
  ctx.strokeStyle='#e6ede7';ctx.beginPath();ctx.moveTo(70,122);ctx.lineTo(575,122);ctx.stroke()
  ctx.textAlign='right';text(ctx,compact(g.max),62,58,10,'#5e7568');text(ctx,'0',62,194,10,'#5e7568');ctx.textAlign='left'
  if(chart.kind==='line'){
    ctx.strokeStyle='#246b58';ctx.lineWidth=2
    for(const segment of g.segments){ctx.beginPath();segment.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.stroke()}
    for(const p of g.points.filter(p=>p.value!=null)){ctx.fillStyle=p.status==='partial'?'#b77a22':'#246b58';ctx.beginPath();ctx.arc(p.x,p.y,4,0,Math.PI*2);ctx.fill()}
    text(ctx,g.points[0]?.label||'',70,218,11,'#5e7568');ctx.textAlign='right';text(ctx,g.points.at(-1)?.label||'',560,218,11,'#5e7568');ctx.textAlign='left'
  }else for(const p of g.points){ctx.fillStyle='#3d846e';ctx.fillRect(p.x-22,p.y,44,190-p.y);ctx.textAlign='center';text(ctx,p.value,p.x,p.y-8,12);text(ctx,p.label,p.x,216,12,'#5e7568');ctx.textAlign='left'}
  if(chart.points.every(p=>p.value==null)){ctx.textAlign='center';text(ctx,'暂无可绘制的已知数据',320,110,14,'#7b887f');ctx.textAlign='left'}
  ctx.font=`12px ${font}`;wrap(ctx,chart.note,600).forEach((line,i)=>text(ctx,line,16,245+i*18,12,'#61776b'))
  ctx.restore()
}
export async function exportChartPNG(report,chart,options={}){
  await fontsReady();const demo=demoReportNotice(options.demo);const {canvas:c,ctx}=canvas(1600,demo?940:880)
  text(ctx,reportName(report),40,42,26,'#246b58',true)
  text(ctx,'仅基于已录入记录；缺失不代表实际摄入为零。',40,82,22,'#61776b')
  if(demo)text(ctx,demo,40,120,24,'#93651b',true)
  drawChart(ctx,chart,20,demo?160:115,1560)
  text(ctx,report.is_partial_period?'当前统计周期进行中；数据可能继续变化。':'历史周期；字段完整不保证已记录全部摄入。',40,demo?910:850,20,'#61776b')
  return {blob:await blob(c), name:`${reportName(report)}_${chart.title}.png`}
}
export async function exportReportPDF(report,options={}){
  await fontsReady()
  const copy=reportCopy(report),demo=demoReportNotice(options.demo)
  // Fixed A4 geometry at ~150dpi; independent of the phone/desktop viewport.
  const W=1240,H=1754,M=70,pages=[];let current,y
  function newPage(){current=canvas(W,H);pages.push(current);y=150;text(current.ctx,'HEALTH JOURNAL · 饮食报告',M,60,22,'#246b58',true);text(current.ctx,`${periodLabels[report.period]}  ${report.date_from} 至 ${report.date_to}`,M,102,26,'#294638',true);current.ctx.strokeStyle='#dce7df';current.ctx.beginPath();current.ctx.moveTo(M,122);current.ctx.lineTo(W-M,122);current.ctx.stroke()}
  function ensure(height){if(y+height>H-145)newPage()}
  function paragraph(value,size=24,color='#294638',bold=false){current.ctx.font=`${bold?'600 ':''}${size}px ${font}`;const lines=wrap(current.ctx,value,W-2*M);const height=lines.length*size*1.6+8;if(height<H-295)ensure(height);for(const line of lines){ensure(size*1.6);text(current.ctx,line,M,y+size,size,color,bold);y+=size*1.6}y+=8}
  function heading(value){ensure(85);y+=12;paragraph(value,30,'#246b58',true)}
  function metricCards(){
    const width=(W-2*M-24)/2,height=208
    for(let i=0;i<metrics.length;i+=2){ensure(height+20);for(let j=0;j<2;j++){const [key,label,unit]=metrics[i+j],m=report.nutrition.total.nutrients[key],x=M+j*(width+24);const ctx=current.ctx;ctx.fillStyle='#f0f6f0';ctx.fillRect(x,y,width,height);text(ctx,label+'已知累计',x+20,y+34,24,'#246b58',true);text(ctx,intakeText(m,unit,report.period_days),x+20,y+76,30,'#246b58',true);text(ctx,`${completenessText(m,report.period_days)} · 未知 ${m.unknown_count} 条`,x+20,y+114,21);text(ctx,'区间目标 '+goalText(m,unit,report.period_days),x+20,y+151,21);text(ctx,'目标比例 '+ratioText(m,report.period_days),x+20,y+184,21)}y+=height+20}
  }
  newPage();heading('记录概览')
  paragraph(`自然周期 ${report.period_from} 至 ${report.period_to}；统计 ${report.period_days} 天；时区 ${timeZoneLabel(report.time_zone)}`,22)
  if(report.is_partial_period)paragraph('部分周期 / 当前周期进行中，今天记录可能继续变化。',24,'#93651b',true)
  for(const line of overviewLines(report))paragraph(line,23)
  paragraph(report.averages.note,21,'#61776b')
  heading('营养与目标');metricCards()
  paragraph(`饮水区间目标 ${goalText(waterMetric(report.water),'ml',report.period_days)}；已记录目标比例 ${ratioText(waterMetric(report.water),report.period_days)}`,23)
  paragraph(`饮水目标缺失 ${report.water.target_missing_days} 天；比例不作为健康判断。目标按每天实际生效版本累计。`,21,'#61776b')
  paragraph('未知营养不作为0；区间内有任一天未设目标则不计算该项累计目标及比例。',21,'#61776b')
  const charts=chartsFor(report)
  for(let index=0;index<charts.length;index++){if(index%2===0)newPage();const chart=charts[index];drawChart(current.ctx,chart,M,y,W-2*M);y+=(W-2*M)/640*285+65}
  newPage();heading('饮食分析建议')
  for(const [index,s] of copy.suggestions.entries()){paragraph(`${index+1}. ${s.text}`,24);for(const line of s.evidence)paragraph('依据：'+line,19,'#61776b')}
  if(!report.suggestions.length)paragraph('当前数据没有触发记录规则提示；不代表医学评价。')
  newPage();heading('数据完整性说明');for(const note of copy.notes)paragraph('• '+note,23)
  paragraph('本文件基于导出时显示的报告数据。',19,'#61776b')
  const images=[]
  for(const [index,page] of pages.entries()){
    if(demo)text(page.ctx,demo,M,H-116,22,'#93651b',true)
    text(page.ctx,'仅基于已录入记录，不进行医学诊断；未知与无记录不代表实际零摄入。',M,H-85,19,'#61776b')
    text(page.ctx,`${report.date_from} 至 ${report.date_to}     第 ${index+1} / ${pages.length} 页`,M,H-48,19,'#61776b')
    images.push({width:W,height:H,jpeg:new Uint8Array(await (await blob(page.canvas,'image/jpeg')).arrayBuffer())})
    page.canvas.width=0;page.canvas.height=0
  }
  return {blob:imagePagesPDF(images,reportName(report)), name:reportName(report)+'.pdf'}
}

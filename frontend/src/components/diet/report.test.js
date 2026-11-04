import test from 'node:test'
import assert from 'node:assert/strict'
import {geometry,chartsFor,metrics,reportName,format} from './reportPresentation.js'
import {imagePagesPDF} from './reportPdf.js'
import {wrap} from './reportExport.js'

test('图表保留真实0，未知和无记录处断线',()=>{
  const chart={points:[0,null,20,null,10].map(value=>({value}))}
  const g=geometry(chart)
  assert.equal(g.points[0].y,190)
  assert.equal(g.points[1].y,null)
  assert.deepEqual(g.segments.map(s=>s.map(p=>p.value)),[[0],[20],[10]])
  assert.equal(g.max,20)
  assert.equal(geometry({points:[{value:null}]}).max,1)
})
test('六张图直接展示服务端数值与状态，不将未知转换为0',()=>{
  const r={nutrition:{daily:[{actual_from:'2026-09-01',nutrients:Object.fromEntries(metrics.map(([k])=>[k,{known_sum:null,data_status:'unknown'}]))}]},water:{daily:[{date:'2026-09-01',known_sum_ml:null,data_status:'no_records'}]},meal_distribution:[{label:'早餐',record_count:0}]}
  const charts=chartsFor(r)
  assert.equal(charts.length,6)
  assert.equal(charts[0].points[0].value,null)
  assert.equal(charts[4].points[0].status,'no_records')
  assert.equal(charts[5].points[0].value,0)
  assert.match(format(null),/未知/)
  assert.equal(format(0),'0')
})
test('导出命名使用当前报告实际日期范围',()=>{
  assert.equal(reportName({period:'month',date_from:'2026-10-01',date_to:'2026-10-14'}),'饮食报告_月报_2026-10-01_2026-10-14')
})
test('PDF中文说明按字符换行，保留完整提示和段落',()=>{
  const lines=wrap({measureText:s=>({width:[...s].length*10})},'未知营养不是零\n数据不完整',40)
  assert.deepEqual(lines,['未知营养','不是零','数据不完','整'])
})
test('PDF二进制交叉引用指向正确对象，包含两页和中文标题',async()=>{
  // Binary placeholder validates the container only; real JPEG/rendering is browser-tested.
  const jpeg=new Uint8Array([255,216,0,128,255,217])
  const blob=imagePagesPDF([{width:100,height:200,jpeg},{width:100,height:200,jpeg}],'饮食报告')
  assert.equal(blob.type,'application/pdf')
  const bytes=new Uint8Array(await blob.arrayBuffer()),text=new TextDecoder('latin1').decode(bytes)
  const xref=Number(text.match(/startxref\n(\d+)/)[1])
  assert.equal(text.slice(xref,xref+4),'xref')
  const rows=text.slice(xref).split('\n'),count=Number(rows[1].split(' ')[1])
  for(let id=1;id<count;id++){
    const at=Number(rows[id+2].slice(0,10))
    assert.equal(text.slice(at,at+`${id} 0 obj`.length),`${id} 0 obj`)
  }
  assert.match(text,/\/Count 2/)
  assert.match(text,/\/Title <FEFF996e98df62a5544a>/)
  assert.throws(()=>imagePagesPDF([]),/没有可导出/)
})

// Minimal PDF 1.4 image-page writer. Binary offsets are measured in bytes, not text.
// Images are generated locally by Canvas; no remote resources or embedded fonts.
const encoder=new TextEncoder()
export function imagePagesPDF(pages,title='Diet report'){
  if(!pages.length)throw new Error('报告没有可导出的页面')
  const objects=[null,null],pageIds=[]
  const bytes=text=>encoder.encode(text)
  const join=parts=>{const size=parts.reduce((sum,p)=>sum+p.length,0),out=new Uint8Array(size);let at=0;for(const p of parts){out.set(p,at);at+=p.length}return out}
  for(const page of pages){
    const id=objects.length+1,imageId=id+1,contentId=id+2;pageIds.push(id)
    objects.push(bytes(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Resources << /XObject << /Im0 ${imageId} 0 R >> >> /Contents ${contentId} 0 R >>`))
    objects.push(join([bytes(`<< /Type /XObject /Subtype /Image /Width ${page.width} /Height ${page.height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${page.jpeg.length} >>\nstream\n`),page.jpeg,bytes('\nendstream')]))
    const stream=bytes('q\n595.28 0 0 841.89 0 0 cm\n/Im0 Do\nQ\n')
    objects.push(join([bytes(`<< /Length ${stream.length} >>\nstream\n`),stream,bytes('endstream')]))
  }
  objects[0]=bytes('<< /Type /Catalog /Pages 2 0 R >>')
  objects[1]=bytes(`<< /Type /Pages /Count ${pages.length} /Kids [${pageIds.map(id=>id+' 0 R').join(' ')}] >>`)
  const utf16='FEFF'+title.split('').map(c=>c.charCodeAt(0).toString(16).padStart(4,'0')).join('')
  objects.push(bytes(`<< /Title <${utf16}> /Producer (Health Assistant - local Canvas export) >>`))
  const chunks=[bytes('%PDF-1.4\n')],offsets=[0];let size=chunks[0].length
  objects.forEach((object,index)=>{offsets.push(size);const chunk=join([bytes(`${index+1} 0 obj\n`),object,bytes('\nendobj\n')]);chunks.push(chunk);size+=chunk.length})
  const xref=size
  chunks.push(bytes(`xref\n0 ${objects.length+1}\n0000000000 65535 f \n${offsets.slice(1).map(n=>String(n).padStart(10,'0')+' 00000 n \n').join('')}trailer\n<< /Size ${objects.length+1} /Root 1 0 R /Info ${objects.length} 0 R >>\nstartxref\n${xref}\n%%EOF\n`))
  return new Blob(chunks,{type:'application/pdf'})
}

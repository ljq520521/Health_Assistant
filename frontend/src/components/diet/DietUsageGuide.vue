<script setup>
import { onBeforeUnmount, ref } from 'vue'

const emit = defineEmits(['select'])
const dialog = ref(null), trigger = ref(null), opened = ref(false)

function open() {
  if (!dialog.value || dialog.value.open) return
  dialog.value.showModal()
  dialog.value.scrollTop = 0
  opened.value = true
}
function close() { dialog.value?.close() }
function closed() {
  opened.value = false
  trigger.value?.focus({ preventScroll: true })
}
function select(tab) {
  close()
  emit('select', tab)
}
function dismissBackdrop(event) {
  if (event.target !== dialog.value) return
  const bounds = dialog.value.getBoundingClientRect()
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) close()
}
onBeforeUnmount(close)
</script>

<template>
  <button ref="trigger" type="button" class="button secondary guide-trigger" aria-haspopup="dialog" :aria-expanded="opened" @click="open">使用指南</button>
  <Teleport to="body">
  <dialog ref="dialog" class="diet-guide" aria-labelledby="diet-guide-title" @close="closed" @click="dismissBackdrop">
    <header class="guide-header">
      <div><h2 id="diet-guide-title">饮食使用指南</h2><p>建档 → 记录 → 推荐 → 反馈</p></div>
      <button type="button" class="guide-close" aria-label="关闭使用指南" autofocus @click="close">关闭 ×</button>
    </header>
    <div class="guide-content">
      <p class="guide-intro">第一次使用，可以按下面的顺序操作。只想查食物或菜谱？无需登录即可浏览 134 种公共食物和 12 道公共菜谱。</p>
      <ol class="guide-steps">
        <li>
          <h3>登录并建立档案</h3>
          <p>打开“用户与基础”，登录后填写并保存健康档案。首次使用时先创建账户。记录、计划和反馈需要具备写入权限，并开启健康数据授权；只读账号不能保存。</p>
          <RouterLink class="guide-action" to="/profile" @click="close">前往用户与基础 →</RouterLink>
        </li>
        <li>
          <h3>选择食物，记录实际摄入</h3>
          <p>在“食物营养库”搜索食品，点击“加入我的可用食品”。再到“饮食记录”选择日期、餐次、食物和实际克重并保存。找不到的食品可在“我的食品”中自行新增；公共食品不能直接编辑。</p>
          <div class="guide-actions"><button type="button" class="guide-action" @click="select('library')">查找食物 →</button><button type="button" class="guide-action" @click="select('records')">记录饮食 →</button></div>
        </li>
        <li>
          <h3>设置目标、库存与偏好</h3>
          <p>在“营养摄入分析”设置自己明确的营养目标。进入“食谱推荐”，可在“食材库存”登记食材，在“成分与偏好”选择具体食物、食材或过敏原，添加喜欢、不喜欢、过敏或禁用规则。</p>
          <p>档案里填写了过敏史或偏好文字时，还需在“一周计划与反馈”核对对应规则。系统不会猜测文字含义，也不会根据身高体重自动设定热量。</p>
          <div class="guide-actions"><button type="button" class="guide-action" @click="select('analysis')">查看营养与目标 →</button><button type="button" class="guide-action" @click="select('recipes')">设置食谱条件 →</button></div>
        </li>
        <li>
          <h3>获取单餐推荐或一周计划</h3>
          <p>进入“食谱推荐 → 获取食谱推荐”，选择早餐、午餐、晚餐或加餐，填写份数后点击“获取推荐”。目标占比可留空；未设置目标、库存或偏好时，对应维度不参与评分。</p>
          <p>想安排一周？打开“一周计划与反馈”，选择开始日期，检查 7 天早、午、晚共 21 个餐次，点击“确认并保存本周计划”，再确认保存。资料更新后，先检查新预览，再决定是否刷新未来安排。</p>
          <button type="button" class="guide-action" @click="select('recipes')">打开食谱推荐 →</button>
        </li>
        <li>
          <h3>每天反馈，查看执行进度</h3>
          <p>进入“一周计划与反馈 → 每日反馈”，选择已保存的计划，点击餐次下的“填写 / 修改反馈”，选择状态、填写可选备注并保存。可随时修改，也可查看反馈历史和历史计划。</p>
          <p class="guide-status"><span class="completed">✓ 已完成</span><span class="missed">× 未完成</span><span class="partial">◐ 部分完成</span><span class="pending">○ 未反馈</span><span class="pending">— 不适用</span></p>
          <p>反馈保存后进度会更新。未反馈不算失败，部分完成单独统计；反馈不会自动生成实际饮食记录，也不会扣库存，吃过的食物仍需自行记录。</p>
        </li>
        <li>
          <h3>记录饮水，回看报告</h3>
          <p>在“饮水管理”记录实际饮水时间和毫升数，并按需设置目标与提醒。在“饮食报告”选择日报、周报或月报，生成报告后查看统计、导出 PDF 或图表 PNG。报告依据已保存的摄入记录，不把食谱计划当作实际摄入。</p>
          <div class="guide-actions"><button type="button" class="guide-action" @click="select('water')">记录饮水 →</button><button type="button" class="guide-action" @click="select('reports')">查看报告 →</button></div>
        </li>
      </ol>
      <div class="guide-help">
        <h3>没有推荐或无法保存时怎么办？</h3>
        <p>先查看页面提示：未登录或未建档，请前往“用户与基础”；只读或未授权，请检查账户权限；档案文字未确认，请核对偏好与禁忌规则。</p>
        <p>没有符合当前餐次的食谱时，查看排除原因。现有公共库只有一道早餐，且含鸡蛋；禁用鸡蛋后可能没有早餐候选，可新增适合自己的早餐食谱。未填写成分资料不会单独排除食谱，但不代表已确认过敏安全，不要为了得到推荐而取消真实禁忌。</p>
      </div>
    </div>
  </dialog>
  </Teleport>
</template>

<style scoped>
.guide-trigger{flex-shrink:0}
.diet-guide{width:min(900px,calc(100% - 32px));max-height:88vh;max-height:88dvh;box-sizing:border-box;margin:auto;padding:0;border:1px solid #dce7dd;border-radius:16px;background:#fff;color:#273e36;overflow:auto;overscroll-behavior:contain;overflow-wrap:anywhere;box-shadow:0 24px 80px #173b2833}
.diet-guide::backdrop{background:#173b2866}
.guide-header{position:sticky;top:0;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 22px;background:#f0f6f1;border-bottom:1px solid #dce7dd}
.guide-header h2{margin:0;font-size:20px;color:#246b58}.guide-header p{margin:6px 0 0;font-size:12px;color:#61776a}
.guide-close{flex-shrink:0;min-height:40px;padding:8px 12px;border:1px solid #cddace;border-radius:8px;background:#fff;color:#246b58;font:inherit;font-size:13px;cursor:pointer}
.guide-close:focus-visible,.guide-action:focus-visible{outline:2px solid #246b58;outline-offset:3px}
.guide-content{padding:22px}.guide-intro{margin:0 0 16px;font-size:13px;line-height:1.8;color:#61776a}
.guide-steps{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px 28px;margin:0;padding-left:24px}.guide-steps li{min-width:0;padding-left:4px}.guide-steps li::marker{color:#246b58;font-weight:700}.guide-content h3{font-size:14px;margin:0 0 6px}.guide-content p{font-size:13px;line-height:1.8}.guide-steps p{margin:6px 0;color:#526b5d}.guide-actions{display:flex;flex-wrap:wrap;gap:4px 16px}.guide-action{display:inline-block;border:0;background:none;padding:6px 0;font:inherit;font-size:13px;color:#246b58;text-decoration:underline;text-underline-offset:3px;cursor:pointer}
.guide-status{display:flex;flex-wrap:wrap;gap:6px}.guide-status span{padding:2px 8px;border-radius:5px;font-size:12px}.completed{background:#e4f2e7;color:#26613c}.missed{background:#fff0ec;color:#a04431}.partial{background:#fff4dc;color:#855a17}.pending{background:#eef1ef;color:#59665f}.guide-help{margin-top:18px;padding-top:14px;border-top:1px solid #e2e9e2}.guide-help p{margin:6px 0;color:#526b5d}
@media(max-width:650px){.diet-guide{width:calc(100% - 20px);max-height:92vh;max-height:92dvh;border-radius:12px}.guide-steps{grid-template-columns:1fr;gap:18px}.guide-content{padding:16px}.guide-header{padding:14px 16px}.guide-header h2{font-size:18px}}
</style>

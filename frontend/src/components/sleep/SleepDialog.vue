<script setup>
import { onMounted, ref } from 'vue'
defineProps({ title: String, busy: Boolean })
const emit = defineEmits(['close'])
const dialog = ref(null)
onMounted(() => dialog.value.showModal())
</script>
<template>
  <dialog ref="dialog" class="sleep-dialog" aria-labelledby="sleep-dialog-title" @cancel.prevent="!busy && emit('close')" @click="event => event.target === dialog && !busy && emit('close')">
    <div class="sleep-dialog-heading"><h2 id="sleep-dialog-title">{{ title }}</h2><button type="button" class="sleep-text-button" aria-label="关闭弹窗" :disabled="busy" @click="emit('close')">✕</button></div>
    <slot />
  </dialog>
</template>

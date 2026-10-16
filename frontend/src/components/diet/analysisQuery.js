import {computed,ref} from 'vue'
export function useAppliedQuery(filters) {
  const applied=ref(null)
  const capture=()=>({date_from:filters.date_from,date_to:filters.date_to,group_by:filters.group_by})
  const changed=computed(()=>!!applied.value && Object.keys(capture()).some(k=>filters[k]!==applied.value[k]))
  const accept=conditions=>{applied.value={...conditions}}
  return {applied,changed,capture,accept}
}

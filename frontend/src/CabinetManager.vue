<script setup>
import { ref, watch } from 'vue'
import * as XLSX from 'xlsx'

const props = defineProps({
  apiBase: { type: String, required: true },
  llmData: { type: Object, default: null },
  pageCount: { type: Number, default: 0 },
})

const emit = defineEmits(['card-saved'])

const cabinets = ref([])
const selectedCabinetId = ref(null)
const entries = ref([])
const newCabinetName = ref('')
const createMode = ref(false)
const busy = ref(false)
const err = ref('')
const cardModal = ref(false)
const lastCard = ref(null)

async function fetchCabinets() {
  try {
    const r = await fetch(`${props.apiBase}/cabinets`)
    cabinets.value = await r.json()
  } catch (e) { console.error(e) }
}

async function fetchEntries(id) {
  if (!id) { entries.value = []; return }
  try {
    const r = await fetch(`${props.apiBase}/cabinets/${id}/entries`)
    entries.value = await r.json()
  } catch (e) { console.error(e) }
}

async function createCabinet() {
  if (!newCabinetName.value.trim()) return
  busy.value = true; err.value = ''
  try {
    const r = await fetch(`${props.apiBase}/cabinets`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newCabinetName.value.trim() })
    })
    if (!r.ok) { const d = await r.json(); throw new Error(d.detail || 'Ошибка') }
    const cab = await r.json()
    await fetchCabinets()
    selectedCabinetId.value = cab.id
    newCabinetName.value = ''
    createMode.value = false
  } catch (e) { err.value = e.message }
  finally { busy.value = false }
}

async function deleteCabinet(id) {
  if (!confirm('Удалить шкаф и все записи?')) return
  try {
    await fetch(`${props.apiBase}/cabinets/${id}`, { method: 'DELETE' })
    if (selectedCabinetId.value === id) { selectedCabinetId.value = null; entries.value = [] }
    await fetchCabinets()
  } catch (e) { console.error(e) }
}

async function addDeviceToShkaf() {
  if (!selectedCabinetId.value || !props.llmData) return
  busy.value = true; err.value = ''
  try {
    const ce = props.llmData.cabinet_entry || {}
    const dc = props.llmData.device_card || {}
    const pg = props.pageCount ? `${props.pageCount} стр.` : ''

    const safeString = (val) => {
      if (val === null || val === undefined) return ''
      if (Array.isArray(val)) return val.join(', ')
      if (typeof val === 'object') return JSON.stringify(val)
      return String(val)
    }

    // 1. Add entry to cabinet
    const r1 = await fetch(`${props.apiBase}/cabinets/${selectedCabinetId.value}/entries`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        document_name: safeString(ce.document_name || dc.name || ''),
        serial_number: safeString(ce.serial_number || dc.serial_number || ''),
        pages: safeString(pg),
        certificate: safeString(ce.certificate || '')
      })
    })
    if (!r1.ok) { const d = await r1.json(); throw new Error(d.detail || 'Ошибка 422: неверный формат данных') }
    const entry = await r1.json()

    // 2. Save device card
    const r2 = await fetch(`${props.apiBase}/cards`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        entry_id: Number(entry.id),
        name: safeString(dc.name || ce.document_name || ''),
        serial_number: safeString(dc.serial_number || ce.serial_number || ''),
        decimal_number: safeString(dc.decimal_number || ''),
        production_date: safeString(dc.production_date || ''),
        warranty_period: safeString(dc.warranty_period || ''),
        raw_json: props.llmData
      })
    })
    if (!r2.ok) { const d = await r2.json(); throw new Error(d.detail || 'Ошибка сохранения карточки') }
    lastCard.value = await r2.json()
    cardModal.value = true
    emit('card-saved', lastCard.value)

    await fetchEntries(selectedCabinetId.value)
  } catch (e) { err.value = e.message }
  finally { busy.value = false }
}

async function deleteEntry(eid) {
  if (!selectedCabinetId.value) return
  try {
    await fetch(`${props.apiBase}/cabinets/${selectedCabinetId.value}/entries/${eid}`, { method: 'DELETE' })
    await fetchEntries(selectedCabinetId.value)
    await fetchCabinets()
  } catch (e) { console.error(e) }
}

function downloadCard() {
  if (!lastCard.value) return
  const blob = new Blob([JSON.stringify(lastCard.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `card-${lastCard.value.serial_number || lastCard.value.id}.json`
  a.click(); URL.revokeObjectURL(url)
}

function downloadCardExcel() {
  if (!lastCard.value) return

  const rows = Object.entries(lastCard.value).map(([key, value]) => {
    if (value && typeof value === 'object') {
      return { field: key, value: JSON.stringify(value) }
    }
    return { field: key, value: value ?? '' }
  })

  const worksheet = XLSX.utils.json_to_sheet(rows)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Card')

  const buffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' })
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `card-${lastCard.value.serial_number || lastCard.value.id}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}

watch(selectedCabinetId, (id) => fetchEntries(id))
fetchCabinets()
</script>

<template>
  <section class="cabinet-section panel">
    <div class="section-head">
      <div>
        <span>Шкафы</span>
        <small>Управление таблицами шкафов и карточками устройств</small>
      </div>
    </div>

    <!-- Cabinet selector -->
    <div class="cab-controls">
      <div class="cab-select-row">
        <select v-model="selectedCabinetId" class="cab-select">
          <option :value="null" disabled>Выберите шкаф…</option>
          <option v-for="c in cabinets" :key="c.id" :value="c.id">
            {{ c.name }} ({{ c.entry_count }} записей)
          </option>
        </select>
        <button class="small-btn" @click="createMode = !createMode">
          {{ createMode ? 'Отмена' : '+ Новый шкаф' }}
        </button>
        <button v-if="selectedCabinetId" class="small-btn danger-btn" @click="deleteCabinet(selectedCabinetId)">
          Удалить шкаф
        </button>
      </div>

      <div v-if="createMode" class="cab-create-row">
        <input v-model="newCabinetName" class="cab-input" placeholder="Название нового шкафа" @keyup.enter="createCabinet" />
        <button class="run-button compact-btn" :disabled="!newCabinetName.trim() || busy" @click="createCabinet">Создать</button>
      </div>

      <div v-if="llmData && selectedCabinetId" class="cab-add-row">
        <button class="run-button" :disabled="busy" @click="addDeviceToShkaf">
          Добавить устройство в шкаф
        </button>
      </div>
    </div>

    <p v-if="err" class="error-message">{{ err }}</p>

    <!-- Cabinet table -->
    <div v-if="selectedCabinetId && entries.length" class="cab-table-wrap">
      <table class="cab-table">
        <thead>
          <tr>
            <th>№ п/п</th>
            <th>Наименование документа</th>
            <th>Заводской номер</th>
            <th>Страницы / листов</th>
            <th>Сертификат</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in entries" :key="e.id">
            <td>{{ e.row_number }}</td>
            <td>{{ e.document_name }}</td>
            <td class="mono">{{ e.serial_number }}</td>
            <td>{{ e.pages }}</td>
            <td>{{ e.certificate }}</td>
            <td><button class="icon-btn small-del" @click="deleteEntry(e.id)">✕</button></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else-if="selectedCabinetId" class="cab-empty">Таблица шкафа пуста. Распознайте паспорт и добавьте устройство.</div>

    <!-- Device card modal -->
    <Teleport to="body">
      <div v-if="cardModal" class="modal-overlay" @click.self="cardModal = false">
        <div class="card-modal panel">
          <div class="card-modal-head">
            <h2>Карточка устройства</h2>
            <button class="icon-btn close-btn" @click="cardModal = false">✕</button>
          </div>
          <div v-if="lastCard" class="card-fields">
            <div class="card-field"><span>Наименование</span><strong>{{ lastCard.name || '—' }}</strong></div>
            <div class="card-field"><span>Заводской номер</span><strong>{{ lastCard.serial_number || '—' }}</strong></div>
            <div class="card-field"><span>Децимальный номер</span><strong>{{ lastCard.decimal_number || '—' }}</strong></div>
            <div class="card-field"><span>Дата выпуска/приёмки</span><strong>{{ lastCard.production_date || '—' }}</strong></div>
            <div class="card-field"><span>Гарантийный срок</span><strong>{{ lastCard.warranty_period || '—' }}</strong></div>
          </div>
          <div class="card-modal-foot">
            <button class="ghost-button" @click="downloadCard">Скачать JSON</button>
            <button class="ghost-button" @click="downloadCardExcel">Скачать Excel</button>
            <button class="small-btn" @click="cardModal = false">Закрыть</button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

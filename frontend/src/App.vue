<script setup>
import { computed, reactive, ref } from 'vue'

const apiBase = ref('http://127.0.0.1:8000')
const file = ref(null)
const dragActive = ref(false)
const step = ref('idle')
const error = ref('')
const ocrText = ref('')
const llmData = ref(null)

const stats = reactive({
  symbols: 0,
  rows: 0,
  fields: 0
})

const timeline = computed(() => [
  {
    key: 'ocr',
    title: 'OCR extraction',
    text: 'Извлечение текста из PDF через /ocr/generate',
    state: step.value === 'ocr' ? 'active' : ocrText.value ? 'done' : 'idle'
  },
  {
    key: 'llm',
    title: 'LLM structuring',
    text: 'Преобразование OCR в JSON через /llm/generate-json',
    state: step.value === 'llm' ? 'active' : llmData.value ? 'done' : 'idle'
  }
])

const fileLabel = computed(() => file.value ? file.value.name : 'Перетащите PDF или выберите файл')

function selectFile(targetFile) {
  if (!targetFile) return
  error.value = ''
  llmData.value = null
  ocrText.value = ''
  stats.symbols = 0
  stats.rows = 0
  stats.fields = 0
  file.value = targetFile
}

function onFileChange(event) {
  selectFile(event.target.files?.[0] ?? null)
}

function onDrop(event) {
  dragActive.value = false
  selectFile(event.dataTransfer?.files?.[0] ?? null)
}

async function runPipeline() {
  if (!file.value) {
    error.value = 'Сначала выберите PDF-файл.'
    return
  }

  error.value = ''
  step.value = 'ocr'

  try {
    const formData = new FormData()
    formData.append('file', file.value)

    const ocrResponse = await fetch(`${apiBase.value}/ocr/generate`, {
      method: 'POST',
      body: formData
    })

    const ocrPayload = await ocrResponse.json()
    if (!ocrResponse.ok) {
      throw new Error(ocrPayload.detail || 'Не удалось выполнить OCR')
    }

    ocrText.value = ocrPayload.ocr_text
    stats.symbols = ocrText.value.length
    stats.rows = ocrText.value.split(/\n+/).filter(Boolean).length

    step.value = 'llm'

    const llmResponse = await fetch(`${apiBase.value}/llm/generate-json`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ocr_text: ocrText.value })
    })

    const llmPayload = await llmResponse.json()
    if (!llmResponse.ok) {
      throw new Error(llmPayload.detail || 'Не удалось получить JSON')
    }

    llmData.value = llmPayload.data
    stats.fields = countFields(llmData.value)
    step.value = 'done'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Неизвестная ошибка'
    step.value = 'error'
  }
}

function countFields(value) {
  if (Array.isArray(value)) {
    return value.reduce((total, item) => total + countFields(item), 0)
  }
  if (value && typeof value === 'object') {
    return Object.entries(value).reduce((total, [, nested]) => total + 1 + countFields(nested), 0)
  }
  return 0
}

function formatJson(value) {
  return JSON.stringify(value, null, 2)
}
</script>

<template>
  <div class="shell">
    <div class="ambient ambient-left"></div>
    <div class="ambient ambient-right"></div>

    <main class="layout">
      <section class="hero-panel panel">
        <div class="eyebrow">GazProm OCR Console</div>
        <h1>PDF in. Structured JSON out.</h1>
        <p class="lead">
          Инструмент для двухшаговой обработки документов: сначала OCR, затем извлечение структуры через LLM.
        </p>

        <div class="hero-grid">
          <article class="metric-card">
            <span>Symbols</span>
            <strong>{{ stats.symbols }}</strong>
          </article>
          <article class="metric-card">
            <span>Rows</span>
            <strong>{{ stats.rows }}</strong>
          </article>
          <article class="metric-card">
            <span>Fields</span>
            <strong>{{ stats.fields }}</strong>
          </article>
        </div>
      </section>

      <section class="control-panel panel">
        <label class="field-label" for="apiBase">API endpoint</label>
        <input id="apiBase" v-model="apiBase" class="text-input" type="text" />

        <label
          class="dropzone"
          :class="{ active: dragActive }"
          @dragenter.prevent="dragActive = true"
          @dragover.prevent="dragActive = true"
          @dragleave.prevent="dragActive = false"
          @drop.prevent="onDrop"
        >
          <input class="hidden-input" type="file" accept="application/pdf" @change="onFileChange" />
          <span class="dropzone-title">{{ fileLabel }}</span>
          <span class="dropzone-text">Один PDF, затем полный pipeline через API.</span>
        </label>

        <button class="run-button" @click="runPipeline">Запустить обработку</button>

        <p v-if="error" class="error-message">{{ error }}</p>
      </section>

      <section class="timeline-panel panel">
        <div v-for="item in timeline" :key="item.key" class="timeline-item" :data-state="item.state">
          <div class="timeline-dot"></div>
          <div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.text }}</p>
          </div>
        </div>
      </section>

      <section class="output-panel panel">
        <div class="section-head">
          <span>OCR text</span>
          <small>{{ ocrText ? 'Готово' : 'Ожидание' }}</small>
        </div>
        <pre>{{ ocrText || 'После загрузки PDF здесь появится текст из /ocr/generate.' }}</pre>
      </section>

      <section class="output-panel panel">
        <div class="section-head">
          <span>Structured JSON</span>
          <small>{{ llmData ? 'Готово' : 'Ожидание' }}</small>
        </div>
        <pre>{{ llmData ? formatJson(llmData) : 'После OCR здесь появится ответ /llm/generate-json.' }}</pre>
      </section>
    </main>
  </div>
</template>

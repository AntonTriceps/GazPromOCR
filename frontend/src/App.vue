<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { PDFDocument, degrees } from 'pdf-lib'
import * as XLSX from 'xlsx'
import VuePdfEmbed from 'vue-pdf-embed'
import CabinetManager from './CabinetManager.vue'

const apiBase = ref('http://127.0.0.1:8000')
const file = ref(null)
const editedFile = ref(null)
const dragActive = ref(false)
const step = ref('idle')
const error = ref('')
const ocrText = ref('')
const llmData = ref(null)
const pdfPreviewUrl = ref('')
const previewModalOpen = ref(false)
const progress = ref(0)
const pageCount = ref(0)
const editorOpen = ref(false)
const editorBusy = ref(false)
const editorError = ref('')
const rotationPreset = ref(90)
const nativeRotations = ref([])
const userRotations = ref([])
const pageCutLines = ref([])
const editedFileName = ref('')
const dataEditorText = ref('')
const dataEditorError = ref('')

const feedbackOpen = ref(false)
const feedbackSent = ref(false)
const feedbackType = ref(null) // 'pos' or 'neg'
const feedbackComment = ref('')
const feedbackBusy = ref(false)

function getTotalRotation(index) {
  const native = nativeRotations.value[index] || 0
  const user = userRotations.value[index] || 0
  return normalizeRotation(native + user)
}

// Removed zoom functions

const stats = reactive({
  symbols: 0,
  rows: 0,
  fields: 0
})

const fileLabel = computed(() => (file.value ? file.value.name : 'Перетащите PDF сюда или выберите файл'))
const fileSizeLabel = computed(() => {
  if (!file.value) return ''
  const sizeInMb = file.value.size / (1024 * 1024)
  return `${sizeInMb.toFixed(2)} MB`
})
const statusLabel = computed(() => {
  if (step.value === 'ocr' || step.value === 'llm') return 'Обработка файла...'
  if (step.value === 'done') return 'Готово'
  if (step.value === 'error') return 'Возникла ошибка'
  if (file.value) return 'Файл загружен'
  return 'Ожидание файла'
})
const hasResult = computed(() => Boolean(ocrText.value || llmData.value))
const canOpenEditor = computed(() => Boolean(file.value && pdfPreviewUrl.value))
const editorSummary = computed(() => {
  if (!nativeRotations.value.length) return 'Страницы ещё не загружены'

  const rotatedCount = userRotations.value.filter((rotation) => rotation % 360 !== 0).length
  const slicedCount = pageCutLines.value.filter((cuts) => cuts.length > 0).length
  const extraPages = pageCutLines.value.reduce((sum, cuts) => sum + cuts.length, 0)

  const parts = [`Подготовлено ${nativeRotations.value.length} стр.`]
  if (rotatedCount) parts.push(`изменен поворот: ${rotatedCount}`)
  if (slicedCount) parts.push(`разрезано: ${slicedCount}`)
  if (extraPages) parts.push(`новых фрагментов: +${extraPages}`)

  return parts.join(' • ')
})

function resetResults() {
  llmData.value = null
  ocrText.value = ''
  stats.symbols = 0
  stats.rows = 0
  stats.fields = 0
  step.value = 'idle'
}

function revokePreviewUrl() {
  if (pdfPreviewUrl.value) {
    URL.revokeObjectURL(pdfPreviewUrl.value)
    pdfPreviewUrl.value = ''
  }
}

function resetEditorState() {
  editorOpen.value = false
  editorBusy.value = false
  editorError.value = ''
  rotationPreset.value = 90
  nativeRotations.value = []
  userRotations.value = []
  pageCutLines.value = []
  editedFileName.value = ''
}

function normalizeRotation(value) {
  return ((value % 360) + 360) % 360
}

async function prepareEditorState(targetFile = file.value) {
  if (!targetFile) return
  editorBusy.value = true
  editorError.value = ''

  try {
    const bytes = await targetFile.arrayBuffer()
    const pdfDoc = await PDFDocument.load(bytes)
    const pages = pdfDoc.getPages()

    nativeRotations.value = pages.map((page) => normalizeRotation(page.getRotation().angle))
    userRotations.value = pages.map(() => 0)
    pageCutLines.value = pages.map(() => [])
    editedFileName.value = targetFile.name.replace(/\.pdf$/i, '')
  } catch (err) {
    nativeRotations.value = []
    userRotations.value = []
    pageCutLines.value = []
    editorError.value = err instanceof Error ? err.message : 'Не удалось открыть PDF для редактирования'
  } finally {
    editorBusy.value = false
  }
}

function selectFile(targetFile) {
  if (!targetFile) return
  if (targetFile.type !== 'application/pdf') {
    error.value = 'Пожалуйста, загрузите PDF-файл.'
    return
  }

  error.value = ''
  resetResults()
  revokePreviewUrl()
  resetEditorState()
  file.value = targetFile
  editedFile.value = null
  pdfPreviewUrl.value = URL.createObjectURL(targetFile)
  void prepareEditorState(targetFile)
}

function onFileChange(event) {
  selectFile(event.target.files?.[0] ?? null)
}

function onDrop(event) {
  dragActive.value = false
  selectFile(event.dataTransfer?.files?.[0] ?? null)
}

function openEditor() {
  if (!canOpenEditor.value) return
  editorOpen.value = true
  editorError.value = ''
  if (!nativeRotations.value.length) {
    void prepareEditorState()
  }
}

function closeEditor() {
  editorOpen.value = false
}

function rotatePage(index, delta) {
  userRotations.value[index] = normalizeRotation((userRotations.value[index] || 0) + delta)
}

function getCutAxis(index) {
  const rot = userRotations.value[index] || 0
  return (rot === 90 || rot === 270) ? 'y' : 'x'
}

function getCutStyle(index, pdfXPct) {
  const pctString = `${(pdfXPct * 100).toFixed(2)}%`
  // Мы всегда используем физическую координату X страницы. 
  // Браузер сам повернет линию вместе с контейнером.
  return { left: pctString }
}

function addCutLine(index, event) {
  const target = event.currentTarget
  // Теперь всё просто: режем по визуальной горизонтали экрана
  const rect = target.getBoundingClientRect()
  const visualPct = (event.clientX - rect.left) / rect.width
  const pct = Math.max(0, Math.min(1, Number(visualPct.toFixed(4))))

  if (pct > 0.02 && pct < 0.98) {
    pageCutLines.value[index].push(pct)
    pageCutLines.value[index].sort((a, b) => a - b)
  }
}

function removeCutLine(index, lineIndex) {
  pageCutLines.value[index].splice(lineIndex, 1)
}

async function buildEditedPdf() {
  const sourceBytes = await file.value.arrayBuffer()
  const sourcePdf = await PDFDocument.load(sourceBytes)
  const targetPdf = await PDFDocument.create()
  const sourcePages = sourcePdf.getPages()

  for (const [index, page] of sourcePages.entries()) {
    const cuts = pageCutLines.value[index] || []
    const width = page.getWidth()
    const height = page.getHeight()
    const rot = userRotations.value[index] || 0

    if (cuts.length === 0) {
      const [copiedPage] = await targetPdf.copyPages(sourcePdf, [index])
      copiedPage.setRotation(degrees(getTotalRotation(index)))
      targetPdf.addPage(copiedPage)
      continue
    }

    const sections = [0.0, ...cuts, 1.0]

    for (let i = 0; i < sections.length - 1; i++) {
      const pStart = sections[i]
      const pEnd = sections[i + 1]

      let pdfLeft = 0, pdfRight = width, pdfBottom = 0, pdfTop = height
      
      if (rot === 0 || rot === 180) {
        // Режем по ширине (физическая ось X)
        // 0°: Визуальное Лево = Физический Лево (0)
        // 180°: Визуальное Лево = Физический Право (W)
        const vStart = (rot === 0) ? pStart : 1.0 - pStart
        const vEnd = (rot === 0) ? pEnd : 1.0 - pEnd
        pdfLeft = Math.max(0, Math.min(width, width * Math.min(vStart, vEnd)))
        pdfRight = Math.max(0, Math.min(width, width * Math.max(vStart, vEnd)))
      } else {
        // Режем по высоте (физическая ось Y)
        // 90° (CW): Визуальное Лево = Физический Низ (0)
        // 270° (CCW): Визуальное Лево = Физический Верх (H)
        const vStart = (rot === 270) ? 1.0 - pStart : pStart
        const vEnd = (rot === 270) ? 1.0 - pEnd : pEnd
        pdfBottom = Math.max(0, Math.min(height, height * Math.min(vStart, vEnd)))
        pdfTop = Math.max(0, Math.min(height, height * Math.max(vStart, vEnd)))
      }

      const partWidth = Math.max(1, pdfRight - pdfLeft)
      const partHeight = Math.max(1, pdfTop - pdfBottom)

      const embeddedPage = await targetPdf.embedPage(page, {
        left: pdfLeft,
        right: pdfRight,
        bottom: pdfBottom,
        top: pdfTop
      })

      const newPage = targetPdf.addPage([partWidth, partHeight])
      newPage.drawPage(embeddedPage, { x: 0, y: 0 })
      
      const totalRotation = getTotalRotation(index)
      newPage.setRotation(degrees(totalRotation))
    }
  }

  return targetPdf.save()
}

async function applyPdfEdits() {
  if (!file.value) return

  editorBusy.value = true
  editorError.value = ''

  try {
    const editedPdf = await buildEditedPdf()
    const nextFileName = `${editedFileName.value || 'document'}-edited.pdf`
    const nextFile = new File([editedPdf], nextFileName, { type: 'application/pdf' })

    editedFile.value = nextFile

    resetResults()
    closeEditor()
  } catch (err) {
    editorError.value = err instanceof Error ? err.message : 'Не удалось сохранить изменения'
  } finally {
    editorBusy.value = false
  }
}

async function runPipeline() {
  error.value = ''
  step.value = 'ocr'
  progress.value = 5

  const progInterval = setInterval(() => {
    if (step.value === 'ocr' && progress.value < 45) progress.value += 1
    if (step.value === 'llm' && progress.value < 90) progress.value += 1
  }, 400)

  try {
    const formData = new FormData()
    formData.append('file', editedFile.value || file.value)

    const ocrResponse = await fetch(`${apiBase.value}/ocr/generate`, {
      method: 'POST',
      body: formData
    })

    const ocrPayload = await ocrResponse.json()
    if (!ocrResponse.ok) {
      throw new Error(ocrPayload.detail || 'Не удалось обработать файл')
    }

    ocrText.value = ocrPayload.ocr_text
    pageCount.value = ocrPayload.page_count || 0
    stats.symbols = ocrText.value.length
    stats.rows = ocrText.value.split(/\n+/).filter(Boolean).length

    step.value = 'llm'
    progress.value = 50

    const llmResponse = await fetch(`${apiBase.value}/llm/generate-json`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ocr_text: ocrText.value })
    })

    const llmPayload = await llmResponse.json()
    if (!llmResponse.ok) {
      throw new Error(llmPayload.detail || 'Не удалось подготовить результат')
    }

    llmData.value = llmPayload.data
    stats.fields = countFields(llmData.value)
    progress.value = 100
    step.value = 'done'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Неизвестная ошибка'
    step.value = 'error'
  } finally {
    clearInterval(progInterval)
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

function flattenJsonToRows(value, path = '', rows = []) {
  if (Array.isArray(value)) {
    if (!value.length) {
      rows.push({ path, value: '[]' })
      return rows
    }
    value.forEach((item, index) => {
      const nextPath = path ? `${path}[${index}]` : `[${index}]`
      flattenJsonToRows(item, nextPath, rows)
    })
    return rows
  }

  if (value && typeof value === 'object') {
    const entries = Object.entries(value)
    if (!entries.length) {
      rows.push({ path, value: '{}' })
      return rows
    }
    entries.forEach(([key, nested]) => {
      const nextPath = path ? `${path}.${key}` : key
      flattenJsonToRows(nested, nextPath, rows)
    })
    return rows
  }

  rows.push({ path, value: value ?? '' })
  return rows
}

function downloadBlob(content, fileName, type) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  URL.revokeObjectURL(url)
}

function downloadOcr() {
  if (!ocrText.value) return
  const baseName = file.value?.name?.replace(/\.pdf$/i, '') || 'result'
  downloadBlob(ocrText.value, `${baseName}-text.txt`, 'text/plain;charset=utf-8')
}

function downloadJson() {
  if (!llmData.value) return
  const baseName = file.value?.name?.replace(/\.pdf$/i, '') || 'result'
  downloadBlob(formatJson(llmData.value), `${baseName}-data.json`, 'application/json;charset=utf-8')
}

function downloadExcel() {
  if (!llmData.value) return

  const baseName = file.value?.name?.replace(/\.pdf$/i, '') || 'result'
  const rows = flattenJsonToRows(llmData.value)
  const worksheet = XLSX.utils.json_to_sheet(rows.length ? rows : [{ path: '', value: '' }])
  const workbook = XLSX.utils.book_new()

  XLSX.utils.book_append_sheet(workbook, worksheet, 'Data')

  const buffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' })
  downloadBlob(
    buffer,
    `${baseName}-data.xlsx`,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  )
}

function applyDataEdits() {
  if (!dataEditorText.value.trim()) {
    dataEditorError.value = 'Поле данных не должно быть пустым.'
    return
  }

  try {
    const parsed = JSON.parse(dataEditorText.value)
    llmData.value = parsed
    stats.fields = countFields(parsed)
    dataEditorText.value = formatJson(parsed)
    dataEditorError.value = ''
  } catch (err) {
    dataEditorError.value = err instanceof Error ? err.message : 'Некорректный JSON'
  }
}

function resetDataEdits() {
  dataEditorText.value = llmData.value ? formatJson(llmData.value) : ''
  dataEditorError.value = ''
}

function formatDataEdits() {
  try {
    const parsed = JSON.parse(dataEditorText.value)
    dataEditorText.value = formatJson(parsed)
    dataEditorError.value = ''
  } catch (err) {
    dataEditorError.value = err instanceof Error ? err.message : 'Некорректный JSON'
  }
}


async function submitFeedback() {
  if (feedbackBusy.value) return
  feedbackBusy.value = true
  try {
    const res = await fetch(`${apiBase.value}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        is_positive: feedbackType.value === 'pos',
        comment: feedbackComment.value
      })
    })
    if (res.ok) {
      feedbackSent.value = true
      setTimeout(() => {
        feedbackOpen.value = false
        feedbackSent.value = false
        feedbackType.value = null
        feedbackComment.value = ''
      }, 2000)
    }
  } catch (err) {
    console.error('Feedback failed', err)
  } finally {
    feedbackBusy.value = false
  }
}

onBeforeUnmount(() => {
  revokePreviewUrl()
})

watch(
  llmData,
  (value) => {
    dataEditorText.value = value ? formatJson(value) : ''
    dataEditorError.value = ''
  },
  { immediate: true }
)
</script>

<template>
  <div class="shell">
    <div class="brand-orb brand-orb-left"></div>
    <div class="brand-orb brand-orb-right"></div>

    <main class="layout">
      <section class="topbar">
        <div>
          <div class="eyebrow">GazProm OCR</div>
          <h1>Преобразование тех.паспорта</h1>
          <p class="lead">Специально для Газпром</p>
        </div>
        <div class="status-pill">{{ statusLabel }}</div>
      </section>

      <section class="workspace panel">
        <div class="workspace-grid">
          <div class="upload-side">
            <label
              class="dropzone"
              :class="{ active: dragActive }"
              @dragenter.prevent="dragActive = true"
              @dragover.prevent="dragActive = true"
              @dragleave.prevent="dragActive = false"
              @drop.prevent="onDrop"
            >
              <input class="hidden-input" type="file" accept="application/pdf" @change="onFileChange" />
              <div class="dropzone-icon">PDF</div>
              <span class="dropzone-title">{{ fileLabel }}</span>
              <span class="dropzone-text">{{ fileSizeLabel }}</span>
            </label>

            <div v-if="file" class="editor-card">
              <div>
                <strong>Редактор PDF</strong>
                <p>Перед OCR можно визуально поправить ориентацию страниц и разрезать длинные склеенные страницы.</p>
                <small>{{ editorSummary }}</small>
              </div>
              <button class="ghost-button" :disabled="!canOpenEditor" @click="openEditor">Редактировать</button>
            </div>

            <div class="action-row">
              <button class="run-button" :disabled="step === 'ocr' || step === 'llm' || !file" @click="runPipeline">Распознать документ</button>
            </div>

            <div v-if="step === 'ocr' || step === 'llm'" class="progress-wrap">
              <div class="progress-labels">
                <span>{{ step === 'ocr' ? 'Распознавание (OCR)...' : 'Извлечение данных (AI)...' }}</span>
                <span>{{ progress }}%</span>
              </div>
              <div class="progress-bar-bg">
                <div class="progress-bar-fill" :style="{ width: progress + '%' }"></div>
              </div>
            </div>

            <div v-if="hasResult" class="mini-stats">
              <article class="metric-card">
                <span>Символов</span>
                <strong>{{ stats.symbols }}</strong>
              </article>
              <article class="metric-card">
                <span>Строк</span>
                <strong>{{ stats.rows }}</strong>
              </article>
              <article class="metric-card">
                <span>Полей</span>
                <strong>{{ stats.fields }}</strong>
              </article>
            </div>

            <p v-if="error" class="error-message">{{ error }}</p>
          </div>

          <div class="preview-side">
            <div v-if="pdfPreviewUrl" class="pdf-container">
              <div class="pdf-toolbar">
                <div class="toolbar-group">
                  <button class="small-btn" @click="previewModalOpen = true">Развернуть</button>
                </div>
                <div class="toolbar-group">
                  <button class="small-btn" :disabled="!canOpenEditor" @click="openEditor">Редактировать PDF</button>
                </div>
              </div>

              <div class="pdf-frame-wrap main-preview-wrap">
                <VuePdfEmbed :source="pdfPreviewUrl" class="custom-pdf" />
              </div>
            </div>
            <div v-else class="empty-state">
              Загрузите PDF, чтобы увидеть его здесь.
            </div>
          </div>
        </div>
      </section>

      <CabinetManager :api-base="apiBase" :llm-data="llmData" :page-count="pageCount" />

      <section class="results panel">
        <div class="section-head results-head">
          <div>
            <span>Результат</span>
            <small>{{ hasResult ? 'Текст и структурированные данные готовы' : 'После обработки здесь появятся данные' }}</small>
          </div>
          <div class="action-row compact">
            <button class="ghost-button" :disabled="!ocrText" @click="downloadOcr">Скачать текст</button>
            <button class="ghost-button" :disabled="!llmData" @click="downloadJson">Скачать JSON</button>
            <button class="ghost-button" :disabled="!llmData" @click="downloadExcel">Скачать Excel</button>
          </div>
        </div>

        <div class="results-grid">
          <div class="result-block">
            <h2>Текст из документа</h2>
            <pre>{{ ocrText || 'Здесь появится распознанный текст.' }}</pre>
          </div>
          <div class="result-block">
            <h2>Данные</h2>
            <div v-if="llmData" class="data-editor-wrap">
              <textarea
                v-model="dataEditorText"
                class="data-editor"
                spellcheck="false"
                placeholder="Здесь появятся подготовленные данные."
              ></textarea>
              <div class="action-row compact">
                <button class="small-btn" @click="formatDataEdits">Форматировать</button>
                <button class="small-btn" @click="resetDataEdits">Сбросить</button>
                <button class="run-button compact-btn" @click="applyDataEdits">Применить</button>
              </div>
              <p v-if="dataEditorError" class="error-message">{{ dataEditorError }}</p>
            </div>
            <pre v-else>Здесь появятся подготовленные данные.</pre>
          </div>
        </div>
      </section>
    </main>

    <div v-if="editorOpen" class="modal-overlay" @click.self="closeEditor">
      <section class="editor-modal panel">
        <div class="editor-header">
          <div>
            <div class="eyebrow">Визуальный редактор PDF</div>
            <h2>Подготовка документа перед OCR</h2>
            <p class="lead editor-lead">
              Внутри редактора показан реальный предпросмотр страниц. Здесь можно повернуть страницу и применить инструмент «Ножницы», чтобы разрезать склеенную страницу на 2 или 3 части.
            </p>
          </div>
          <button class="icon-btn close-btn" @click="closeEditor">✕</button>
        </div>

        <div class="editor-toolbar simplified">
          <div class="toolbar-group wrap">
            <span class="toolbar-label">Шаг поворота:</span>
            <button
              v-for="preset in [90, 180, 270]"
              :key="preset"
              class="small-btn"
              :class="{ active: rotationPreset === preset }"
              @click="rotationPreset = preset"
            >
              {{ preset }}°
            </button>
          </div>
          <div class="toolbar-group wrap">
            <span class="toolbar-label">Ножницы:</span>
            <span class="toolbar-hint">кликните по странице, чтобы провести <b>вертикальную</b> линию (для нарезки сканов книжных разворотов или столбцов)</span>
          </div>
        </div>

        <p v-if="editorError" class="error-message">{{ editorError }}</p>
        <div v-if="editorBusy" class="editor-loading">Подготавливаем документ...</div>

        <div v-else class="editor-grid">
          <article v-for="(nativeRot, index) in nativeRotations" :key="index" class="page-card">
            <div class="page-card-head">
              <div>
                <strong>Страница {{ index + 1 }}</strong>
                <small v-if="pageCutLines[index]?.length">Разрезана на {{ pageCutLines[index].length + 1 }} частей</small>
              </div>
              <div class="page-actions">
                <button class="small-btn" @click="rotatePage(index, -rotationPreset)">↺</button>
                <button class="small-btn" @click="rotatePage(index, rotationPreset)">↻</button>
              </div>
            </div>

            <div class="editor-page-preview slicer-mode">
              <!-- Документ, который крутится -->
              <div class="page-render-wrap" :style="{ transform: `rotate(${userRotations[index] || 0}deg)` }">
                <VuePdfEmbed
                  :source="pdfPreviewUrl"
                  :page="index + 1"
                  :scale="1.5"
                  class="editor-pdf-page high-res"
                />
              </div>
              <!-- Слой ножниц, который ВСЕГДА стоит ровно -->
              <div class="slicer-overlay fixed-overlay" @click.self="addCutLine(index, $event)">
                <div 
                  v-for="(cut, cIndex) in pageCutLines[index]" 
                  :key="cIndex" 
                  class="cut-line cut-axis-x" 
                  :style="{ left: `${(cut * 100).toFixed(2)}%` }"
                >
                  <button class="cut-line-delete" @click.stop="removeCutLine(index, cIndex)">✕</button>
                </div>
              </div>
            </div>
          </article>
        </div>

        <div class="editor-footer">
          <div>
            <strong>{{ editorSummary }}</strong>
            <p>После сохранения будет создан новый PDF, который пойдёт в OCR вместо исходного файла.</p>
          </div>
          <div class="action-row compact">
            <button class="ghost-button" @click="closeEditor">Отмена</button>
            <button class="run-button" :disabled="editorBusy || !nativeRotations.length" @click="applyPdfEdits">
              Сохранить исправленный PDF
            </button>
          </div>
        </div>
      </section>
    </div>

    <!-- Fullscreen PDF Preview Modal -->
    <Teleport to="body">
      <div v-if="previewModalOpen" class="modal-overlay" @click.self="previewModalOpen = false">
        <section class="editor-modal fullscreen-pdf-modal panel">
          <div class="editor-header">
            <div>
              <div class="eyebrow">Просмотр документа</div>
              <h2>Оригинальный PDF</h2>
            </div>
            <button class="icon-btn close-btn" @click="previewModalOpen = false">✕</button>
          </div>
          <div class="fullscreen-pdf-wrap">
            <VuePdfEmbed :source="pdfPreviewUrl" class="custom-pdf-fullscreen" />
          </div>
        </section>
      </div>
    </Teleport>

    <!-- Feedback Widget -->
    <div class="feedback-widget" :class="{ open: feedbackOpen }">
      <button v-if="!feedbackOpen" class="feedback-toggle" @click="feedbackOpen = true">
        Обратная связь
      </button>
      
      <div v-else class="feedback-popover panel">
        <div v-if="!feedbackSent">
          <h3>Вам нравится сервис?</h3>
          <div class="feedback-actions">
            <button 
              class="feedback-btn pos" 
              :class="{ active: feedbackType === 'pos' }"
              @click="feedbackType = 'pos'; submitFeedback()"
            >👍</button>
            <button 
              class="feedback-btn neg" 
              :class="{ active: feedbackType === 'neg' }"
              @click="feedbackType = 'neg'"
            >👎</button>
          </div>
          
          <div v-if="feedbackType === 'neg'" class="feedback-details">
            <textarea 
              v-model="feedbackComment" 
              placeholder="Что нам стоит улучшить?"
              rows="3"
            ></textarea>
            <button 
              class="run-button compact" 
              :disabled="feedbackBusy"
              @click="submitFeedback"
            >Отправить</button>
          </div>
          
          <button class="feedback-close" @click="feedbackOpen = false">✕</button>
        </div>
        <div v-else class="feedback-thanks">
          <div class="thanks-icon">✨</div>
          <p>Спасибо за отзыв!</p>
        </div>
      </div>
    </div>
  </div>
</template>

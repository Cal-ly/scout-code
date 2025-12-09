# Web Interface - Claude Code Instructions

**Version:** 2.0 (PoC Aligned)  
**Updated:** November 26, 2025  
**Status:** Ready for Implementation  
**Priority:** Phase 3 - Integration (Build Last)

---

## PoC Scope Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Job text paste input | ✅ In Scope | Textarea for raw text |
| Process button | ✅ In Scope | Trigger pipeline |
| Progress display | ✅ In Scope | Polling-based updates |
| Results display | ✅ In Scope | Compatibility score, strategy |
| PDF download links | ✅ In Scope | CV and cover letter |
| Toast notifications | ✅ In Scope | Success/error feedback |
| Basic error display | ✅ In Scope | User-friendly messages |
| Real-time WebSocket | ❌ Deferred | Polling sufficient |
| Job history page | ❌ Deferred | Single job workflow |
| Analytics dashboard | ❌ Deferred | Not needed for PoC |
| Settings page | ❌ Deferred | Environment config only |
| Profile editing UI | ❌ Deferred | Manual YAML editing |

---

## Context & Objective

Build the **Web Interface** for Scout - a simple single-page application that allows users to paste job postings and receive tailored application materials.

### Why This Interface Exists

The Web Interface provides:
- User-friendly input for job postings
- Visual feedback during processing
- Display of analysis results
- Download access to generated PDFs

Simple Vue.js frontend with polling for updates.

---

## Technical Requirements

### Dependencies

```json
{
  "dependencies": {
    "vue": "^3.4",
    "axios": "^1.6",
    "tailwindcss": "^3.4"
  }
}
```

### File Structure

```
scout/
├── frontend/
│   ├── src/
│   │   ├── App.vue              # Main application
│   │   ├── components/
│   │   │   ├── JobInput.vue     # Job text input
│   │   │   ├── ProcessButton.vue # Submit button
│   │   │   ├── ProgressDisplay.vue # Progress bar
│   │   │   ├── ResultsDisplay.vue  # Analysis results
│   │   │   ├── DownloadLinks.vue   # PDF downloads
│   │   │   └── ToastNotification.vue # Notifications
│   │   ├── api/
│   │   │   └── client.js        # API client
│   │   └── stores/
│   │       └── pipeline.js      # Pipeline state
│   ├── index.html
│   └── tailwind.config.js
├── app/
│   └── api/
│       └── routes/
│           ├── pipeline.py      # Pipeline endpoints
│           └── files.py         # File download endpoints
└── tests/
    └── frontend/
        └── components/
```

---

## API Endpoints

### Pipeline Routes

Create `app/api/routes/pipeline.py`:

```python
"""
Pipeline API Routes

Endpoints for job processing.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path

from app.models.pipeline import PipelineInput, PipelineResult, PipelineStatus
from app.services.pipeline import PipelineOrchestrator, create_pipeline_orchestrator
from app.services.notification import get_notification_service

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# Store active pipelines (in-memory for PoC)
_active_pipelines: dict[str, PipelineResult] = {}


@router.post("/process", response_model=dict)
async def start_pipeline(
    input_data: PipelineInput,
    background_tasks: BackgroundTasks
) -> dict:
    """
    Start job processing pipeline.
    
    Returns pipeline_id for status polling.
    """
    # Get services (would use dependency injection in production)
    from app.services.llm import get_llm_service
    from app.services.vector_store import get_vector_store
    from app.core.collector import create_collector
    
    llm = await get_llm_service()
    vs = await get_vector_store()
    collector = await create_collector(vs)
    
    orchestrator = await create_pipeline_orchestrator(collector, llm, vs)
    
    # Start processing in background
    async def run_pipeline():
        notification_service = get_notification_service()
        
        result = await orchestrator.execute(input_data)
        _active_pipelines[result.pipeline_id] = result
        
        # Send notification
        if result.is_success:
            notification_service.notify_pipeline_completed(
                result.pipeline_id,
                result.job_title or "Job",
                result.company_name or "Company",
                result.compatibility_score or 0
            )
        else:
            notification_service.notify_pipeline_failed(
                result.pipeline_id,
                result.error or "Unknown error"
            )
    
    # For PoC, run synchronously (background would need task queue)
    result = await orchestrator.execute(input_data)
    _active_pipelines[result.pipeline_id] = result
    
    notification_service = get_notification_service()
    if result.is_success:
        notification_service.notify_pipeline_completed(
            result.pipeline_id,
            result.job_title or "Job",
            result.company_name or "Company",
            result.compatibility_score or 0
        )
    else:
        notification_service.notify_pipeline_failed(
            result.pipeline_id,
            result.error or "Unknown error"
        )
    
    return {"pipeline_id": result.pipeline_id}


@router.get("/status/{pipeline_id}", response_model=PipelineResult)
async def get_pipeline_status(pipeline_id: str) -> PipelineResult:
    """Get pipeline execution status."""
    if pipeline_id not in _active_pipelines:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    return _active_pipelines[pipeline_id]


@router.get("/download/{pipeline_id}/{document_type}")
async def download_document(
    pipeline_id: str,
    document_type: str  # "cv" or "cover_letter"
) -> FileResponse:
    """Download generated document."""
    if pipeline_id not in _active_pipelines:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    result = _active_pipelines[pipeline_id]
    
    if not result.is_success:
        raise HTTPException(status_code=400, detail="Pipeline did not complete successfully")
    
    if document_type == "cv":
        file_path = result.cv_path
        filename = f"{result.company_name}_CV.pdf"
    elif document_type == "cover_letter":
        file_path = result.cover_letter_path
        filename = f"{result.company_name}_Cover_Letter.pdf"
    else:
        raise HTTPException(status_code=400, detail="Invalid document type")
    
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf"
    )
```

---

## Frontend Components

### Main App

Create `frontend/src/App.vue`:

```vue
<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm">
      <div class="max-w-4xl mx-auto px-4 py-4">
        <h1 class="text-2xl font-bold text-gray-900">Scout</h1>
        <p class="text-gray-600">Intelligent Job Application Generator</p>
      </div>
    </header>
    
    <!-- Main Content -->
    <main class="max-w-4xl mx-auto px-4 py-8">
      <!-- Input Section -->
      <section v-if="!isProcessing && !result" class="space-y-6">
        <JobInput v-model="jobText" />
        <ProcessButton 
          :disabled="!canProcess" 
          @click="startProcessing" 
        />
      </section>
      
      <!-- Progress Section -->
      <section v-if="isProcessing" class="space-y-6">
        <ProgressDisplay 
          :status="pipelineStatus" 
          :current-step="currentStep"
          :steps-completed="stepsCompleted"
        />
      </section>
      
      <!-- Results Section -->
      <section v-if="result && result.is_success" class="space-y-6">
        <ResultsDisplay :result="result" />
        <DownloadLinks :pipeline-id="result.pipeline_id" />
        <button 
          @click="reset"
          class="w-full py-3 bg-gray-200 hover:bg-gray-300 rounded-lg"
        >
          Process Another Job
        </button>
      </section>
      
      <!-- Error Section -->
      <section v-if="result && !result.is_success" class="space-y-6">
        <div class="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 class="text-lg font-semibold text-red-800">Processing Failed</h3>
          <p class="text-red-700 mt-2">{{ result.error }}</p>
        </div>
        <button 
          @click="reset"
          class="w-full py-3 bg-gray-200 hover:bg-gray-300 rounded-lg"
        >
          Try Again
        </button>
      </section>
    </main>
    
    <!-- Toast Notifications -->
    <ToastNotification />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import JobInput from './components/JobInput.vue';
import ProcessButton from './components/ProcessButton.vue';
import ProgressDisplay from './components/ProgressDisplay.vue';
import ResultsDisplay from './components/ResultsDisplay.vue';
import DownloadLinks from './components/DownloadLinks.vue';
import ToastNotification from './components/ToastNotification.vue';
import { startPipeline, getPipelineStatus } from './api/client';

const jobText = ref('');
const isProcessing = ref(false);
const pipelineId = ref(null);
const pipelineStatus = ref('pending');
const currentStep = ref(null);
const stepsCompleted = ref(0);
const result = ref(null);

const canProcess = computed(() => jobText.value.length >= 100);

async function startProcessing() {
  isProcessing.value = true;
  result.value = null;
  
  try {
    const response = await startPipeline(jobText.value);
    pipelineId.value = response.pipeline_id;
    
    // Poll for status
    await pollStatus();
  } catch (error) {
    console.error('Failed to start pipeline:', error);
    isProcessing.value = false;
  }
}

async function pollStatus() {
  const maxAttempts = 60; // 1 minute max
  let attempts = 0;
  
  while (attempts < maxAttempts) {
    try {
      const status = await getPipelineStatus(pipelineId.value);
      
      pipelineStatus.value = status.status;
      currentStep.value = status.current_step;
      stepsCompleted.value = status.steps.filter(s => s.status === 'completed').length;
      
      if (status.status === 'completed' || status.status === 'failed') {
        result.value = status;
        isProcessing.value = false;
        return;
      }
      
      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, 1000));
      attempts++;
    } catch (error) {
      console.error('Poll error:', error);
      attempts++;
    }
  }
  
  // Timeout
  isProcessing.value = false;
}

function reset() {
  jobText.value = '';
  result.value = null;
  pipelineId.value = null;
}
</script>
```

### Job Input Component

Create `frontend/src/components/JobInput.vue`:

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-6">
    <label class="block text-sm font-medium text-gray-700 mb-2">
      Paste Job Posting
    </label>
    <textarea
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
      rows="12"
      class="w-full border border-gray-300 rounded-lg p-4 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      placeholder="Paste the full job posting text here...

Include:
- Job title
- Company name
- Requirements
- Responsibilities
- etc."
    ></textarea>
    <p class="mt-2 text-sm text-gray-500">
      {{ modelValue.length }} characters
      <span v-if="modelValue.length < 100" class="text-amber-600">
        (minimum 100 required)
      </span>
    </p>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true
  }
});

defineEmits(['update:modelValue']);
</script>
```

### Process Button Component

Create `frontend/src/components/ProcessButton.vue`:

```vue
<template>
  <button
    @click="$emit('click')"
    :disabled="disabled"
    class="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 
           text-white font-semibold rounded-lg transition-colors"
  >
    <span v-if="!disabled">Generate Application</span>
    <span v-else>Enter job posting text (100+ characters)</span>
  </button>
</template>

<script setup>
defineProps({
  disabled: {
    type: Boolean,
    default: false
  }
});

defineEmits(['click']);
</script>
```

### Progress Display Component

Create `frontend/src/components/ProgressDisplay.vue`:

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-6">
    <h3 class="text-lg font-semibold text-gray-900 mb-4">Processing...</h3>
    
    <!-- Progress Bar -->
    <div class="w-full bg-gray-200 rounded-full h-3 mb-4">
      <div 
        class="bg-blue-600 h-3 rounded-full transition-all duration-500"
        :style="{ width: progressPercent + '%' }"
      ></div>
    </div>
    
    <!-- Steps -->
    <div class="space-y-3">
      <div 
        v-for="(step, index) in steps" 
        :key="step.id"
        class="flex items-center gap-3"
      >
        <!-- Status Icon -->
        <div 
          class="w-8 h-8 rounded-full flex items-center justify-center"
          :class="getStepClass(index)"
        >
          <span v-if="index < stepsCompleted">✓</span>
          <span v-else-if="currentStep === step.id" class="animate-spin">⟳</span>
          <span v-else>{{ index + 1 }}</span>
        </div>
        
        <!-- Label -->
        <span :class="{ 'text-gray-400': index > stepsCompleted }">
          {{ step.label }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  status: String,
  currentStep: String,
  stepsCompleted: Number
});

const steps = [
  { id: 'rinser', label: 'Processing job posting...' },
  { id: 'analyzer', label: 'Analyzing compatibility...' },
  { id: 'creator', label: 'Generating content...' },
  { id: 'formatter', label: 'Creating PDFs...' }
];

const progressPercent = computed(() => (props.stepsCompleted / steps.length) * 100);

function getStepClass(index) {
  if (index < props.stepsCompleted) {
    return 'bg-green-500 text-white';
  } else if (steps[index].id === props.currentStep) {
    return 'bg-blue-500 text-white';
  }
  return 'bg-gray-200 text-gray-500';
}
</script>
```

### Results Display Component

Create `frontend/src/components/ResultsDisplay.vue`:

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-6">
    <h3 class="text-lg font-semibold text-gray-900 mb-4">Analysis Results</h3>
    
    <!-- Job Info -->
    <div class="mb-6">
      <h4 class="text-xl font-bold text-gray-900">{{ result.job_title }}</h4>
      <p class="text-gray-600">{{ result.company_name }}</p>
    </div>
    
    <!-- Compatibility Score -->
    <div class="mb-6">
      <div class="flex items-center justify-between mb-2">
        <span class="text-gray-700">Compatibility Score</span>
        <span class="text-2xl font-bold" :class="scoreColorClass">
          {{ Math.round(result.compatibility_score) }}%
        </span>
      </div>
      <div class="w-full bg-gray-200 rounded-full h-4">
        <div 
          class="h-4 rounded-full transition-all duration-500"
          :class="scoreBarClass"
          :style="{ width: result.compatibility_score + '%' }"
        ></div>
      </div>
    </div>
    
    <!-- Match Level -->
    <div class="p-4 rounded-lg" :class="matchLevelBgClass">
      <p class="font-semibold" :class="matchLevelTextClass">
        {{ matchLevelLabel }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  result: {
    type: Object,
    required: true
  }
});

const scoreColorClass = computed(() => {
  const score = props.result.compatibility_score;
  if (score >= 85) return 'text-green-600';
  if (score >= 70) return 'text-blue-600';
  if (score >= 50) return 'text-yellow-600';
  return 'text-red-600';
});

const scoreBarClass = computed(() => {
  const score = props.result.compatibility_score;
  if (score >= 85) return 'bg-green-500';
  if (score >= 70) return 'bg-blue-500';
  if (score >= 50) return 'bg-yellow-500';
  return 'bg-red-500';
});

const matchLevelLabel = computed(() => {
  const score = props.result.compatibility_score;
  if (score >= 85) return 'Excellent Match! Strongly recommended to apply.';
  if (score >= 70) return 'Strong Match! Good candidate for this role.';
  if (score >= 50) return 'Moderate Match. Consider highlighting transferable skills.';
  return 'Weak Match. May want to focus on other opportunities.';
});

const matchLevelBgClass = computed(() => {
  const score = props.result.compatibility_score;
  if (score >= 70) return 'bg-green-50';
  if (score >= 50) return 'bg-yellow-50';
  return 'bg-red-50';
});

const matchLevelTextClass = computed(() => {
  const score = props.result.compatibility_score;
  if (score >= 70) return 'text-green-800';
  if (score >= 50) return 'text-yellow-800';
  return 'text-red-800';
});
</script>
```

### Download Links Component

Create `frontend/src/components/DownloadLinks.vue`:

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-6">
    <h3 class="text-lg font-semibold text-gray-900 mb-4">Download Documents</h3>
    
    <div class="grid grid-cols-2 gap-4">
      <a
        :href="`/api/pipeline/download/${pipelineId}/cv`"
        class="flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        download
      >
        <span>📄</span>
        <span>Download CV</span>
      </a>
      
      <a
        :href="`/api/pipeline/download/${pipelineId}/cover_letter`"
        class="flex items-center justify-center gap-2 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
        download
      >
        <span>📝</span>
        <span>Download Cover Letter</span>
      </a>
    </div>
  </div>
</template>

<script setup>
defineProps({
  pipelineId: {
    type: String,
    required: true
  }
});
</script>
```

### Toast Notification Component

Create `frontend/src/components/ToastNotification.vue`:

```vue
<template>
  <div class="fixed bottom-4 right-4 space-y-2 z-50">
    <TransitionGroup name="toast">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        class="max-w-sm p-4 rounded-lg shadow-lg"
        :class="notificationClass(notification.type)"
      >
        <div class="flex items-start gap-3">
          <span class="text-xl">{{ notificationIcon(notification.type) }}</span>
          <div class="flex-1">
            <h4 class="font-semibold">{{ notification.title }}</h4>
            <p class="text-sm opacity-90">{{ notification.message }}</p>
          </div>
          <button 
            @click="dismissNotification(notification.id)"
            class="opacity-50 hover:opacity-100"
          >
            ✕
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { getNotifications, markNotificationRead } from '../api/client';

const notifications = ref([]);
let pollInterval = null;

function notificationClass(type) {
  const classes = {
    info: 'bg-blue-500 text-white',
    success: 'bg-green-500 text-white',
    warning: 'bg-yellow-500 text-gray-900',
    error: 'bg-red-500 text-white'
  };
  return classes[type] || classes.info;
}

function notificationIcon(type) {
  const icons = {
    info: 'ℹ️',
    success: '✅',
    warning: '⚠️',
    error: '❌'
  };
  return icons[type] || icons.info;
}

async function fetchNotifications() {
  try {
    const result = await getNotifications(true);
    notifications.value = result.notifications;
  } catch (error) {
    console.error('Failed to fetch notifications:', error);
  }
}

async function dismissNotification(id) {
  await markNotificationRead(id);
  notifications.value = notifications.value.filter(n => n.id !== id);
}

onMounted(() => {
  fetchNotifications();
  pollInterval = setInterval(fetchNotifications, 3000);
});

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval);
});
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
```

### API Client

Create `frontend/src/api/client.js`:

```javascript
/**
 * API Client for Scout backend
 */

const API_BASE = '/api';

async function fetchJson(url, options = {}) {
  const response = await fetch(API_BASE + url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  return response.json();
}

export async function startPipeline(jobText) {
  return fetchJson('/pipeline/process', {
    method: 'POST',
    body: JSON.stringify({
      raw_job_text: jobText
    })
  });
}

export async function getPipelineStatus(pipelineId) {
  return fetchJson(`/pipeline/status/${pipelineId}`);
}

export async function getNotifications(unreadOnly = false) {
  const params = new URLSearchParams();
  if (unreadOnly) params.append('unread_only', 'true');
  return fetchJson(`/notifications?${params}`);
}

export async function markNotificationRead(notificationId) {
  return fetchJson(`/notifications/${notificationId}/read`, {
    method: 'POST'
  });
}
```

---

## Implementation Steps

### Step W.1: Backend API Routes
```bash
# Create app/api/routes/pipeline.py
# Verify:
python -c "from app.api.routes.pipeline import router; print('OK')"
```

### Step W.2: Frontend Setup
```bash
# Initialize Vue project in frontend/
cd frontend
npm create vue@latest . --template vue
npm install axios
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### Step W.3: Components
```bash
# Create all Vue components
# Verify:
npm run dev  # Start dev server
```

### Step W.4: Integration Test
```bash
# Start backend
uvicorn app.main:app --reload

# Start frontend  
cd frontend && npm run dev

# Test in browser
```

---

## Success Criteria

| Metric | Target | Verification |
|--------|--------|--------------|
| Job input | Text accepted | Paste job posting |
| Processing | Pipeline executes | Submit and watch progress |
| Results | Score displayed | View compatibility |
| Downloads | PDFs download | Click download links |
| Notifications | Toast appears | Check on success/error |

---

*This specification is aligned with Scout PoC Scope Document v1.0*

{{- define "backend.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "backend.fullname" -}}
{{- $name := printf "%s-%s" .Release.Name (include "backend.name" .) | trunc 63 | trimSuffix "-" -}}
{{- if regexMatch "^[a-z]" $name -}}
{{- $name -}}
{{- else -}}
{{- printf "r-%s" $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "backend.systemName" -}}
{{- default "app" .Values.systemName | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "backend.apiName" -}}
{{- printf "r-%s-api" (include "backend.systemName" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "backend.workerName" -}}
{{- printf "r-%s-worker" (include "backend.systemName" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "backend.cleanupName" -}}
{{- printf "r-%s-cleanup" (include "backend.systemName" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "backend.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "backend.namespace" -}}
{{- .Release.Namespace -}}
{{- end -}}

{{- define "backend.labels" -}}
helm.sh/chart: {{ include "backend.chart" . }}
app.kubernetes.io/name: {{ include "backend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "backend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "frontend.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "frontend.fullname" -}}
{{- $name := printf "%s-%s" .Release.Name (include "frontend.name" .) | trunc 63 | trimSuffix "-" -}}
{{- if regexMatch "^[a-z]" $name -}}
{{- $name -}}
{{- else -}}
{{- printf "r-%s" $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "frontend.systemName" -}}
{{- default "app" .Values.systemName | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "frontend.webName" -}}
{{- printf "r-%s-web" (include "frontend.systemName" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "frontend.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "frontend.namespace" -}}
{{- .Release.Namespace -}}
{{- end -}}

{{- define "frontend.labels" -}}
helm.sh/chart: {{ include "frontend.chart" . }}
app.kubernetes.io/name: {{ include "frontend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "frontend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "frontend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

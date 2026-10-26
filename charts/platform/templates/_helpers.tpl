{{- define "platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "platform.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if eq .Release.Name $name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "platform.labels" -}}
app.kubernetes.io/name: {{ include "platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "platform.serviceAccount" -}}
{{- if .Values.serviceAccount.name }}{{ .Values.serviceAccount.name }}{{ else }}{{ include "platform.fullname" . }}{{ end -}}
{{- end -}}

{{- define "platform.postgresSecret" -}}
{{- default (printf "%s-postgres" (include "platform.fullname" .)) .Values.postgres.existingSecret -}}
{{- end -}}

{{- define "platform.adminSecret" -}}
{{- default (printf "%s-admin" (include "platform.fullname" .)) .Values.seed.secretName -}}
{{- end -}}

{{- define "platform.image" -}}
{{- $image := index .root.Values.images .key -}}
{{- printf "%s:%s" $image.repository $image.tag -}}
{{- end -}}

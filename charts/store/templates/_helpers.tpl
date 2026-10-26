{{- define "store.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}


{{- define "store.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}


{{- define "store.labels" -}}
app.kubernetes.io/name: {{ include "store.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "store.selectorLabels" -}}
app.kubernetes.io/name: {{ include "store.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "store.wordpressServiceAccount" -}}
{{- if .Values.wordpress.serviceAccount.name -}}
{{ .Values.wordpress.serviceAccount.name }}
{{- else if .Values.wordpress.serviceAccount.create -}}
{{ include "store.fullname" . }}-wordpress
{{- else -}}
default
{{- end -}}
{{- end -}}

{{- define "store.bootstrapServiceAccount" -}}
{{- if .Values.bootstrap.serviceAccount.name -}}
{{ .Values.bootstrap.serviceAccount.name }}
{{- else if .Values.bootstrap.serviceAccount.create -}}
{{ include "store.fullname" . }}-bootstrap
{{- else -}}
default
{{- end -}}
{{- end -}}

{{- define "store.secretName" -}}
{{- default (include "store.fullname" .) .Values.secrets.existingSecret -}}
{{- end -}}

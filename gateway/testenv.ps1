# testenv.ps1
$base = "http://127.0.0.1:9000"
$env:NO_PROXY = "127.0.0.1,localhost"

# Test accounts only. A and B passwords are the ones set by the reset script.
$env:PW_A = "a-long-test-password-1"
$env:PW_B = "another-long-test-password-2"
if (-not $env:ADMIN_PW) {
  $s = Read-Host "Admin password" -AsSecureString
  $env:ADMIN_PW = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))
}
$adminPw = $env:ADMIN_PW

function Call($Method, $Path, $Token, $Body) {
  $h = @{}; if ($Token) { $h["Authorization"] = "Bearer $Token" }
  $p = @{ Method=$Method; Uri="$base$Path"; Headers=$h; UseBasicParsing=$true; ErrorAction="Stop" }
  if ($Body) { $p.Body = ($Body | ConvertTo-Json -Depth 10); $p.ContentType = "application/json" }
  try { $r = Invoke-WebRequest @p; $code = [int]$r.StatusCode; $raw = $r.Content }
  catch {
    $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
    $raw = if ($_.ErrorDetails.Message) { $_.ErrorDetails.Message } else { $_.Exception.Message }
  }
  $json = $null; try { $json = $raw | ConvertFrom-Json } catch {}
  Write-Host "$Method $Path -> HTTP $code" -ForegroundColor Cyan
  if ($raw) { Write-Host $raw }
  [pscustomobject]@{ Code=$code; Json=$json; Raw=$raw }
}

function Mcp($Key, $Method, $Params, $Path="/mcp/") {
  $b = @{ jsonrpc="2.0"; id=1; method=$Method; params=$Params } | ConvertTo-Json -Depth 10
  try {
    $r = Invoke-WebRequest -Method Post -Uri "$base$Path" -UseBasicParsing -TimeoutSec 45 `
      -Headers @{ Authorization="Bearer $Key"; Accept="application/json, text/event-stream" } `
      -ContentType "application/json" -Body $b
    Write-Host "MCP $Method -> HTTP $([int]$r.StatusCode)" -ForegroundColor Cyan; $r.Content
  } catch {
    $c = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
    Write-Host "MCP $Method -> HTTP $c" -ForegroundColor Cyan
  }
}

function Login-All {
  $script:adm  = (Call POST /auth/login $null @{ email="admin@example.com";   password=$adminPw }).Json.access_token
  $script:memA = (Call POST /auth/login $null @{ email="membera@example.com"; password=$env:PW_A }).Json.access_token
  $script:memB = (Call POST /auth/login $null @{ email="memberb@example.com"; password=$env:PW_B }).Json.access_token
  "adm=$($adm.Length) memA=$($memA.Length) memB=$($memB.Length)   (each should be about 43)"
}
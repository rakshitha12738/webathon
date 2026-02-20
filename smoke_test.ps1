$ErrorActionPreference = 'Stop'
$base='http://127.0.0.1:5000'
try {
  $doctor = Invoke-RestMethod -Uri "$base/api/register" -Method Post -Body (@{name='Dr Smith'; email='doctor@example.com'; password='password123'; role='doctor'} | ConvertTo-Json) -ContentType 'application/json'
  Write-Output "DR: $($doctor | ConvertTo-Json)"
  $patient = Invoke-RestMethod -Uri "$base/api/register" -Method Post -Body (@{name='John Doe'; email='patient@example.com'; password='password123'; role='patient'; assigned_doctor_id=$doctor.user_id} | ConvertTo-Json) -ContentType 'application/json'
  Write-Output "PA: $($patient | ConvertTo-Json)"
  $login = Invoke-RestMethod -Uri "$base/api/login" -Method Post -Body (@{email='patient@example.com'; password='password123'} | ConvertTo-Json) -ContentType 'application/json'
  Write-Output "LG: $($login | ConvertTo-Json)"
  $token = $login.token
  $log = Invoke-RestMethod -Uri "$base/api/patient/daily-log" -Method Post -Headers @{Authorization = "Bearer $token"} -Body (@{date='2026-02-20'; pain_level=4; mood_level=3; sleep_hours=7.0; appetite='good'; swelling=$false; body_part='knee'; note_text='Feeling okay'} | ConvertTo-Json) -ContentType 'application/json'
  Write-Output "LOG: $($log | ConvertTo-Json)"
  $logs = Invoke-RestMethod -Uri "$base/api/patient/my-logs" -Method Get -Headers @{Authorization = "Bearer $token"}
  Write-Output "MYL: $($logs | ConvertTo-Json)"
} catch {
  Write-Output "ERR: $($_.Exception.Message)"
  if ($_.Exception.Response) {
    $sr = $_.Exception.Response.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($sr)
    Write-Output "BODY: $($reader.ReadToEnd())"
  }
}

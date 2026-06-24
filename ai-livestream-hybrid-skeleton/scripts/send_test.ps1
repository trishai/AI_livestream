$body = @{
    reply = "Xin chào test"
    emotion = "happy"
    action = "sell"
    source_user = "debug"
    comment = "gia bao nhieu"
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8088/speak" `
  -Method POST `
  -ContentType "application/json" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
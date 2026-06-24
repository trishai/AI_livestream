$body = @{
    comment = "da chot"
    user_id = "viewer_007"
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "http://localhost:5678/webhook/ai-livestream-comment-test" `
  -Method POST `
  -ContentType "application/json" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body))

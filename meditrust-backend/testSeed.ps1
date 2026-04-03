$body = @{
    secret = "MediTrustAdmin@2026SecretKey"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:3000/api/admin/seed" -Method POST -ContentType "application/json" -Body $body
Write-Host "Seed response:"
$response | ConvertTo-Json -Depth 5

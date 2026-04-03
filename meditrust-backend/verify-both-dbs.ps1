Write-Host "Checking NGO databases..."

Write-Host "`n=== NGO DB (ngo_db) ==="
$cmd1 = "mysql -u root -pNewRootPassword123 -e `"USE ngo_db; SELECT COUNT(*) as total_ngos FROM ngo_identity;`""
cmd /c $cmd1

Write-Host "`n=== MediTrust NGO Table ==="
$cmd2 = "mysql -u root -pNewRootPassword123 -e `"USE meditrust; SELECT COUNT(*) as total_ngos FROM NGO;`""
cmd /c $cmd2

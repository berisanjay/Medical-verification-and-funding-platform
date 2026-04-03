$mysqlPath = "mysql"
$username = "root"
$password = "NewRootPassword123"
$database = "ngo_db"
$sqlFile = "D:\OM\MedicalTrust\Medical_crowdfunding\meditrust-backend\seed-ngo-db.sql"

Write-Host "Seeding NGO database..."
$cmd = "$mysqlPath -u $username -p$password < `"$sqlFile`""
cmd /c $cmd

Write-Host "Verifying NGO database..."
$verifyCmd = "$mysqlPath -u $username -p$password -e `"USE $database; SELECT COUNT(*) as total_ngos FROM ngo_identity;`""
cmd /c $verifyCmd

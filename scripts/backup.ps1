# PowerShell kunlik zaxira
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { ".\backups" }
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$file = Join-Path $outDir "fjsti_id_$stamp.sql"
docker compose exec -T db pg_dump -U fjsti fjsti_id | Set-Content -Path $file -Encoding Byte
Write-Host "Backup: $file"

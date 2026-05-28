param(
  [string]$LocalRoot = "C:/OpenHeat-local/solweig/b87c_n300",
  [string]$RepoPacketDir = "C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/outputs/v12_surrogate/b8_7b4_b87c_materialization_package/postrun_review_packet"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $RepoPacketDir | Out-Null
Copy-Item -Force "C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/outputs/v12_surrogate/b8_7b4_b87c_materialization_package/b87c_manifest.csv" (Join-Path $RepoPacketDir "b87c_manifest.csv")
Copy-Item -Force "C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid_b8/06-openheat_grid/outputs/v12_surrogate/b8_7b4_b87c_materialization_package/b87c_manifest_audit.csv" (Join-Path $RepoPacketDir "b87c_manifest_audit.csv")
Get-ChildItem -Path (Join-Path $LocalRoot "run_logs") -Filter "*.csv" -ErrorAction SilentlyContinue |
  Copy-Item -Destination $RepoPacketDir -Force
Write-Host "Review packet refreshed at $RepoPacketDir"
Write-Host "No rasters or svfs.zip are copied by this script."

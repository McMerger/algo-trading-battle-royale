# PowerShell script to generate gRPC code from protobuf definitions for Python and Go

Write-Host "Generating gRPC code from protobuf definitions..." -ForegroundColor Cyan

# Create output directories
Write-Host "Creating output directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "..\python-strategy-engine\grpc_generated" | Out-Null
New-Item -ItemType Directory -Force -Path "..\go-execution-core\pb" | Out-Null

# Generate Python code
Write-Host "Generating Python gRPC code..." -ForegroundColor Yellow
python -m grpc_tools.protoc `
    -I. `
    --python_out=..\python-strategy-engine\grpc_generated `
    --grpc_python_out=..\python-strategy-engine\grpc_generated `
    execution.proto

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python protobuf generation failed!" -ForegroundColor Red
    exit 1
}

# Fix Python imports (protobuf generates incorrect relative imports)
Write-Host "Fixing Python imports..." -ForegroundColor Yellow
$grpcFile = "..\python-strategy-engine\grpc_generated\execution_pb2_grpc.py"
if (Test-Path $grpcFile) {
    (Get-Content $grpcFile) -replace '^import execution_pb2', 'from . import execution_pb2' | Set-Content $grpcFile
}

# Create __init__.py for Python package
New-Item -ItemType File -Force -Path "..\python-strategy-engine\grpc_generated\__init__.py" | Out-Null

Write-Host "✓ Python gRPC code generated in python-strategy-engine\grpc_generated\" -ForegroundColor Green

# Check if protoc is available for Go generation
if (Get-Command protoc -ErrorAction SilentlyContinue) {
    # Generate Go code
    Write-Host "Generating Go gRPC code..." -ForegroundColor Yellow
    protoc -I. `
        --go_out=..\go-execution-core\pb `
        --go_opt=paths=source_relative `
        --go-grpc_out=..\go-execution-core\pb `
        --go-grpc_opt=paths=source_relative `
        execution.proto
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Go gRPC code generated in go-execution-core\pb\" -ForegroundColor Green
    } else {
        Write-Host "WARNING: Go protobuf generation failed (protoc plugins may be missing)" -ForegroundColor Yellow
        Write-Host "Python code generation completed successfully. Go code can be generated in Docker." -ForegroundColor Yellow
    }
} else {
    Write-Host "WARNING: protoc not found. Skipping Go code generation." -ForegroundColor Yellow
    Write-Host "Python code generation completed successfully. Go code can be generated in Docker." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "gRPC code generation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Python: python-strategy-engine\grpc_generated\" -ForegroundColor Cyan
Write-Host "Go: go-execution-core\pb\" -ForegroundColor Cyan

#!/bin/bash
# Generate gRPC code from protobuf definitions for Python and Go

set -e

echo "Generating gRPC code from protobuf definitions..."

# Create output directories
mkdir -p ../python-strategy-engine/grpc_generated
mkdir -p ../go-execution-core/pb

# Generate Python code
echo "Generating Python gRPC code..."
python3 -m grpc_tools.protoc \
    -I. \
    --python_out=../python-strategy-engine/grpc_generated \
    --grpc_python_out=../python-strategy-engine/grpc_generated \
    execution.proto

# Fix Python imports (protobuf generates incorrect relative imports)
sed -i 's/^import execution_pb2/from . import execution_pb2/' \
    ../python-strategy-engine/grpc_generated/execution_pb2_grpc.py 2>/dev/null || \
    sed -i '' 's/^import execution_pb2/from . import execution_pb2/' \
    ../python-strategy-engine/grpc_generated/execution_pb2_grpc.py 2>/dev/null || true

# Create __init__.py for Python package
touch ../python-strategy-engine/grpc_generated/__init__.py

echo "✓ Python gRPC code generated in python-strategy-engine/grpc_generated/"

# Generate Go code
echo "Generating Go gRPC code..."
protoc -I. \
    --go_out=../go-execution-core/pb \
    --go_opt=paths=source_relative \
    --go-grpc_out=../go-execution-core/pb \
    --go-grpc_opt=paths=source_relative \
    execution.proto

echo "✓ Go gRPC code generated in go-execution-core/pb/"

echo ""
echo "gRPC code generation complete!"
echo ""
echo "Python: python-strategy-engine/grpc_generated/"
echo "Go: go-execution-core/pb/"

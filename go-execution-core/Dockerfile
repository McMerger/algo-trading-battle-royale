FROM golang:1.21-alpine AS builder

WORKDIR /build

# Install build dependencies including protobuf
RUN apk add --no-cache git gcc musl-dev protobuf protobuf-dev

# Copy go mod files
COPY go-execution-core/go.mod go-execution-core/go.sum* ./

# Download dependencies
RUN go mod download || go mod download

# Install protoc Go plugins
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.31.0
RUN go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.3.0

# Copy source code first
COPY go-execution-core/ ./

# Copy proto files and generate code in the pb subdirectory
COPY proto/ /build/proto/
RUN mkdir -p pb && \
    protoc -I/build/proto \
    --go_out=./pb \
    --go_opt=paths=source_relative \
    --go-grpc_out=./pb \
    --go-grpc_opt=paths=source_relative \
    /build/proto/execution.proto

# After generating proto files, download all dependencies including from generated code
# Use go get to download without strict verification
RUN go get -d ./... || true
RUN go mod download

# Build the binary with GO111MODULE and GOPROXY settings
RUN CGO_ENABLED=1 GOOS=linux GO111MODULE=on go build -mod=mod -a -installsuffix cgo -ldflags="-w -s" -o execution-engine .

# Final stage
FROM alpine:latest

WORKDIR /app

# Install runtime dependencies
RUN apk --no-cache add ca-certificates postgresql-client wget

# Copy binary from builder
COPY --from=builder /build/execution-engine .

# Expose ports
EXPOSE 8080 8081 50050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Run the binary
CMD ["./execution-engine"]

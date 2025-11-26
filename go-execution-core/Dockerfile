FROM golang:1.21-alpine AS builder

WORKDIR /build

# Install build dependencies
RUN apk add --no-cache git gcc musl-dev

# Copy go mod files
COPY go-execution-core/go.mod go-execution-core/go.sum* ./

# Download dependencies
RUN go mod download || go mod download

# Copy source code
COPY go-execution-core/ ./

# Build the binary
RUN CGO_ENABLED=1 GOOS=linux go build -a -installsuffix cgo -ldflags="-w -s" -o execution-engine .

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

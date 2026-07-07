FROM golang:1.24-alpine AS builder

RUN apk add --no-cache \
    ca-certificates \
    gcc \
    musl-dev \
    librdkafka-dev

WORKDIR /build

COPY go.mod go.sum ./
RUN go mod download && go mod verify

COPY . .

ARG TARGETOS
ARG TARGETARCH
RUN CGO_ENABLED=1 \
    GOOS=${TARGETOS} \
    GOARCH=${TARGETARCH} \
    go build -tags dynamic -o /build/downloader \
    ./main.go

# ------------------
FROM alpine:3

RUN apk add --no-cache \
    ca-certificates \
    librdkafka

RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

WORKDIR /app

COPY --from=builder /build/downloader /app/downloader

RUN chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["/app/downloader"]

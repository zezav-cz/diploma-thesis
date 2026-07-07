package logging

import (
	"bytes"
	"github.com/sirupsen/logrus"
	"runtime"
	"strconv"
)

type GoroutineHook struct{}

func (h *GoroutineHook) Levels() []logrus.Level {
	return logrus.AllLevels
}

func (h *GoroutineHook) Fire(entry *logrus.Entry) error {
	entry.Data["goid"] = getGoroutineID()
	return nil
}

func getGoroutineID() uint64 {
	b := make([]byte, 64)
	b = b[:runtime.Stack(b, false)]
	b = bytes.TrimPrefix(b, []byte("goroutine "))
	b = b[:bytes.IndexByte(b, ' ')]
	n, _ := strconv.ParseUint(string(b), 10, 64)
	return n
}

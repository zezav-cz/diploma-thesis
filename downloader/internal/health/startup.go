package health

import (
	"fmt"
	"os"
)

const startupIndicatorFile = "/tmp/start"

// CheckStartupIndicatorNotExists checks that the startup indicator file does not exist
// If it exists, it means the application was not properly shut down
// This function should be called at the beginning of main() before initialization
func CheckStartupIndicatorNotExists() error {
	if _, err := os.Stat(startupIndicatorFile); err == nil {
		return fmt.Errorf("startup indicator file %s already exists - application was not properly shutdown", startupIndicatorFile)
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("failed to check startup indicator file: %w", err)
	}
	return nil
}

// CreateStartupIndicator creates the startup indicator file
// This function should be called when startup is complete
func CreateStartupIndicator() error {
	file, err := os.Create(startupIndicatorFile)
	if err != nil {
		return fmt.Errorf("failed to create startup indicator file: %w", err)
	}
	defer file.Close()

	return nil
}

// RemoveStartupIndicator removes the startup indicator file
// This function should be called when the checker is closed
func RemoveStartupIndicator() error {
	if err := os.Remove(startupIndicatorFile); err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("failed to remove startup indicator file: %w", err)
	}
	return nil
}

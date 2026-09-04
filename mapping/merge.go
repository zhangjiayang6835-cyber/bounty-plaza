// Package mapping provides deterministic helpers for composing SS13 DMM maps.
package mapping

import (
	"fmt"
	"strings"
)

// MergeRows combines a northern MetaStation slice with a southern DeltaStation
// slice. The slices must have equal width; the returned rows are independent.
func MergeRows(metaNorth, deltaSouth [][]string) ([][]string, error) {
	if len(metaNorth) == 0 || len(deltaSouth) == 0 {
		return nil, fmt.Errorf("both map slices must be non-empty")
	}
	width := len(metaNorth[0])
	if width == 0 {
		return nil, fmt.Errorf("map width must be positive")
	}
	merged := make([][]string, 0, len(metaNorth)+len(deltaSouth))
	// Keep the requested north-to-south composition deterministic; map iteration is random.
	sections := []struct {
		name string
		rows [][]string
	}{
		{name: "MetaStation north", rows: metaNorth},
		{name: "DeltaStation south", rows: deltaSouth},
	}
	for _, section := range sections {
		for row, cells := range section.rows {
			if len(cells) != width {
				return nil, fmt.Errorf("%s row %d has width %d, want %d", section.name, row, len(cells), width)
			}
			copyRow := append([]string(nil), cells...)
			merged = append(merged, copyRow)
		}
	}
	return merged, nil
}

// EncodeRows emits a compact, reviewable DMM-like row representation.
func EncodeRows(rows [][]string) (string, error) {
	if len(rows) == 0 {
		return "", fmt.Errorf("map has no rows")
	}
	width := len(rows[0])
	if width == 0 {
		return "", fmt.Errorf("map width must be positive")
	}
	var b strings.Builder
	for i, row := range rows {
		if len(row) != width {
			return "", fmt.Errorf("row %d has width %d, want %d", i, len(row), width)
		}
		if i > 0 { b.WriteByte('\n') }
		b.WriteString(strings.Join(row, " "))
	}
	return b.String(), nil
}

package mapping

import "testing"

func TestMergeRowsOrderAndCopy(t *testing.T) {
	north := [][]string{{"meta-a"}, {"meta-b"}}
	south := [][]string{{"delta-a"}}
	got, err := MergeRows(north, south)
	if err != nil { t.Fatal(err) }
	if got[0][0] != "meta-a" || got[2][0] != "delta-a" { t.Fatalf("unexpected order: %#v", got) }
	north[0][0] = "changed"
	if got[0][0] != "meta-a" { t.Fatal("merge aliases input rows") }
}

func TestMergeRowsRejectsRaggedInput(t *testing.T) {
	if _, err := MergeRows([][]string{{"a"}, {"b", "c"}}, [][]string{{"d"}}); err == nil { t.Fatal("expected width error") }
}

func TestEncodeRows(t *testing.T) {
	got, err := EncodeRows([][]string{{"a", "b"}, {"c", "d"}})
	if err != nil || got != "a b\nc d" { t.Fatalf("got %q, err %v", got, err) }
}
